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
    
    prompt_instructions = []
    if glossary and text_to_translate:
        for term, translations in glossary.items():
            #if re.search(r'\b' + re.escape(term) + r'\b', text_to_translate, re.IGNORECASE):
            if re.search(r'\b' + re.escape(term) + r'\b', text_to_translate):
                target_translation = translations.get(target_lang)
                if target_translation and not pd.isna(target_translation):
                    # 指定翻譯
                    prompt_instructions.append(
                        f"- Always translate '{term}' (case-sensitive) as '{target_translation}'."
                    )
                else:
                    # 保持原樣
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
        f"The text to translate is: \"{text_to_translate}\""
    )

    try:
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.5, "top_p": 0.95},
        )
        translated_text = response["message"]["content"].strip()
        # 移除可能出現的引號
        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1]
        print(f"{translated_text}")
        return translated_text
    except Exception as e:
        print(f"An error occurred while translating '{text_to_translate}': {e}")
        return "" # 發生錯誤時回傳空字串