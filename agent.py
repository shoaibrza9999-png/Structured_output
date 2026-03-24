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
import random
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Your core Gemini model (if you still use it for fallback/planning)
llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# 2. Your pool of Groq models to rotate and bypass RPM limits
groq_model_pool = [
    ChatGroq(model="openai/gpt-oss-120b", temperature=0.7),
    ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0.7),
    ChatGroq(model="openai/gpt-oss-20b", temperature=0.7)
]

def get_random_groq_model():
    """
    Picks a random model from the pool to distribute API requests 
    safely across concurrent async tasks.
    """
    selected_model = random.choice(groq_model_pool)
    print(f"🤖 Selected LLM: {selected_model.model_name}")
    return selected_model


async def generate_agentic_manim_slide(prompt: str, audio_path: str, output_filename: str, max_retries=3):
    # Your Manim loop logic goes here
    # 1. Get timestamps
    # 2. Call thinker LLM
    # 3. Call coder LLM in a loop
    # 4. Render via subprocess
    # 5. Fallback to MarkdownSlide if it fails
    pass
