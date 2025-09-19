import argparse
import asyncio
from pathlib import Path
from process import process_csv

async def main_cli():
    parser = argparse.ArgumentParser(description="Translate a CSV file using an Ollama LLM.")
    parser.add_argument("csv_path", type=str, help="Path to the input CSV file.")
    parser.add_argument("source_lang", type=str, help="Source language.")
    parser.add_argument("target_lang", type=str, help="Target language.")
    parser.add_argument("--ollama_host", type=str, default="http://192.168.7.149:11434", help="Ollama host URL.")
    parser.add_argument("--model", type=str, default="gpt-oss:20b", help="Ollama model to use.")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of rows to process before saving.")
    parser.add_argument("--overwrite", action='store_true', help="Overwrite existing translations. If false, only translates rows with empty target.")
    # 新增的參數
    parser.add_argument("--glossary", type=str, default=None, help="Path to the optional glossary CSV file.")

    args = parser.parse_args()

    input_path = Path(args.csv_path)
    if not input_path.is_file():
        print(f"Error: File not found at {input_path}")
        return

    # 處理可選的 glossary 路徑
    glossary_path = Path(args.glossary) if args.glossary else None
    if glossary_path and not glossary_path.is_file():
        print(f"Error: Glossary file not found at {glossary_path}")
        return

    await process_csv(
        csv_path=input_path,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        ollama_host=args.ollama_host,
        model=args.model,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        glossary_path=glossary_path # 傳遞 glossary 路徑
    )

if __name__ == "__main__":
    asyncio.run(main_cli())