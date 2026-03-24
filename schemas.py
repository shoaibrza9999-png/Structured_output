from typing import Annotated, List, Literal, Union, TypedDict
from pydantic import BaseModel, Field
import operator

# Output Schemas
class ThinkingPlan(BaseModel):
    animation_plan: str = Field(description="Strictly formatted timeline...")
    required_functions: List[str] = Field(description="List of exact Manim functions.")

class FallbackSlide(BaseModel):
    voice: str
    md_text: str

# TypedDicts for LangGraph State
class ManimSlideArgs(TypedDict):
    template_name: Literal["ManimSlide"]
    voice: str
    prompt: str

class MarkdownSlideArgs(TypedDict):
    template_name: Literal["MarkdownSlide"]
    voice: str
    md_text: str

SubSlide = Union[MarkdownSlideArgs, ManimSlideArgs] # Add your other slide types here

class IntroSlideArgs(TypedDict):
    voice: str
    heading: str
    image_prompt: str

class intro_scene_output(TypedDict):
    intro_slide: IntroSlideArgs
    additional_slides: List[SubSlide]

class topic_scene_output(TypedDict):
    banner_slide: dict
    additional_slides: List[SubSlide]

class GraphState(TypedDict):
    prompt: str
    introduction: str
    topics: List[str]
    theme_color: str
    clips: Annotated[List[tuple[int, str]], operator.add]
    final_video: str

class SceneState(TypedDict):
    introduction: str
    topics: List[str]
    current_index: int
    topic_text: str
