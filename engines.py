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




# ==========================================
# 2. The Refactored HTML Templates
# ==========================================

async def generate_banner(number, heading, short_description, output_filename):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden;
            display: flex; align-items: center; font-family: 'Outfit', sans-serif;
            background: transparent !important; /* Made transparent */
        }}
        .number-container {{
            width: 380px; display: flex; justify-content: center; align-items: center;
        }}
        .big-number {{
            font-size: 380px; font-weight: 700; font-family: sans-serif; color: white;
            -webkit-text-stroke: 6px black; text-shadow: 15px 15px 0px black;
            line-height: 1; margin-top: -30px;
        }}
        .text-container {{
            flex: 1; background: white; border: 5px solid black; border-right: none;
            border-radius: 120px 0 0 120px; height: 400px; display: flex;
            flex-direction: column; justify-content: center; padding-left: 80px; box-sizing: border-box;
            box-shadow: -15px 15px 0px rgba(0,0,0,0.1); /* Added slight shadow to separate from paper */
        }}
        .heading {{ font-size: 65px; font-weight: 500; margin: 0; color: #111; line-height: 1.15; }}
        .subheading {{ font-size: 34px; font-weight: 400; margin: 15px 0 0 0; color: #333; }}
    </style>
    </head>
    <body>
        <div class="number-container"><div class="big-number">{number}</div></div>
        <div class="text-container">
            <div class="heading">{heading}</div>
            <div class="subheading">{short_description}</div>
        </div>
    </body>
    </html>
    """
    print(f"Generating Transparent Banner PNG for Chapter {number}...")
    await _take_screenshot(html_content, output_filename)


async def generate_grid(sentences, output_filename):
    cards_html = ""
    for i, text in enumerate(sentences):
        md_text = markdown.markdown(text)
        cards_html += f"""
        <div class="card">
            <div class="card-number">{i+1:02d}</div>
            <div class="card-text">{md_text}</div>
            <div class="card-dot"></div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden;
            display: flex; justify-content: center; align-items: center; font-family: 'Outfit', sans-serif;
            background: transparent !important; /* Made transparent */
        }}
        #grid-container {{ width: 1040px; display: flex; flex-wrap: wrap; justify-content: flex-start; gap: 40px; }}
        .card {{
            width: 320px; height: 220px; background: white; border: 3px solid black; border-radius: 16px;
            position: relative; box-shadow: 8px 8px 0px #ffd83b; padding: 25px; box-sizing: border-box;
            display: flex; flex-direction: column;
        }}
        .card-number {{ color: #ffd83b; font-size: 30px; font-weight: 600; margin-bottom: 10px; }}
        .card-text {{ font-size: 30px; font-weight: 500; color: #111; line-height: 1.3; overflow: hidden; flex-grow: 1; }}
        .card-dot {{ position: absolute; bottom: 20px; right: 20px; width: 16px; height: 16px; background: #ffd83b; border: 3px solid black; border-radius: 50%; }}
        .card-text p {{ margin: 0; }}
        .card-text strong {{ font-weight: 600; color: #000; }}
    </style>
    </head>
    <body>
        <div id="grid-container">{cards_html}</div>
        <script>
            const textContainers = document.querySelectorAll('.card-text');
            textContainers.forEach(container => {{
                let size = 30;
                while (container.scrollHeight > container.clientHeight+2 && size > 14) {{
                    size -= 1; container.style.fontSize = size + 'px';
                }}
            }});
        </script>
    </body>
    </html>
    """
    print("Generating Transparent Grid PNG...")
    await _take_screenshot(html_content, output_filename)


async def generate_bullet_list(heading, bullet_points, output_filename):
    list_html = ""
    for point in bullet_points:
        md_text = markdown.markdown(point).replace("<p>", "").replace("</p>", "")
        list_html += f"<li>{md_text}</li>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 80px 120px; width: 1280px; height: 720px; box-sizing: border-box; overflow: hidden;
            font-family: 'Outfit', sans-serif;
            background: transparent !important; /* Made transparent */
        }}
        .heading {{ font-size: 65px; font-weight: 500; color: #111; margin-bottom: 40px; margin-top: 0; white-space: nowrap; }}
        ul {{ margin: 0; padding-left: 40px; display: flex; flex-direction: column; gap: 15px; }}
        li {{ font-size: 38px; font-weight: 400; color: #222; line-height: 1.4; }}
        strong {{ font-weight: 600; color: #000; }}
        code {{ background: rgba(240, 240, 240, 0.8); padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
    </style>
    </head>
    <body>
        <h1 class="heading" id="slide-heading">{heading}</h1>
        <ul id="bullet-container">{list_html}</ul>
        <script>
            const heading = document.getElementById('slide-heading');
            let hSize = 65;
            while (heading.scrollWidth > 1040 && hSize > 25) {{
                hSize -= 1; heading.style.fontSize = hSize + 'px';
            }}
            const body = document.body;
            const container = document.getElementById('bullet-container');
            const listItems = container.getElementsByTagName('li');
            let currentSize = 38;
            while (body.scrollHeight > 720 && currentSize > 16) {{
                currentSize -= 1;
                for (let li of listItems) {{ li.style.fontSize = currentSize + 'px'; }}
            }}
        </script>
    </body>
    </html>
    """
    print("Generating Transparent Bullet List PNG...")
    await _take_screenshot(html_content, output_filename)


async def generate_chart_slide(chart_data, x_axis_title, y_axis_title, side_text, output_filename):
    max_val = max(item["value"] for item in chart_data) if chart_data else 10
    tick_count = 5
    rough_step = max_val / tick_count
    mag = 10 ** math.floor(math.log10(rough_step)) if rough_step > 0 else 1
    rel = rough_step / mag

    if rel <= 1: nice_step = 1 * mag
    elif rel <= 2: nice_step = 2 * mag
    elif rel <= 5: nice_step = 5 * mag
    else: nice_step = 10 * mag

    y_max = nice_step * tick_count
    y_steps = [int(nice_step * i) for i in range(1, tick_count + 1)]

    y_labels_html = ""
    grid_lines_html = ""
    for step in y_steps:
        bottom_pct = (step / y_max) * 100
        grid_lines_html += f'<div class="grid-line" style="bottom: {bottom_pct}%;"></div>'
        y_labels_html += f'<div class="y-label" style="bottom: {bottom_pct}%;">{step}</div>'

    bars_html = ""
    for item in chart_data:
        height_pct = (item["value"] / y_max) * 100
        bars_html += f"""
        <div class="bar-wrapper">
            <div class="bar" style="height: {height_pct}%;"></div>
            <div class="x-label">{item["label"]}</div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden;
            font-family: 'Outfit', sans-serif; display: flex; justify-content: center; align-items: center;
            background: transparent !important; /* Made transparent */
        }}
        .slide-container {{ width: 1050px; display: flex; justify-content: space-between; align-items: center; }}
        .chart-section {{ position: relative; width: 450px; height: 380px; margin-left: 60px; }}
        .y-axis-title {{ position: absolute; top: -40px; left: 15px; font-size: 16px; font-weight: 600; color: #111; white-space: nowrap; }}
        .x-axis-title {{ position: absolute; bottom: -80px; right: 0; font-size: 16px; font-weight: 600; color: #111; }}
        .y-axis-container {{ position: absolute; left: -60px; top: 0; width: 50px; height: 100%; pointer-events: none; z-index: 3; }}
        .y-label {{ position: absolute; right: 0; transform: translateY(50%); font-size: 15px; color: #333; font-weight: 500; padding-right: 10px; }}
        .graph-area {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; border-left: 2px solid #111; border-bottom: 2px solid #111; }}
        .grid-line {{ position: absolute; left: 0; width: 100%; border-top: 1px solid rgba(0,0,0,0.15); z-index: 1; }}
        .bars-container {{ position: absolute; left: 0; bottom: 0; width: 100%; height: 100%; display: flex; justify-content: space-evenly; align-items: flex-end; z-index: 2; padding: 0 10px; box-sizing: border-box; }}
        .bar-wrapper {{ position: relative; height: 100%; width: 70px; display: flex; flex-direction: column; justify-content: flex-end; }}
        .bar {{ width: 100%; background-color: #ffd83b; border-radius: 2px 2px 0 0; border: 2px solid #111; border-bottom: none; }}
        .x-label {{ position: absolute; top: 100%; left: 50%; transform: translateX(-50%); margin-top: 10px; font-size: 14px; color: #111; width: 110px; text-align: center; word-wrap: break-word; line-height: 1.2; font-weight: 500; }}
        .text-section {{ width: 440px; font-size: 42px; font-weight: 400; color: #111; line-height: 1.4; }}
    </style>
    </head>
    <body>
        <div class="slide-container">
            <div class="chart-section">
                <div class="y-axis-title">{y_axis_title}</div>
                <div class="y-axis-container">{y_labels_html}</div>
                <div class="graph-area">{grid_lines_html}<div class="bars-container">{bars_html}</div></div>
                <div class="x-axis-title">{x_axis_title}</div>
            </div>
            <div class="text-section">{side_text}</div>
        </div>
        <script>
            const xLabels = document.querySelectorAll('.x-label');
            xLabels.forEach(label => {{
                let size = 14;
                while (label.scrollHeight > 60 && size > 9) {{
                    size -= 1; label.style.fontSize = size + 'px';
                }}
            }});
        </script>
    </body>
    </html>
    """
    print("Generating Transparent Chart Slide PNG...")
    await _take_screenshot(html_content, output_filename)


async def generate_question_slide(text, output_filename):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden;
            display: flex; justify-content: center; align-items: center;
            font-family: 'Outfit', sans-serif; position: relative;
            background: transparent !important; /* Made transparent */
        }}
        .question-mark {{
            position: absolute; font-size: 700px; font-weight: 700; color: rgba(255, 216, 59, 0.4); /* Made slightly translucent */
            line-height: 1; z-index: 1; top: 50%; left: 50%; transform: translate(-50%, -50%); user-select: none;
        }}
        .text-content {{
            position: relative; z-index: 2; font-size: 65px; font-weight: 600; color: #111;
            text-align: center; max-width: 900px; line-height: 1.4;
            text-shadow: 2px 2px 10px rgba(255,255,255,0.8); /* Glow to stand out from video layer */
        }}
    </style>
    </head>
    <body>
        <div class="question-mark">?</div>
        <div class="text-content">{text}</div>
    </body>
    </html>
    """
    print("Generating Transparent Question Slide PNG...")
    await _take_screenshot(html_content, output_filename)


async def generate_slide_from_markdown(md_text, output_filename):
    html_body = markdown.markdown(md_text, extensions=['tables'])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0; padding: 60px 100px; width: 1280px; height: 720px; overflow: hidden;
            font-family: 'Outfit', sans-serif; box-sizing: border-box;
            display: flex; flex-direction: column; justify-content: center;
            background: transparent !important; /* Made transparent */
        }}
        .content-box {{
            background: white; border: 3px solid #111; border-radius: 16px;
            padding: 50px 70px; box-shadow: 8px 8px 0px #ffd83b; max-height: 100%;
            overflow: hidden; box-sizing: border-box;
        }}
        h1 {{ font-size: 55px; font-weight: 700; color: #111; margin: 0 0 20px 0; }}
        h2 {{ font-size: 45px; font-weight: 600; color: #222; margin: 0 0 15px 0; }}
        p {{ font-size: 32px; font-weight: 400; color: #333; line-height: 1.5; margin: 0 0 20px 0; }}
        strong {{ font-weight: 600; color: #111; background-color: #d1e4ff; padding: 2px 8px; border-radius: 6px; }}
        em {{ font-style: italic; color: #555; }}
        ul, ol {{ margin: 0 0 20px 0; padding-left: 40px; }}
        li {{ font-size: 32px; font-weight: 400; color: #333; line-height: 1.5; margin-bottom: 12px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; margin-top: 10px; }}
        th {{ background: #ffecb3; padding: 18px 25px; font-size: 26px; font-weight: 600; color: #111; border-bottom: 2px solid #111; }}
        td {{ padding: 18px 25px; font-size: 24px; color: #333; border-bottom: 1px solid rgba(0,0,0,0.1); }}
        tr:last-child td {{ border-bottom: none; }}
        blockquote {{ border-left: 8px solid #ffd83b; margin: 0 0 20px 0; padding-left: 25px; font-size: 38px; font-style: italic; color: #222; }}
    </style>
    </head>
    <body>
        <div class="content-box">
            {html_body}
        </div>
    </body>
    </html>
    """
    print("Generating Transparent Markdown Slide PNG...")
    await _take_screenshot(html_content, output_filename)


async def generate_emoji_text_slide(text, emojis, output_filename):
    md_text = markdown.markdown(text)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">

    <style>
        body {{
            margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden;
            display: flex; justify-content: center; align-items: center; font-family: 'Outfit', sans-serif;
            position: relative;
            background: transparent !important; /* Made transparent */
        }}
        .text-container {{
            max-width: 900px; text-align: center; font-size: 55px; font-weight: 500; color: #111; line-height: 1.5;
            z-index: 10;
            background: rgba(255, 255, 255, 0.6); /* Added slight frosted backing to ensure readability over videos */
            padding: 30px; border-radius: 20px;
        }}
        strong {{ background-color: #d1e4ff; padding: 5px 15px; border-radius: 8px; font-weight: 600; }}
        .text-container img.emoji {{ height: 1em; width: 1em; margin: 0 .05em 0 .1em; vertical-align: -0.1em; }}
        .floating-emoji {{ position: absolute; font-size: 85px; z-index: 1; display: flex; justify-content: center; align-items: center; opacity: 0.9; }}
        .floating-emoji img.emoji {{ width: 1em; height: 1em; }}
    </style>
    </head>
    <body>
        <div class="text-container" id="text-content">
            {md_text}
        </div>

        <script>
            const container = document.getElementById('text-content');
            let size = 55;
            while (container.scrollHeight > 600 && size > 20) {{
                size -= 1; container.style.fontSize = size + 'px';
            }}

            const emojisList = {json.dumps(emojis)};
            const body = document.body;
            const textBox = container.getBoundingClientRect();
            const padding = 20;
            const emojiSize = 155;

            function isOverlapping(x, y) {{
                const buffer = 40;
                return (
                    x + emojiSize > textBox.left - buffer && x < textBox.right + buffer &&
                    y + emojiSize > textBox.top - buffer && y < textBox.bottom + buffer
                );
            }}

            emojisList.forEach(emojiChar => {{
                const el = document.createElement('div');
                el.className = 'floating-emoji';
                el.textContent = emojiChar;
                body.appendChild(el);

                let x, y;
                let overlapping = true;
                let attempts = 0;

                while(overlapping && attempts < 200) {{
                    x = padding + Math.random() * (1280 - 2 * padding - emojiSize);
                    y = padding + Math.random() * (720 - 2 * padding - emojiSize);
                    overlapping = isOverlapping(x, y);
                    attempts++;
                }}

                const angle = Math.random() * 70 - 35;
                el.style.left = x + 'px';
                el.style.top = y + 'px';
                el.style.transform = `rotate(${{angle}}deg)`;
            }});

            twemoji.parse(document.body);
        </script>
    </body>
    </html>
    """
    print("Generating Transparent Emoji Text Slide PNG...")
    await _take_screenshot(html_content, output_filename)
# Include your HTML generation functions here (generate_banner, generate_slide_from_markdown, etc.)
# Include your compositing functions here (combine_layered_slide, concat_videos, etc.)
