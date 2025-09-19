import asyncio
import pandas as pd
import ollama
from pathlib import Path
from translator import translate_text
from typing import Callable, Awaitable

# 定義回呼函式的類型
ProgressCallback = Callable[[int, int], Awaitable[None]]

async def process_csv(
    csv_path: Path,
    source_lang: str,
    target_lang: str,
    ollama_host: str,
    model: str,
    batch_size: int,
    overwrite: bool,
    progress_callback: ProgressCallback = None
):
    """
    處理CSV翻譯的核心邏輯，進度透過回呼函式報告。
    CancelledError會被向上拋出給調用者處理。
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV {csv_path}: {e}")
        raise

    if 'source' not in df.columns:
        raise ValueError("CSV file must contain a 'source' column.")

    if 'target' not in df.columns:
        df['target'] = ""

    df['source'] = df['source'].fillna('').astype(str)
    df['target'] = df['target'].fillna('').astype(str)

    if not overwrite:
        rows_to_process_mask = (df['target'] == '') | (df['target'].isna())
        indices_to_update = df.index[rows_to_process_mask]
        texts_to_translate = df.loc[indices_to_update, 'source'].tolist()
    else:
        indices_to_update = df.index
        texts_to_translate = df["source"].tolist()

    total_to_translate = len(texts_to_translate)
    
    if progress_callback:
        await progress_callback(0, total_to_translate)

    if total_to_translate == 0:
        return

    client = ollama.AsyncClient(host=ollama_host)
    processed_count = 0

    for i in range(0, total_to_translate, batch_size):
        batch_texts = texts_to_translate[i:i + batch_size]
        batch_indices = indices_to_update[i:i + batch_size]
        
        tasks = [
            translate_text(client, text, source_lang, target_lang, model)
            for text in batch_texts
        ]
        
        # 當此任務被取消時，asyncio.gather會拋出CancelledError
        batch_results = await asyncio.gather(*tasks)
        
        df.loc[batch_indices, 'target'] = batch_results
        processed_count += len(batch_results)

        try:
            # 將進度寫入一個新的檔案，以避免覆蓋原始上傳的檔案
            processed_filepath = csv_path.with_name(f"{csv_path.stem}_processed.csv")
            df.to_csv(processed_filepath, index=False, encoding='utf-8-sig')
            if progress_callback:
                await progress_callback(processed_count, total_to_translate)
        except Exception as e:
            print(f"Error writing to CSV file {processed_filepath}: {e}")
            raise
