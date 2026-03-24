import os
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from schemas import GraphState, SceneState, intro_scene_output, topic_scene_output
from langchain_core.prompts import ChatPromptTemplate
from agent import llm_thinker # Or whichever Groq model you rotate
from engines import concat_videos

browser_semaphore = asyncio.Semaphore(5) # Lowered for HF Spaces free tier limits

async def planner(state: GraphState):
    # Your planner LLM logic
    return {"introduction": "Intro text", "topics": ["Topic 1"], "theme_color": "#FF0000"}

def continue_to_scenes(state: GraphState):
    sends = [Send("generate_scene", {"introduction": state["introduction"], "topics": state["topics"], "current_index": 0, "topic_text": ""})]
    for i, topic in enumerate(state["topics"]):
        sends.append(Send("generate_scene", {"introduction": state["introduction"], "topics": state["topics"], "current_index": i + 1, "topic_text": topic}))
    return sends

async def generate_scene(state: SceneState):
    # Your parallel generation logic using browser_semaphore
    return {"clips": [(state["current_index"], "scene_x.mp4")]}

async def merge_videos(state: GraphState):
    sorted_clips = sorted(state["clips"], key=lambda x: x[0])
    video_paths = [path for _, path in sorted_clips]
    final_video_path = "final_output_video.mp4"
    await concat_videos(video_paths, final_video_path)
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
