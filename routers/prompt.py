# routers/prompt.py
from fastapi import APIRouter
import re

from translator import translate_text

router = APIRouter(
    prefix="/prompt",
    tags=["Prompt Management"]
)

@router.get("/default")
async def get_default_prompt():
    """
    Returns the default prompt template used by the translator.
    """
    # This is a bit of a hack, but it's the most reliable way to get the prompt
    # without duplicating the code. We can get the source code of the function.
    import inspect
    source_code = inspect.getsource(translate_text)

    # Extract the prompt string using regex
    prompt_match = re.search(r'prompt = \((.*?)\)', source_code, re.DOTALL)
    if not prompt_match:
        return {"template": "Could not extract prompt template."}

    prompt_template = prompt_match.group(1)

    # Clean up the f-string formatting and extra quotes/indentation
    prompt_template = re.sub(r'f"""|f"|"""|"', '', prompt_template)
    prompt_template = re.sub(r'\s*\n\s*', ' ', prompt_template) # Replace newlines and surrounding whitespace with a single space
    prompt_template = prompt_template.strip()
    
    # Replace the f-string variables with placeholders
    prompt_template = prompt_template.replace("{instruction_str}", "{glossary_rules}")
    
    return {"template": prompt_template}
