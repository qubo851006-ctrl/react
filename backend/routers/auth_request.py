import os
import io
import base64
import tempfile
from fastapi import APIRouter, UploadFile, File

from routers.chat import load_history, save_history

router = APIRouter(prefix="/api/auth-request", tags=["auth-request"])


@router.post("/process")
async def process_auth_request(pdf_file: UploadFile = File(...)):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from utils.auth_request_drafter import extract_approval_info, draft_auth_request, save_as_docx
    from ledger_helpers import ocr_pdf_with_vision
    import pdfplumber

    pdf_bytes = await pdf_file.read()

    # 提取文字
    pdf_text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pdf_text += t + "\n"
    pdf_text = pdf_text.strip()

    if not pdf_text:
        pdf_text = ocr_pdf_with_vision(pdf_bytes)

    # AI 提取字段
    info = extract_approval_info(pdf_text)

    # 生成请示内容
    auth_content = draft_auth_request(info)

    # 生成 Word 文档并转 base64
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False, prefix="授权请示_") as tmp:
        docx_path = tmp.name
    save_as_docx(auth_content, docx_path)
    with open(docx_path, "rb") as f:
        docx_b64 = base64.b64encode(f.read()).decode()
    os.unlink(docx_path)

    project_name = info.get("项目名称") or "授权请示"

    reply = f"✅ 授权请示已生成！\n\n---\n\n{auth_content}"
    history = load_history()
    history.append({"role": "assistant", "content": reply})
    save_history(history)

    return {
        "content": auth_content,
        "docx_base64": docx_b64,
        "filename": f"授权请示_{project_name[:20]}.docx",
        "info": info,
    }
