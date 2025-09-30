import asyncio
import ollama
import re
from typing import Dict, Optional

# The prompt template is defined as a constant for better readability, reusability,
# and to allow for easier parsing by other parts of the application.
DEFAULT_PROMPT_TEMPLATE = (
    "{custom_prompt}"
    "Translate the following text from {source_lang} to {target_lang}. "
    "{instruction_str}"
    "Both {source_lang} and {target_lang} are specified using BCP 47 language codes "
    "(e.g., en, fr-FR, fr-CA, pt-BR, zh-Hant, zh-Hans). "
    "Do not provide any explanation or extra text, just the translation. "
    "The text to translate is: \"{text_to_translate}\""
)

async def translate_text(
    client: ollama.AsyncClient,
    text_to_translate: str,
    source_lang: str,
    target_lang: str,
    model: str,
    glossary: Optional[Dict[str, Dict[str, str]]] = None,
    custom_prompt: str = ""
) -> str:
    """
    使用指定的Ollama模型非同步翻譯單一文本。
    新增 glossary 參數以處理特定字詞的翻譯規則。
    """
    
    prompt_instructions = []
    if glossary and text_to_translate:
        for term, translations in glossary.items():
            # 使用正規表示式進行全字匹配，並忽略大小寫
            if re.search(r'\b' + re.escape(term) + r'\b', text_to_translate, re.IGNORECASE):
                target_translation = translations.get(target_lang)
                if target_translation:
                    # Prompt B: 指定翻譯
                    prompt_instructions.append(f"the term '{term}' MUST be translated as '{target_translation}'")
                else:
                    # Prompt C: 不需翻譯
                    prompt_instructions.append(f"the term '{term}' MUST NOT be translated, keep it as it is")

    instruction_str = ""
    if prompt_instructions:
        instruction_str = "Follow these rules: " + ", and ".join(prompt_instructions) + ". "

    # Use the template to format the prompt, ensuring a space after custom_prompt if it exists.
    prompt = DEFAULT_PROMPT_TEMPLATE.format(
        custom_prompt=f"{custom_prompt} " if custom_prompt else "",
        source_lang=source_lang,
        target_lang=target_lang,
        instruction_str=instruction_str,
        text_to_translate=text_to_translate
    )

    print(f"\nxxxxxxxxxxxxx\n{prompt}\nxxxxxxxxxxxxxx\n")

    try:
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0, "repeat_penalty": 1.1},
        )
        translated_text = response["message"]["content"].strip()
        # 移除可能出現的引號
        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1]
        return translated_text
    except Exception as e:
        print(f"An error occurred while translating '{text_to_translate}': {e}")
        return "" # 發生錯誤時回傳空字串