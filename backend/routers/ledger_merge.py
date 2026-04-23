# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from utils.excel_merger import merge_ledgers

router = APIRouter(prefix="/api/ledger-merge")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MERGED_FILE = DATA_DIR / "合并台账.xlsx"


@router.post("/merge")
async def merge_excel(
    contract_file: UploadFile = File(...),
    purchase_file: Optional[UploadFile] = File(None),
    finance_file: Optional[UploadFile] = File(None),
):
    try:
        contract_bytes = await contract_file.read()
        purchase_bytes = await purchase_file.read() if purchase_file and purchase_file.filename else None
        finance_bytes = await finance_file.read() if finance_file and finance_file.filename else None

        excel_bytes, stats = merge_ledgers(contract_bytes, purchase_bytes, finance_bytes)

        DATA_DIR.mkdir(exist_ok=True)
        MERGED_FILE.write_bytes(excel_bytes)

        return {"ok": True, **stats}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并失败：{e}")


@router.get("/download")
def download_merged():
    if not MERGED_FILE.exists():
        raise HTTPException(status_code=404, detail="合并文件不存在，请先执行合并操作。")
    return FileResponse(
        path=str(MERGED_FILE),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="合并台账.xlsx",
    )
