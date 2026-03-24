import asyncio
import os
import random
import markdown
import edge_tts
from faster_whisper import WhisperModel
from playwright.async_api import async_playwright

# Load Whisper Globally
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

async def get_whisper_timestamps(audio_file_path):
    segments, _ = whisper_model.transcribe(audio_file_path, word_timestamps=True)
    return ", ".join([f"[{int(w.start//3)*3}-{int(w.start//3)*3+3}] {w.word}" for s in segments for w in s.words])

async def run_ffmpeg(command: str):
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg Error: {stderr.decode()}")

async def get_audio_duration(audio_path: str) -> float:
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    return float(stdout.decode().strip())

async def _take_screenshot(html_content: str, output_filename: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})
        await page.set_content(html_content)
        await asyncio.sleep(0.5)
        await page.screenshot(path=output_filename, omit_background=True)
        await browser.close()

# Include your HTML generation functions here (generate_banner, generate_slide_from_markdown, etc.)
# Include your compositing functions here (combine_layered_slide, concat_videos, etc.)
