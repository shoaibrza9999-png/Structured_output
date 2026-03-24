import os
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain_core.prompts import ChatPromptTemplate
import edge_tts

# Import from your other files
from schemas import GraphState, SceneState, intro_scene_output, topic_scene_output
from agent import get_random_groq_model, llm_gemini, generate_agentic_manim_slide
from engines import (
    get_audio_duration, generate_intro_slide, combine_intro_slide,
    generate_ai_image, combine_ai_image_ken_burns, generate_banner,
    generate_slide_from_markdown, generate_emoji_text_slide,
    generate_bullet_list, generate_grid, generate_chart_slide,
    generate_question_slide, combine_layered_slide, concat_videos
)

# Protects HF Spaces from crashing due to too many headless browsers opening at once
browser_semaphore = asyncio.Semaphore(5) 

async def planner(state: GraphState):
    """MAIN LLM: Generates the intro, topics, and picks a theme color."""
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are an expert course creator. Output an engaging introduction outlining what will be covered, followed by a detailed list of topics. Finally, pick a visually striking 6-character Hex color code (e.g. #FF5733) that matches the emotional tone of the subject to be used as the presentation's theme color."),
        ("user", "{prompt}")
    ])

    current_llm = get_random_groq_model()
    chain = prompt_template | current_llm.with_structured_output(GraphState) # Assuming GraphState or a similar dict output
    res = await chain.ainvoke({"prompt": state["prompt"]})

    return {
        "introduction": res.get("Introduction", res.get("introduction")),
        "topics": res.get("Topics", res.get("topics")),
        "theme_color": res.get("ThemeColor", res.get("theme_color", "#FF5733"))
    }

def continue_to_scenes(state: GraphState):
    """Maps the data to the parallel Scene nodes."""
    sends = []
    # Send Intro (Index 0)
    sends.append(Send("generate_scene", {
        "introduction": state["introduction"],
        "topics": state["topics"],
        "current_index": 0,
        "topic_text": ""
    }))
    # Send Topics (Index 1, 2, 3...)
    for i, topic in enumerate(state["topics"]):
        sends.append(Send("generate_scene", {
            "introduction": state["introduction"],
            "topics": state["topics"],
            "current_index": i + 1,
            "topic_text": topic
        }))
    return sends

