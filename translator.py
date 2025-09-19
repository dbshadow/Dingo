import asyncio
import ollama

async def translate_text(
    client: ollama.AsyncClient,
    text_to_translate: str,
    source_lang: str,
    target_lang: str,
    model: str,
) -> str:
    """
    使用指定的Ollama模型非同步翻譯單一文本。

    Args:
        client: ollama.AsyncClient 的實例。
        text_to_translate: 要翻譯的文字。
        source_lang: 來源語言。
        target_lang: 目標語言。
        model: 要使用的 Ollama 模型名稱。

    Returns:
        翻譯後的文字。
    """
    prompt = (
        f"Translate the following text from {source_lang} to {target_lang}. "
        f"Both {source_lang} and {target_lang} are specified using BCP 47 language codes "
        f"(e.g., en, fr-FR, fr-CA, pt-BR, zh-Hant, zh-Hans). "
        f"Do not provide any explanation or extra text, just the translation. "
        f"The text to translate is: \"{text_to_translate}\""
    )

    try:
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        translated_text = response["message"]["content"].strip()
        # 移除可能出現的引號
        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1]
        return translated_text
    except Exception as e:
        print(f"An error occurred while translating '{text_to_translate}': {e}")
        return "" # 發生錯誤時回傳空字串
