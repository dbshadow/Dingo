import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import io

def extract_idml_to_csv(idml_file_path: Path) -> str:
    """
    Extracts all user-facing text from an IDML file and returns it as a CSV string.

    Args:
        idml_file_path: The path to the .idml file.

    Returns:
        A string containing the data in CSV format with 'source' and 'target' columns.
    """
    stories_content = []

    try:
        with zipfile.ZipFile(idml_file_path, 'r') as z:
            # Find all story files
            story_files = [f for f in z.namelist() if f.startswith('Stories/Story_') and f.endswith('.xml')]

            for story_file in story_files:
                with z.open(story_file) as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    # IDML text is within <Content> tags inside <CharacterStyleRange>
                    for content_tag in root.findall(".//CharacterStyleRange/Content"):
                        if content_tag.text:
                            # Append the text content, stripping leading/trailing whitespace
                            stories_content.append(content_tag.text.strip())
    except zipfile.BadZipFile:
        raise ValueError("Invalid IDML file: Not a valid zip archive.")
    except ET.ParseError:
        raise ValueError("Invalid IDML file: Contains corrupted XML.")

    # Filter out empty strings that might result from empty tags
    stories_content = [text for text in stories_content if text]

    if not stories_content:
        return "source,target\n"

    # Create a pandas DataFrame
    df = pd.DataFrame({
        'source': stories_content,
        'target': [''] * len(stories_content) # Add an empty target column
    })

    # Convert DataFrame to CSV string
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    
    return csv_buffer.getvalue()

def rebuild_idml_from_csv(original_idml_path: Path, translated_csv_path: Path) -> bytes:
    """
    Rebuilds an IDML file by replacing text content with translations from a CSV.
    """
    # 1. Read translated CSV into a lookup dictionary
    try:
        df = pd.read_csv(translated_csv_path)
        # Ensure columns exist and handle potential NaN values
        if 'source' not in df.columns or 'target' not in df.columns:
            raise ValueError("CSV must contain 'source' and 'target' columns.")
        df['source'] = df['source'].astype(str).fillna('')
        # Replace NaN in target with empty strings for safe processing
        df['target'] = df['target'].fillna('').astype(str)
        translation_map = dict(zip(df.source, df.target))
    except Exception as e:
        raise ValueError(f"Error reading or processing CSV file: {e}")

    # In-memory buffer for the new zip file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as new_zip:
        with zipfile.ZipFile(original_idml_path, 'r') as old_zip:
            for item in old_zip.infolist():
                # If the item is not a story XML, copy it directly
                if not (item.filename.startswith('Stories/Story_') and item.filename.endswith('.xml')):
                    new_zip.writestr(item, old_zip.read(item.filename))
                    continue

                # If it is a story XML, process it
                tree = ET.parse(old_zip.open(item.filename))
                root = tree.getroot()

                for content_tag in root.findall(".//CharacterStyleRange/Content"):
                    original_text = content_tag.text.strip() if content_tag.text else ""
                    if original_text in translation_map:
                        translated_text = translation_map[original_text]
                        # CRITICAL: Only replace if the translation is a non-empty string
                        if translated_text and isinstance(translated_text, str):
                            content_tag.text = translated_text
                
                # Write the (potentially modified) XML tree to the new zip
                xml_buffer = io.BytesIO()
                tree.write(xml_buffer, encoding='UTF-8', xml_declaration=True)
                new_zip.writestr(item.filename, xml_buffer.getvalue())

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