async def generate_scene(state: SceneState):
    """Parallel node handling both Intro and Topic scenes."""
    idx = state["current_index"]
    topics_context = "\n".join([f"Topic {i+1}: {t}" for i, t in enumerate(state["topics"])])
    slides_to_render = []
    current_llm = get_random_groq_model()

    if idx == 0:
        prompt_template = ChatPromptTemplate.from_messages([
               ("system", """
        DO NOT welcome the viewer. The intro and other topics are for context only. Focus entirely on teaching '{topic_text}'.
        Max 3 slides.if other slide cam do the task not use markdown slide .
        SLIDE GENERATION RULES:
        1. You MUST start with a `banner_slide` to introduce this specific topic chapter.
        2. Follow with one or more additional slides chosen from this toolkit (Note: all templates support basic HTML. use <br> to break line):
           - MarkdownSlide: Keep text concise (max 6-7 lines).
           - EmojiTextSlide: Use for punchy, highly visual facts. Use emojis sparingly.
           - BulletListSlide: Best for sequential steps or standard lists.
           - GridSlide: BEST FOR breaking down sub-categories, types, or showing 3 to 6 key data points.use any emoji at starting of sentence.
           - ChartSlide: Use to compare numerical data or show simple statistics using a bar chart.
           - QuestionSlide: Use to ask thought-provoking questions, introduce a quiz, or transition to a new idea.
           - AiImage: Use to show a full-screen, high-quality AI-generated image. Provide a highly detailed visual prompt.only for drawing object and things. Do not try to draw which have text rendering or graph.
           - ManimSlide: BEST FOR mathematical concepts, 2D/3D geometry, plotting graphs, or dynamic technical animations. Provide a detailed visual `prompt`.if needed generate more slide do not try to keep all in single slide.
        CRITICAL RULE: Do NOT output any conversational text, explanations Be completely silent other than the tool call.
        Voice will be played at background you will provided.voice text must be detailed.
        Ensure the voiceover text is educational, clear, and perfectly matches the visual pace and detailed."""),
        ("user", "Current Topic ({index}): {topic_text}\n\nIntroduction for context: {intro}\nAll Topics for context:\n{topics}")

        ])
        chain = prompt_template | current_llm.with_structured_output(intro_scene_output)
        res = await chain.ainvoke({"intro": state["introduction"], "topics": topics_context})
        slides_to_render = [res["intro_slide"]] + res["additional_slides"]
    else:
        prompt_template = ChatPromptTemplate.from_messages([
               ("system", """
        DO NOT welcome the viewer. The intro and other topics are for context only. Focus entirely on teaching '{topic_text}'.
        Max 3 slides.if other slide cam do the task not use markdown slide .
        SLIDE GENERATION RULES:
        1. You MUST start with a `banner_slide` to introduce this specific topic chapter.
        2. Follow with one or more additional slides chosen from this toolkit (Note: all templates support basic HTML. use <br> to break line):
           - MarkdownSlide: Keep text concise (max 6-7 lines).
           - EmojiTextSlide: Use for punchy, highly visual facts. Use emojis sparingly.
           - BulletListSlide: Best for sequential steps or standard lists.
           - GridSlide: BEST FOR breaking down sub-categories, types, or showing 3 to 6 key data points.use any emoji at starting of sentence.
           - ChartSlide: Use to compare numerical data or show simple statistics using a bar chart.
           - QuestionSlide: Use to ask thought-provoking questions, introduce a quiz, or transition to a new idea.
           - AiImage: Use to show a full-screen, high-quality AI-generated image. Provide a highly detailed visual prompt.only for drawing object and things. Do not try to draw which have text rendering or graph.
           - ManimSlide: BEST FOR mathematical concepts, 2D/3D geometry, plotting graphs, or dynamic technical animations. Provide a detailed visual `prompt`.if needed generate more slide do not try to keep all in single slide.
        CRITICAL RULE: Do NOT output any conversational text, explanations Be completely silent other than the tool call.
        Voice will be played at background you will provided.voice text must be detailed.
        Ensure the voiceover text is educational, clear, and perfectly matches the visual pace and detailed."""),
        ("user", "Current Topic ({index}): {topic_text}\n\nIntroduction for context: {intro}\nAll Topics for context:\n{topics}")

        ])
        chain = prompt_template | current_llm.with_structured_output(topic_scene_output)
        res = await chain.ainvoke({"index": idx, "topic_text": state["topic_text"], "intro": state["introduction"], "topics": topics_context})
        slides_to_render = [res["banner_slide"]] + res["additional_slides"]

    async def process_single_slide(slide_num, slide_data):
        audio_path = f"temp_aud_{idx}_{slide_num}.mp3"
        image_path = f"temp_img_{idx}_{slide_num}.png"
        video_path = f"temp_vid_{idx}_{slide_num}.mp4"

        print(f"🎤 Generating voice: {slide_data['voice']}")
        communicate = edge_tts.Communicate(slide_data['voice'], "en-US-AriaNeural")
        await communicate.save(audio_path)
        duration = await get_audio_duration(audio_path)

        is_intro_or_ai = False

        async with browser_semaphore:
            if slide_data.get("template_name") == "IntroSlide" or "image_prompt" in slide_data:
                is_intro_or_ai = True
                await generate_intro_slide(slide_data["heading"], image_path)
                await combine_intro_slide(image_path, "intro_background.mp4", audio_path, video_path, duration)

            elif slide_data.get("template_name") == "ManimSlide":
                is_intro_or_ai = True 
                await generate_agentic_manim_slide(slide_data["prompt"], audio_path, video_path)

            elif slide_data.get("template_name") == "AiImage":
                is_intro_or_ai = True
                await generate_ai_image(slide_data.get("prompt", "Beautiful scenery"), image_path)
                await combine_ai_image_ken_burns(image_path, audio_path, video_path, duration)

            elif slide_data.get("short_description"): # Banner
                await generate_banner(str(idx), slide_data["heading"], slide_data["short_description"], image_path)
            elif slide_data.get("template_name") == "MarkdownSlide":
                await generate_slide_from_markdown(slide_data["md_text"], image_path)
            elif slide_data.get("template_name") == "EmojiTextSlide":
                await generate_emoji_text_slide(slide_data["text"], slide_data["emojis"], image_path)
            elif slide_data.get("template_name") == "BulletListSlide":
                await generate_bullet_list(slide_data["heading"], slide_data["bullet_points"], image_path)
            elif slide_data.get("template_name") == "GridSlide":
                await generate_grid(slide_data["sentences"], image_path)
            elif slide_data.get("template_name") == "ChartSlide":
                await generate_chart_slide(slide_data["chart_data"], slide_data["x_axis_title"], slide_data["y_axis_title"], slide_data["side_text"], image_path)
            elif slide_data.get("template_name") == "QuestionSlide":
                await generate_question_slide(slide_data["text"], image_path)

        template_name = slide_data.get("template_name", "BannerSlide")
        if not is_intro_or_ai:
            await combine_layered_slide(image_path, audio_path, video_path, duration, template_name)

        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise RuntimeError(f"❌ FFmpeg silently failed to create {video_path}")

        return video_path

    tasks = [process_single_slide(i, slide) for i, slide in enumerate(slides_to_render)]
    sub_video_paths = await asyncio.gather(*tasks)

    scene_path = f"scene_{idx}.mp4"
    await concat_videos(sub_video_paths, scene_path)
    return {"clips": [(idx, scene_path)]}

async def merge_videos(state: GraphState):
    """Concatenates all scenes into the final video and cleans up temp files."""
    sorted_clips = sorted(state["clips"], key=lambda x: x[0])
    video_paths = [path for _, path in sorted_clips]

    final_video_path = "final_output_video.mp4"
    await concat_videos(video_paths, final_video_path)

    # Clean up temp files
    for file in os.listdir():
        if file.startswith("temp_") or (file.startswith("scene_") and file.endswith(".mp4")):
            try:
                os.remove(file)
            except Exception:
                pass

    return {"final_video": final_video_path}

def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("planner", planner)
    workflow.add_node("generate_scene", generate_scene)
    workflow.add_node("merge_videos", merge_videos)

    workflow.add_edge(START, "planner")
    workflow.add_conditional_edges("planner", continue_to_scenes, ["generate_scene"])
    workflow.add_edge("generate_scene", "merge_videos")
    workflow.add_edge("merge_videos", END)
    
    return workflow.compile()
