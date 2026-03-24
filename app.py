import os
import asyncio
import gradio as gr
from workflow import build_graph

# 1. Install Playwright browsers on startup (Crucial for Hugging Face)
print("Installing Playwright dependencies...")
os.system("playwright install chromium")
os.system("playwright install-deps chromium")

# 2. Set Environment Variables (It is highly recommended to remove these from code and set them in Hugging Face Space Settings -> Variables and Secrets)
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "YOUR_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "YOUR_KEY")

app_workflow = build_graph()

async def generate_course_video(user_prompt: str):
    inputs = {"prompt": user_prompt}
    final_path = None
    
    # Run the graph
    async for output in app_workflow.astream(inputs, stream_mode="updates"):
        for node_name, state_update in output.items():
            print(f"Finished node: {node_name}")
            if node_name == "merge_videos":
                final_path = state_update.get('final_video')
                
    return final_path

def gradio_interface(prompt):
    # Gradio runs sync functions, so we wrap the async execution
    try:
        video_path = asyncio.run(generate_course_video(prompt))
        return video_path
    except Exception as e:
        return f"Error: {str(e)}"

# Build beautiful UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 AI Video Course Generator")
    gr.Markdown("Enter a topic below to generate a fully animated Manim & HTML course video.")
    
    with gr.Row():
        with gr.Column():
            prompt_input = gr.Textbox(label="Course Topic", placeholder="Explain triangles for a math channel...")
            generate_btn = gr.Button("Generate Video", variant="primary")
        
        with gr.Column():
            video_output = gr.Video(label="Generated Course")

    generate_btn.click(fn=gradio_interface, inputs=prompt_input, outputs=video_output)

if __name__ == "__main__":
    demo.launch()
