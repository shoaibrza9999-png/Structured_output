import os
import asyncio
import re
import ast
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from schemas import ThinkingPlan, FallbackSlide
from engines import get_whisper_timestamps, get_audio_duration, run_ffmpeg

# Setup LLMs (Make sure to use HF Secrets for these in production)
llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
llm_coder = ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0)
llm_thinker = ChatGroq(model="openai/gpt-oss-120b", temperature=0.7)

import os
import asyncio
import re
import ast
import glob
import shutil
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from schemas import FallbackSlide, ThinkingPlan
from engines import get_whisper_timestamps, get_audio_duration, run_ffmpeg, generate_slide_from_markdown, combine_layered_slide
import edge_tts
import random

# Core LLM Definitions
llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

groq_model_pool = [
    ChatGroq(model="openai/gpt-oss-120b", temperature=0.7),
    ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0.7),
    ChatGroq(model="openai/gpt-oss-20b", temperature=0.7),
    ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7),
    ChatGroq(model="qwen/qwen3-32b", temperature=0.7),
    

]

def get_random_groq_model():
    return random.choice(groq_model_pool)

CODER_SYSTEM_PROMPT = """You are an expert Python developer and Manim Animation Director specializing strictly in Manim Community v0.20.1.
Your task is to translate a highly specific mathematical animation plan into flawless, executable Manim code.

CRITICAL OUTPUT RULES (FAILURE IS NOT AN OPTION):
1. RAW CODE ONLY: You must output ONLY valid Python code. Do NOT wrap the code in ```python markdown blocks. Do NOT include any conversational text, explanations, or greetings.
2. REQUIRED STRUCTURE: Always start your script with `from manim import *`. Create exactly one main class inheriting from the appropriate Scene type (e.g., `class GeneratedScene(Scene):` or `class GeneratedScene(ThreeDScene):`).

STRICT ANIMATION & TIMING RULES:
3. TIMING MATCHING: You must synchronize the `run_time` of your `self.play()` animations to perfectly match the exact durations given in the VISUAL PLAN.
4. PADDING WITH WAIT: Use `self.wait(X)` to pad out the exact remaining time as instructed by the plan. You MUST NOT ever generate `self.wait(0)`. If the remaining wait time is zero, omit the wait command entirely.
5. NO AUDIO LOGIC: Do not write any code to import, play, or sync audio tracks. Generate the visual Python code only.

MANIM v0.20.1 SYNTAX RULES:
6. POSITIONAL ARGS FIRST: In `self.play()`, ALL positional arguments MUST come BEFORE keyword arguments. Never place an animation without a keyword after a keyword argument like `run_time=2`.
7. RATE FUNCTIONS: Never use `func.`. Always pass rate functions explicitly as keyword arguments using `rate_functions.` (e.g., `rate_func=rate_functions.linear`).
8. CREATING MULTIPLE OBJECTS: `FadeIn` accepts multiple mobjects, but `Create()` and `Write()` strictly take ONLY ONE Mobject. To create a list of items, you MUST wrap them in a `VGroup` first (e.g., `self.play(Create(VGroup(*my_list)))`).
9. THE .ANIMATE TRAP: NEVER pass `run_time` or `rate_func` inside an `.animate` call (e.g., `obj.animate.move_to(UP, run_time=2)` is FATAL). Keyword arguments MUST ONLY be passed directly to `self.play()`.
10. COLORS: Strictly use the 6-character Hex codes provided in the plan (e.g., `color="#FF0000"`). NEVER use Manim's built-in text color names.

3D SCENE RULES (IF APPLICABLE):
11. INSTANT CAMERA SETUP: Use `self.set_camera_orientation(phi=..., theta=...)` as a standalone command. NEVER put this inside `self.play()`.
12. CONTINUOUS CAMERA ROTATION: To smoothly spin the camera over time, use `self.begin_ambient_camera_rotation(rate=...)`, followed by `self.wait(time)`, and end with `self.stop_ambient_camera_rotation()`.

GRAPH RULE
13. ALWAYS USE LABEL:in default label graph with numbers,etc.you can also generate without labels.
You will be provided with a VISUAL PLAN and highly specific REQUIRED DOCUMENTATION. You MUST strictly obey the parameters listed in the documentation.
"""

