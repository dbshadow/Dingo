import asyncio
import pandas as pd
import ollama
from pathlib import Path
from translator import translate_text
from typing import Callable, Awaitable, Dict

# 定義回呼函式的類型
ProgressCallback = Callable[[int, int], Awaitable[None]]

def load_glossary(glossary_path: Path) -> Dict[str, Dict[str, str]]:
    """
    從CSV檔案載入對照表並轉換為字典格式。
    第一欄應為 'English' 或作為索引的基準語言。
    """
    if not glossary_path or not glossary_path.exists():
        return None
    try:
        glossary_df = pd.read_csv(glossary_path)
        # 將 NaN 轉換為 None，以便後續 .get() 操作能正確返回 None
        glossary_df = glossary_df.where(pd.notna(glossary_df), None)
        
        # 假設第一欄是英文原文，並將其設為索引
        english_col = glossary_df.columns[0]
        if english_col != 'English':
            print(f"Warning: Glossary's first column is '{english_col}', not 'English'. Using it as the base language.")

        glossary_df = glossary_df.set_index(english_col)
        
        # to_dict('index') 會產生 {index_val: {col1: val1, col2: val2}} 的格式
        glossary_dict = glossary_df.to_dict('index')
        return glossary_dict
    except Exception as e:
        print(f"Error loading glossary from {glossary_path}: {e}")
        return None

async def process_csv(
    csv_path: Path,
    source_lang: str,
    target_lang: str,
    ollama_host: str,
    model: str,
    batch_size: int,
    overwrite: bool,
    progress_callback: ProgressCallback = None,
    glossary_path: Path | None = None
):
    """
    處理CSV翻譯的核心邏輯，進度透過回呼函式報告。
    CancelledError會被向上拋出給調用者處理。
    """
    glossary_dict = load_glossary(glossary_path)

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
            translate_text(client, text, source_lang, target_lang, model, glossary=glossary_dict)
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