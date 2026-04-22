import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse

from config import LEDGER_JSON_PATH, LEDGER_EXCEL_PATH, LEDGER_OUTPUT_DIR
from ledger_helpers import (
    extract_file_text, ocr_pdf_with_vision, detect_doc_type_by_content,
    extract_case_fields, load_cases_json, save_cases_json,
    find_matching_case_idx, merge_case_data, archive_legal_docs,
)
from routers.chat import load_history, save_history

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.post("/process")
async def process_ledger(files: list[UploadFile] = File(...)):
    files_data = []
    for f in files:
        b = await f.read()
        files_data.append({"name": f.filename, "bytes": b})

    async def event_stream() -> AsyncGenerator[str, None]:
        def send(msg: str) -> str:
            return f"data: {json.dumps({'log': msg}, ensure_ascii=False)}\n\n"

        total = len(files_data)

        # Step 1: 提取文字
        docs = []
        for i, fd in enumerate(files_data):
            yield send(f"**Step 1** 📄 提取文字：`{fd['name']}`")
            text = extract_file_text(fd["bytes"], fd["name"])
            if not text:
                yield send("→ 扫描件，启动视觉 OCR…")
                try:
                    text = ocr_pdf_with_vision(fd["bytes"])
                except Exception as e:
                    yield send(f"⚠️ OCR 失败：{e}")
            yield send(f"→ 提取到 **{len(text)}** 字符")
            doc_type = detect_doc_type_by_content(text) if text else "其他"
            yield send(f"→ 文书类型：**{doc_type}**")
            docs.append({"filename": fd["name"], "text": text, "doc_type": doc_type})

        # Step 2: AI 提取字段
        yield send("**Step 2** 🤖 AI 抽取案件字段…")
        new_case = extract_case_fields(docs, status_fn=lambda m: None)
        yield send(f"→ 案件名称：**{new_case.get('案件名称') or '（未提取到）'}**")
        yield send(f"→ 案由：**{new_case.get('案由') or '（未提取到）'}**")
        yield send(f"→ 标的金额：**{new_case.get('标的金额') or '（未提取到）'}**")

        # Step 3: 比对台账
        yield send("**Step 3** 🔍 比对现有台账…")
        existing_cases = load_cases_json()
        match_idx = find_matching_case_idx(new_case, existing_cases, docs=docs)
        yield send(f"→ {'匹配到第 ' + str(match_idx) + ' 条记录' if match_idx is not None else '未匹配，将新增'}")

        # Step 4: 合并或新增
        if match_idx is not None:
            merged = merge_case_data(existing_cases[match_idx], new_case)
            existing_cases[match_idx] = merged
            case_name = merged.get("案件名称", "")
            stage_summary = "、".join(s["审级"] for s in merged.get("stages", []))
            action_text = f"识别为**已有案件**「{case_name}」，已更新（当前审级：{stage_summary or '无'}）"
        else:
            if not new_case.get("案件名称"):
                new_case["案件名称"] = files_data[0]["name"]
            existing_cases.append(new_case)
            case_name = new_case.get("案件名称", "")
            action_text = f"识别为**新案件**「{case_name}」，已添加至台账"

        # Step 5: 归档文书
        yield send("📁 归档文书文件…")
        archive_dir = archive_legal_docs(files_data, docs, case_name)

        # Step 6: 保存
        yield send("💾 保存台账…")
        save_cases_json(existing_cases)
        Path(LEDGER_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

        # 写 Excel
        try:
            from utils.write_excel import write_ledger as write_legal_ledger
            write_legal_ledger(existing_cases, LEDGER_EXCEL_PATH)
        except Exception as e:
            yield send(f"⚠️ Excel 写入失败：{e}")

        reply = (
            f"✅ {action_text}\n\n"
            f"📊 台账共 **{len(existing_cases)}** 个案件，Excel 已更新。\n\n"
            f"📁 文书已归档至：`{archive_dir}`"
        )
        history = load_history()
        history.append({"role": "assistant", "content": reply})
        save_history(history)

        yield f"data: {json.dumps({'done': True, 'reply': reply, 'case_count': len(existing_cases), 'archive_dir': archive_dir}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/clear")
def clear_ledger():
    p = Path(LEDGER_JSON_PATH)
    if p.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = p.with_name(f"cases_backup_{ts}.json")
        p.rename(backup)
        msg = f"✅ 台账已清空，备份已保存至：`{backup}`"
    else:
        msg = "台账本来就是空的，无需清空。"
    history = load_history()
    history.append({"role": "assistant", "content": msg})
    save_history(history)
    return {"message": msg}


@router.get("/download-excel")
def download_ledger_excel():
    if not os.path.exists(LEDGER_EXCEL_PATH):
        from fastapi import HTTPException
        raise HTTPException(404, "台账文件不存在")
    return FileResponse(
        LEDGER_EXCEL_PATH,
        filename="诉讼案件台账.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
