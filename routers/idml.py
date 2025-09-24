# routers/idml.py
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response

from dependencies import verify_api_token
from idml_processor import extract_idml_to_csv, rebuild_idml_from_csv

# --- Router Setup ---
router = APIRouter(
    prefix="/idml",
    tags=["IDML Tools"],
    dependencies=[Depends(verify_api_token)]
)

UPLOAD_DIR = Path("uploads")

@router.post("/extract")
async def handle_idml_extraction(idml_file: UploadFile = File(...)):
    # Use a more unique temporary filename to avoid potential collisions
    temp_idml_path = UPLOAD_DIR / f"temp_extract_{Path(idml_file.filename).name}"
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await idml_file.read())
        
        csv_content = extract_idml_to_csv(temp_idml_path)
        
        output_filename = f"{Path(idml_file.filename).stem}.csv"
        headers = {'Content-Disposition': f'attachment; filename="{output_filename}"'}
        return Response(content=csv_content, media_type="text/csv", headers=headers)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists():
            temp_idml_path.unlink()

@router.post("/rebuild")
async def handle_idml_rebuild(original_idml: UploadFile = File(...), translated_csv: UploadFile = File(...)):
    temp_idml_path = UPLOAD_DIR / f"temp_rebuild_{Path(original_idml.filename).name}"
    temp_csv_path = UPLOAD_DIR / f"temp_rebuild_{Path(translated_csv.filename).name}"
    
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await original_idml.read())
        with open(temp_csv_path, "wb") as buffer:
            buffer.write(await translated_csv.read())
            
        rebuilt_idml_content = rebuild_idml_from_csv(temp_idml_path, temp_csv_path)
        
        output_filename = f"{Path(original_idml.filename).stem}_translated.idml"
        headers = {'Content-Disposition': f'attachment; filename="{output_filename}"'}
        return Response(content=rebuilt_idml_content, media_type="application/vnd.adobe.indesign-idml-package", headers=headers)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists(): temp_idml_path.unlink()
        if temp_csv_path.exists(): temp_csv_path.unlink()
