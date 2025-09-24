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
    Core logic for CSV translation. Progress is reported via a callback.
    CancelledError will be propagated to the caller.
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
        # Even if there's nothing to translate, we need to ensure the processed file exists for the download endpoint.
        processed_filepath = csv_path.with_name(f"{csv_path.stem}_processed.csv")
        if not processed_filepath.exists():
            df.to_csv(processed_filepath, index=False, encoding='utf-8-sig')
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
        
        batch_results = await asyncio.gather(*tasks)
        
        df.loc[batch_indices, 'target'] = batch_results
        processed_count += len(batch_results)

        try:
            processed_filepath = csv_path.with_name(f"{csv_path.stem}_processed.csv")
            df.to_csv(processed_filepath, index=False, encoding='utf-8-sig')
            if progress_callback:
                await progress_callback(processed_count, total_to_translate)
        except Exception as e:
            print(f"Error writing to CSV file {processed_filepath}: {e}")
            raise

def _cleanup_temp_files(temp_csv_path: Path, translated_csv_path: Path):
    """Safely remove temporary files."""
    print("Cleaning up temporary files...")
    try:
        if temp_csv_path.exists():
            temp_csv_path.unlink()
        if translated_csv_path.exists():
            translated_csv_path.unlink()
    except OSError as e:
        print(f"Error during cleanup: {e}")


async def process_idml(
    idml_path: Path,
    source_lang: str,
    target_lang: str,
    ollama_host: str,
    model: str,
    batch_size: int,
    overwrite: bool, # Overwrite is implicitly handled by the process
    progress_callback: ProgressCallback = None,
    glossary_path: Path | None = None
):
    """
    Orchestrates the full IDML translation process.
    Intermediate files are preserved on cancellation.
    """
    temp_csv_path = idml_path.with_name(f"{idml_path.stem}.csv")
    translated_csv_path = temp_csv_path.with_name(f"{temp_csv_path.stem}_processed.csv")
    final_idml_path = idml_path.with_name(f"{idml_path.stem}_processed.idml")

    try:
        # 1. Extract IDML to a temporary CSV file
        print(f"Extracting IDML: {idml_path}")
        csv_content = extract_idml_to_csv(idml_path)
        with open(temp_csv_path, 'w', encoding='utf-8-sig') as f:
            f.write(csv_content)
        print(f"Temporary CSV created at: {temp_csv_path}")

        # 2. Translate the temporary CSV using the existing process_csv function
        print("Starting translation of extracted CSV...")
        await process_csv(
            csv_path=temp_csv_path,
            source_lang=source_lang,
            target_lang=target_lang,
            ollama_host=ollama_host,
            model=model,
            batch_size=batch_size,
            overwrite=True,  # Always overwrite for the IDML process
            progress_callback=progress_callback,
            glossary_path=glossary_path
        )
        print("CSV translation completed.")

        # 3. Rebuild the IDML from the translated CSV
        if not translated_csv_path.exists():
            raise FileNotFoundError(f"Translated CSV file not found at {translated_csv_path}")
        
        print("Rebuilding IDML file...")
        rebuilt_idml_content = rebuild_idml_from_csv(
            original_idml_path=idml_path,
            translated_csv_path=translated_csv_path
        )
        
        # 4. Save the final IDML file
        with open(final_idml_path, 'wb') as f:
            f.write(rebuilt_idml_content)
        print(f"Rebuilt IDML saved to: {final_idml_path}")

        # 5. Clean up temporary files on success
        _cleanup_temp_files(temp_csv_path, translated_csv_path)

    except asyncio.CancelledError:
        print("IDML processing was cancelled. Intermediate files will be preserved.")
        # Re-raise the exception to be caught by the background worker
        raise
    except Exception as e:
        print(f"An error occurred during IDML processing: {e}")
        # Clean up on other errors
        _cleanup_temp_files(temp_csv_path, translated_csv_path)
        # Re-raise the exception to be caught by the background worker
        raise