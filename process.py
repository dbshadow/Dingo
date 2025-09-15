import asyncio
import pandas as pd
import ollama
import json
from pathlib import Path
from translator import translate_text
from fastapi import WebSocket

async def send_ws_message(websocket: WebSocket, msg_type: str, content: dict):
    """輔助函式，用於發送JSON格式的WebSocket訊息"""
    if not websocket:
        return
    message = {"type": msg_type, "payload": content}
    await websocket.send_text(json.dumps(message))

async def process_csv(
    csv_path: Path,
    source_lang: str,
    target_lang: str,
    ollama_host: str,
    model: str,
    batch_size: int,
    overwrite: bool,
    websocket: WebSocket = None
):
    """
    處理CSV翻譯的核心邏輯。
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        await send_ws_message(websocket, 'error', {"message": f"Error reading CSV file: {e}"})
        return

    if 'source' not in df.columns:
        await send_ws_message(websocket, 'error', {"message": "CSV file must contain a 'source' column."})
        return

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
    if total_to_translate == 0:
        await send_ws_message(websocket, 'log', {"message": "No empty target fields to translate. All done!"})
        await send_ws_message(websocket, 'progress', {
            "csv_data": df.to_csv(index=False),
            "processed": 0,
            "total": 0
        })
        return

    await send_ws_message(websocket, 'log', {"message": f"Found {total_to_translate} texts to translate..."})

    client = ollama.AsyncClient(host=ollama_host)
    output_path = csv_path.parent / f"{csv_path.stem}_translated.csv"
    processed_count = 0

    for i in range(0, total_to_translate, batch_size):
        batch_texts = texts_to_translate[i:i + batch_size]
        batch_indices = indices_to_update[i:i + batch_size]
        
        start_num = i + 1
        end_num = min(i + batch_size, total_to_translate)
        await send_ws_message(websocket, 'log', {"message": f"--- Translating batch {start_num}-{end_num} of {total_to_translate} ---"})

        tasks = [
            translate_text(client, text, source_lang, target_lang, model)
            for text in batch_texts
        ]

        batch_results = await asyncio.gather(*tasks)
        df.loc[batch_indices, 'target'] = batch_results
        processed_count += len(batch_results)

        try:
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            await send_ws_message(websocket, 'log', {"message": f"Progress for batch {start_num}-{end_num} saved."})
            await send_ws_message(websocket, 'progress', {
                "csv_data": df.to_csv(index=False),
                "processed": processed_count,
                "total": total_to_translate
            })
        except Exception as e:
            await send_ws_message(websocket, 'error', {"message": f"Error writing to CSV file: {e}"})
            return

    await send_ws_message(websocket, 'log', {"message": "\nTranslation complete. Final results saved."})