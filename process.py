import asyncio
import pandas as pd
import ollama
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from translator import translate_text
from idml_processor import extract_idml_to_csv
from typing import Callable, Awaitable, Dict

# Define the type for the progress callback function
ProgressCallback = Callable[[int, int], Awaitable[None]]

def load_glossary(glossary_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Loads a glossary from a CSV file into a dictionary format.
    The first column should be 'English' or the base language for indexing.
    """
    if not glossary_path or not glossary_path.exists():
        return None
    try:
        glossary_df = pd.read_csv(glossary_path)
        glossary_df = glossary_df.where(pd.notna(glossary_df), None)
        
        english_col = glossary_df.columns[0]
        if english_col != 'en':
            print(f"Warning: Glossary's first column is '{english_col}', not 'en'. Using it as the base language.")

        glossary_df = glossary_df.set_index(english_col)
        glossary_dict = glossary_df.to_dict('index')
        return glossary_dict
    except Exception as e:
        print(f"Error loading glossary from {glossary_path}: {e}")
        return None

async def process_csv(
    csv_path: Path,
    ollama_host: str,
    model: str,
    batch_size: int,
    progress_callback: ProgressCallback = None,
    glossary_path: Path | None = None
):
    """
    Core logic for CSV translation. Languages are determined by the CSV headers.
    Progress is reported via a callback. CancelledError will be propagated to the caller.
    """
    glossary_dict = load_glossary(glossary_path)

    try:
        df = pd.read_csv(csv_path, dtype=str).fillna('')
    except Exception as e:
        print(f"Error reading CSV {csv_path}: {e}")
        raise

    if len(df.columns) < 2:
        raise ValueError("CSV file must contain at least two columns: one for the source language and at least one for a target language.")

    # --- NEW: Validate headers to prevent misuse of IDML-extracted CSVs ---
    for header in df.columns:
        if header.lower() in ['source', 'target']:
            raise ValueError(
                f"Header contains '{header}', which is not allowed. "
                "This seems to be an IDML-extracted file. Please use BCP-47 language codes (e.g., 'en', 'de') as headers for the CSV Translator."
            )

    source_lang = df.columns[0]
    target_langs = df.columns[1:]
    source_col_name = source_lang

    client = ollama.AsyncClient(host=ollama_host)
    
    # Calculate total number of cells to translate for progress tracking
    total_to_translate = 0
    for target_lang in target_langs:
        if target_lang not in df.columns:
            df[target_lang] = ''
        total_to_translate += int((df[target_lang] == '').sum())

    if progress_callback:
        await progress_callback(0, total_to_translate)

    processed_count = 0
    processed_filepath = csv_path.with_name(f"{csv_path.stem}_processed.csv")

    for target_lang in target_langs:
        target_col_name = target_lang
        
        # Ensure target column exists
        if target_col_name not in df.columns:
            df[target_col_name] = ''

        # Identify rows that need translation for the current target language
        rows_to_process_mask = (df[target_col_name] == '') & (df[source_col_name] != '')
        indices_to_update = df.index[rows_to_process_mask]
        texts_to_translate = df.loc[indices_to_update, source_col_name].tolist()

        if not texts_to_translate:
            continue

        for i in range(0, len(texts_to_translate), batch_size):
            batch_texts = texts_to_translate[i:i + batch_size]
            batch_indices = indices_to_update[i:i + batch_size]
            
            tasks = [
                translate_text(client, text, source_lang, target_lang, model, glossary=glossary_dict)
                for text in batch_texts
            ]
            
            batch_results = await asyncio.gather(*tasks)
            
            df.loc[batch_indices, target_col_name] = batch_results
            processed_count += len(batch_results)

            try:
                df.to_csv(processed_filepath, index=False, encoding='utf-8-sig')
                if progress_callback:
                    await progress_callback(processed_count, total_to_translate)
            except Exception as e:
                print(f"Error writing to CSV file {processed_filepath}: {e}")
                raise
    
    # Final save to ensure the file exists even if no translations were needed
    if not processed_filepath.exists():
        df.to_csv(processed_filepath, index=False, encoding='utf-8-sig')