async def generate_agentic_manim_slide(prompt: str, audio_path: str, output_filename: str, max_retries=3):
    base_name = output_filename.replace('.mp4', '')
    raw_manim_vid = f"raw_{base_name}.mp4"

    print("⏳ Running Whisper for exact timestamps...")
    formatted_voice_text = await get_whisper_timestamps(audio_path)

    # 1. Fully restored Thinking & Planning calls
    print("🧠 Thinking LLM Planning...")
    think_prompt = f"{prompt}"
    plan_data = await asyncio.to_thread(generate_thinking_plan, think_prompt, formatted_voice_text)

    print(f"📄 Fetching docs for: {plan_data.required_functions}")
    retrieved_docs = await asyncio.to_thread(get_docs, plan_data.required_functions)

    # 2. Injecting the retrieved data into the Coder Prompt
    coder_prompt = CODER_SYSTEM_PROMPT + f"\n\nVISUAL PLAN:\n{plan_data.animation_plan}\n\nREQUIRED DOCUMENTATION:\n{retrieved_docs}\n\nWrite the Manim script now:"

    attempt = 1
    syntax_valid = False
    manim_success = False

    while attempt <= max_retries:
        print(f"\n🔄 Manim Coding Attempt {attempt} of {max_retries}...")

        current_coder_llm = llm_coder
        res = await current_coder_llm.ainvoke(coder_prompt)
        code = res.content.strip()
        code = re.sub(r"^```python\s*|^```\s*|```$", "", code, flags=re.MULTILINE).strip()
        if "from manim import *" not in code:
             code = "from manim import *\n" + code

        try:
            ast.parse(code)
            syntax_valid = True
        except SyntaxError as e:
            syntax_valid = False
            error_msg = f"Python Syntax Error: {e}"

        if syntax_valid:
            unique_script_name = f"manim_script_{base_name}.py"
            with open(unique_script_name, "w") as f:
                f.write(code)

            match = re.search(r"class\s+(\w+)\(Scene\):", code)
            scene_name = match.group(1) if match else "GeneratedScene"

            process = await asyncio.create_subprocess_exec(
                "manim", unique_script_name, scene_name,
                "--resolution", "1280,720", "--fps", "24", "--disable_caching",
                "-o", base_name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                search_pattern = f"media/videos/{unique_script_name.replace('.py', '')}/**/{base_name}.mp4"
                found_files = glob.glob(search_pattern, recursive=True)

                if found_files:
                    shutil.move(found_files[0], raw_manim_vid)
                    os.remove(unique_script_name)
                    manim_success = True
                    break 
            else:
                error_msg = "\n".join(stderr.decode().split("\n")[-20:])
                os.remove(unique_script_name) 

        # 3. Restored Error Document extraction for the retry loop
        print(f"⚠️ Render failed. Updating prompt with errors (Attempt {attempt})...")
        error_specific_docs = await asyncio.to_thread(extract_error_docs, error_msg)
        
        coder_prompt += f"""\n\n===================================
ATTEMPT {attempt} FAILED.
FAILED CODE:
{code}
ERROR TRACEBACK:
{error_msg}
HINT DOCUMENTS FOR FIX:
{error_specific_docs}
REWRITE THE CODE FIXING THIS SPECIFIC ERROR. Output ONLY raw code.
==================================="""
        attempt += 1

    if not manim_success:
        print("\n🚨 Manim failed. Initiating LLM Fallback Protocol...")
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert educator. Create a clear, text-based Markdown slide and a brand NEW voiceover. Do NOT mention any animations."),
            ("user", "Concept to explain: {prompt}")
        ])
        fallback_chain = fallback_prompt | llm_gemini.with_structured_output(FallbackSlide)
        fallback_data = await fallback_chain.ainvoke({"prompt": prompt})

        # 4. Changed voice to GuyNeural
        communicate = edge_tts.Communicate(fallback_data.voice, "en-US-GuyNeural")
        await communicate.save(audio_path)
        fallback_audio_dur = await get_audio_duration(audio_path)

        fallback_png = f"fallback_img_{base_name}.png"
        await generate_slide_from_markdown(fallback_data.md_text, fallback_png)

        await combine_layered_slide(fallback_png, audio_path, output_filename, fallback_audio_dur, "MarkdownSlide")
        return 

    print("\n🎞️ Merging Manim animation with Audio...")
    dur_a = await get_audio_duration(audio_path)
    dur_v = await get_video_duration(raw_manim_vid)
    target_dur = max(dur_a, dur_v)

    cmd = (
        f'ffmpeg -y -i "{raw_manim_vid}" -i "{audio_path}" '
        f'-filter_complex "[0:v]tpad=stop_mode=clone:stop_duration={target_dur}[v]; [1:a]apad[a]" '
        f'-map "[v]" -map "[a]" -c:v libx264 -r 24 -c:a aac -b:a 192k -pix_fmt yuv420p '
        f'-t {target_dur} "{output_filename}"'
    )
    await run_ffmpeg(cmd)

    if os.path.exists(raw_manim_vid):
        os.remove(raw_manim_vid)
