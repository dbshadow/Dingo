# routers/prompt.py
from fastapi import APIRouter
import re

# Import the template directly, no need for translate_text anymore
from translator import DEFAULT_PROMPT_TEMPLATE

router = APIRouter(
    prefix="/prompt",
    tags=["Prompt Management"]
)

@router.get("/default")
async def get_default_prompt():
    """
    Returns the default prompt template used by the translator.
    """
    # The template is now directly imported.
    # Python's string literal concatenation makes it a single line.
    # We can make it more readable for the UI.
    
    # Create a display version by replacing placeholders and adding line breaks.
    # The template is a single line, so we add newlines for UI readability.
    display_template = DEFAULT_PROMPT_TEMPLATE.replace("{custom_prompt}", "{custom_prompt}")
    display_template = display_template.replace(". ", ".\n")
    display_template = display_template.replace("{instruction_str}", "{glossary_rules}")
    
    # Replace the final part for a cleaner template view.
    display_template = display_template.replace(
        'The text to translate is: "{text_to_translate}"', 
        'The text to translate is: "..."'
    )

    # Add a newline before the glossary rules for better separation
    display_template = display_template.replace("{glossary_rules}", "\n{glossary_rules}")

    return {"template": display_template}
