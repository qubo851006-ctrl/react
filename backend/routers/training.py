import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse

from config import CHAT_HISTORY_PATH
from routers.chat import load_history, save_history

router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/process")
async def process_training(
    notice_pdf: UploadFile = File(...),
    signin_img: UploadFile = File(...),
    department: str = Form(""),
):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from utils.pdf_reader import extract_pdf_text
    from utils.image_analyzer import count_attendees
    from utils.classifier import classify_training
    from utils.archiver import archive_files
    from utils.excel_writer import append_record, EXCEL_PATH

    notice_bytes = await notice_pdf.read()
    signin_bytes = await signin_img.read()

    with tempfile.TemporaryDirectory() as tmpdir:
        notice_path = os.path.join(tmpdir, notice_pdf.filename)
        signin_path = os.path.join(tmpdir, signin_img.filename)
        with open(notice_path, "wb") as f:
            f.write(notice_bytes)
        with open(signin_path, "wb") as f:
            f.write(signin_bytes)

        notice_text = extract_pdf_text(notice_path)
        sign_in_info = count_attendees(signin_path)
        category = classify_training(notice_text, sign_in_info["topic"])
        archive_path = archive_files(
            notice_path=notice_path,
            sign_in_path=signin_path,
            category=category,
            date=sign_in_info["date"],
            topic=sign_in_info["topic"],
        )
        append_record(
            date=sign_in_info["date"],
            topic=sign_in_info["topic"],
            location=sign_in_info["location"],
            department=department,
            count=sign_in_info["count"],
            category=category,
            archive_path=archive_path,
        )

    result = {
        "topic": sign_in_info["topic"] or "未识别",
        "location": sign_in_info["location"] or "未识别",
        "date": sign_in_info["date"] or "未识别",
        "department": department or "未填写",
        "count": sign_in_info["count"],
        "category": category,
        "archive_path": archive_path,
        "excel_path": EXCEL_PATH,
    }

    # 追加到对话历史
    reply = (
        f"✅ 处理完成！\n\n"
        f"| 字段 | 内容 |\n|------|------|\n"
        f"| 培训主题 | {result['topic']} |\n"
        f"| 培训地点 | {result['location']} |\n"
        f"| 培训日期 | {result['date']} |\n"
        f"| 主办部门 | {result['department']} |\n"
        f"| 参与人数 | **{result['count']} 人** |\n"
        f"| 培训类别 | {result['category']} |\n"
        f"| 归档路径 | `{result['archive_path']}` |"
    )
    history = load_history()
    history.append({"role": "assistant", "content": reply})
    save_history(history)

    return result


@router.get("/download-excel")
def download_excel():
    from utils.excel_writer import EXCEL_PATH
    if not os.path.exists(EXCEL_PATH):
        from fastapi import HTTPException
        raise HTTPException(404, "统计表不存在")
    return FileResponse(
        EXCEL_PATH,
        filename="培训统计表.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
