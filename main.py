import argparse
import asyncio
import pandas as pd
import ollama
from pathlib import Path
from translator import translate_text

async def main():
    """
    主函式，用於解析參數、讀取CSV、執行翻譯並寫入結果。
    """
    parser = argparse.ArgumentParser(description="Translate a CSV file using an Ollama LLM.")
    parser.add_argument("csv_path", type=str, help="Path to the input CSV file.")
    parser.add_argument("source_lang", type=str, help="Source language.")
    parser.add_argument("target_lang", type=str, help="Target language.")
    parser.add_argument("--ollama_host", type=str, default="http://192.168.7.149:11434", help="Ollama host URL.")
    parser.add_argument("--model", type=str, default="gpt-oss:20b", help="Ollama model to use.")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of rows to process before saving.")
    parser.add_argument("--overwrite", action='store_true', help="Overwrite existing translations. If false, only translates rows with empty target.")

    args = parser.parse_args()

    input_path = Path(args.csv_path)
    if not input_path.is_file():
        print(f"Error: File not found at {input_path}")
        return

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if 'source' not in df.columns:
        print("Error: CSV file must contain a 'source' column.")
        return

    if 'target' not in df.columns:
        df['target'] = ""

    # 修正 pandas 讀取空值行為：先填充na再轉str
    df['source'] = df['source'].fillna('').astype(str)
    df['target'] = df['target'].fillna('').astype(str)

    # 根據 overwrite 旗標決定要翻譯的行
    if not args.overwrite:
        print("Overwrite mode is OFF. Only translating rows with empty target.")
        rows_to_process_mask = (df['target'] == '') | (df['target'].isna())
        indices_to_update = df.index[rows_to_process_mask]
        texts_to_translate = df.loc[indices_to_update, 'source'].tolist()
    else:
        print("Overwrite mode is ON. Translating all rows.")
        indices_to_update = df.index
        texts_to_translate = df["source"].tolist()

    total_to_translate = len(texts_to_translate)
    if total_to_translate == 0:
        print("No empty target fields to translate. All done!")
        return
        
    print(f"Found {total_to_translate} texts to translate...")

    client = ollama.AsyncClient(host=args.ollama_host)
    output_path = input_path.parent / f"{input_path.stem}_translated.csv"

    # 以批次方式處理
    for i in range(0, total_to_translate, args.batch_size):
        batch_texts = texts_to_translate[i:i + args.batch_size]
        batch_indices = indices_to_update[i:i + args.batch_size]
        
        start_num = i + 1
        end_num = min(i + args.batch_size, total_to_translate)
        print(f"--- Translating batch {start_num}-{end_num} of {total_to_translate} ---")

        tasks = [
            translate_text(client, text, args.source_lang, args.target_lang, args.model)
            for text in batch_texts
        ]

        batch_results = await asyncio.gather(*tasks)

        # 將批次結果寫回DataFrame
        df.loc[batch_indices, 'target'] = batch_results

        try:
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"Progress for batch {start_num}-{end_num} saved to {output_path}")
        except Exception as e:
            print(f"Error writing to CSV file: {e}")
            return

    print(f"\nTranslation complete. Final results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
