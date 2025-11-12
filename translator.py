import asyncio
import ollama
import re
import pandas as pd
from typing import Dict, Optional

async def translate_text(
    client: ollama.AsyncClient,
    text_to_translate: str,
    source_lang: str,
    target_lang: str,
    model: str,
    glossary: Optional[Dict[str, Dict[str, str]]] = None
) -> str:
    """
    使用指定的Ollama模型非同步翻譯單一文本。
    新增 glossary 參數以處理特定字詞的翻譯規則。
    """
    # --- Start of new whitespace handling ---
    # 1. Manually handle whitespace to ensure reliable formatting
    stripped_text = text_to_translate.strip()
    if not stripped_text:
        return text_to_translate # Return original string if it's all whitespace

    leading_whitespace = text_to_translate[:len(text_to_translate) - len(text_to_translate.lstrip())]
    trailing_whitespace = text_to_translate[len(text_to_translate.rstrip()):]
    # --- End of new whitespace handling ---

    prompt_instructions = []
    if glossary and stripped_text:
        for term, translations in glossary.items():
            if re.search(r'\b' + re.escape(term) + r'\b', stripped_text):
                target_translation = translations.get(target_lang)
                if target_translation and not pd.isna(target_translation):
                    prompt_instructions.append(
                        f"- Always translate '{term}' (case-sensitive) as '{target_translation}'."
                    )
                else:
                    prompt_instructions.append(
                        f"- Do not translate '{term}'; keep it exactly as written, including its original capitalization (case-sensitive)."
                    )

    general_rules = (
        "- Keep all Arabic numerals (0–9) unchanged.\n"
        "- Keep terms with numbers + units unchanged (e.g., mW, mHz, Mbps, dBm, GHz, MHz).\n"
        "- Keep acronyms/abbreviations in ALL CAPS unchanged (e.g., SSID, WPS, QoS).\n"
    )

    if prompt_instructions:
        rules_section = (
            "Follow these rules in order of priority:\n\n"
            "1. Glossary rules (highest priority):\n"
            + "\n".join(prompt_instructions)
            + "\n\n"
            "2. Then apply the general non-translation rules:\n"
            + general_rules
        )
    else:
        rules_section = (
            "Follow these non-translation rules:\n\n"
            + general_rules
        )

    prompt = (
        f"Translate the following text from {source_lang} to {target_lang}.\n\n"
        f"{rules_section}\n"
        f"Both {source_lang} and {target_lang} are specified using BCP 47 language codes "
        f"(e.g., en, fr-FR, fr-CA, pt-BR, zh-Hant, zh-Hans).\n"
        f"Do not provide any explanation or extra text, only output the translation.\n\n"
        f"The text to translate is: \"{stripped_text}\"" # Use stripped text for translation
    )

    try:
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.5, "top_p": 0.95},
        )
        translated_text = response["message"]["content"]
        
        # Handle quotes: only remove if LLM added them and original (stripped) text didn't have them.
        if translated_text.startswith('"') and translated_text.endswith('"'):
            if not (stripped_text.startswith('"') and stripped_text.endswith('"')):
                translated_text = translated_text[1:-1]
        
        # Re-apply original whitespace
        final_translation = leading_whitespace + translated_text + trailing_whitespace
        return final_translation

    except Exception as e:
        print(f"An error occurred while translating '{stripped_text}': {e}")
        # On error, return the original text with its whitespace
        return text_to_translate