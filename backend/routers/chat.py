import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
import httpx

from config import MODEL_CHAT, CHAT_HISTORY_PATH, ZHISHU_API_KEY, ZHISHU_BASE_URL
from llm_client import get_llm_client

router = APIRouter(prefix="/api/chat", tags=["chat"])


def load_history() -> list:
    p = Path(CHAT_HISTORY_PATH)
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(messages: list):
    try:
        with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@router.get("/history")
def get_history():
    saved = load_history()
    if not saved:
        saved = [{
            "role": "assistant",
            "content": "你好！我是**培训统计助手**，可以帮您完成培训签到统计和文件归档，也可以回答您的各类问题。"
        }]
    return {"messages": saved}


@router.delete("/history")
def clear_history():
    save_history([])
    return {"ok": True}


class ChatRequest(BaseModel):
    message: str
    use_kb: bool = False
    kb_conversation_id: str = ""


@router.post("")
def chat(req: ChatRequest):
    history = load_history()

    # 知识库模式
    if req.use_kb:
        try:
            url = f"{ZHISHU_BASE_URL}/chat-messages"
            headers = {
                "Authorization": f"Bearer {ZHISHU_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": req.message,
                "inputs": {},
                "response_mode": "blocking",
                "user": "training-manager",
                "conversation_id": req.kb_conversation_id,
            }
            resp = httpx.post(url, json=payload, headers=headers, verify=False, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get("answer", "（知识库未返回内容）")
            new_conv_id = data.get("conversation_id", "")
            history.append({"role": "user", "content": req.message})
            history.append({"role": "assistant", "content": reply})
            save_history(history)
            return {"reply": reply, "next_stage": "idle", "kb_conversation_id": new_conv_id}
        except Exception as e:
            reply = f"❌ 知识库查询失败：{e}"
            history.append({"role": "user", "content": req.message})
            history.append({"role": "assistant", "content": reply})
            save_history(history)
            return {"reply": reply, "next_stage": "idle", "kb_conversation_id": ""}

    client = get_llm_client()

    # 意图识别
    def detect_intent(system_content: str) -> bool:
        resp = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": req.message},
            ],
            max_tokens=5,
        )
        return resp.choices[0].message.content.strip().upper().startswith("Y")

    # 下载意图优先检测（必须在处理类意图之前，避免被误拦截）
    if detect_intent(
        '你是一个意图识别助手。判断用户的消息是否表达了想要下载或导出培训统计表、培训台账、培训记录Excel的意图。'
        '关键词包括：下载、导出、获取、统计表、培训台账、培训记录、Excel。'
        '注意：如果用户说的是"导出培训台账"、"下载统计表"、"获取培训Excel"等，应判断为YES。'
        '只回复 YES 或 NO。'
    ):
        reply = "📥 正在为您打开培训统计表下载…"
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        save_history(history)
        return {"reply": reply, "next_stage": "download_training_excel", "kb_conversation_id": ""}

    if detect_intent(
        '你是一个意图识别助手。判断用户的消息是否表达了想要下载或导出案件台账、诉讼台账Excel的意图。'
        '关键词包括：下载、导出、获取、案件台账、诉讼台账、台账Excel。'
        '注意：如果用户说的是"导出案件台账"、"下载台账"等，应判断为YES。'
        '只回复 YES 或 NO。'
    ):
        reply = "📥 正在为您打开案件台账下载…"
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        save_history(history)
        return {"reply": reply, "next_stage": "download_ledger_excel", "kb_conversation_id": ""}

    if detect_intent(
        '你是一个意图识别助手。判断用户的消息是否表达了需要进行培训统计或归档处理的意图。'
        '包括但不限于：刚组织完培训想记录、要统计签到人数、需要归档培训文件、上传培训材料等。'
        '注意：纯粹的下载/导出请求不算，只有涉及上传文件、新增记录才算YES。只回复 YES 或 NO。'
    ):
        reply = (
            "好的！请上传以下两个文件：\n\n"
            "- 📄 **培训通知**（PDF 格式）\n"
            "- ✍️ **签到表**（图片格式：JPG / PNG）"
        )
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        save_history(history)
        return {"reply": reply, "next_stage": "waiting_files", "kb_conversation_id": ""}

    if detect_intent(
        '你是一个意图识别助手。判断用户的消息是否表达了需要生成案件台账、整理诉讼案件材料、'
        '提取案件信息或生成法务台账的意图。注意：纯粹的下载/导出请求不算，只有涉及上传文书、新增案件才算YES。只回复 YES 或 NO。'
    ):
        reply = (
            "好的！请上传案件的法律文书文件（支持 **PDF / DOCX / DOC**，可多选）。\n\n"
            "系统会自动识别文书类型，并判断是否为台账中的已有案件：\n"
            "- 已有案件：追加审级处理结果或更新执行信息\n"
            "- 新案件：在台账末尾新增一行"
        )
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        save_history(history)
        return {"reply": reply, "next_stage": "waiting_ledger_files", "kb_conversation_id": ""}

    if detect_intent(
        '你是一个意图识别助手。判断用户的消息是否表达了需要起草授权请示、'
        '根据呈批件生成授权文件、或处理项目授权相关公文的意图。只回复 YES 或 NO。'
    ):
        reply = (
            "好的！请上传**呈批件 PDF**，系统将自动提取关键信息并生成授权请示 Word 文档。\n\n"
            "- 支持文字版 PDF（直接提取）\n"
            "- 支持扫描版 PDF（自动 OCR 识别）"
        )
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": reply})
        save_history(history)
        return {"reply": reply, "next_stage": "waiting_auth_file", "kb_conversation_id": ""}

    # 通用对话
    system_prompt = (
        '你是一个培训统计助手，服务于企业内部培训管理工作。'
        '你可以回答用户的各类问题，也可以帮助用户完成培训签到统计和文件归档。'
        '重要提示：这是一个网页应用，如果用户想进行培训统计，请引导他们点击左侧的技能卡片，或直接说出需求即可自动触发。'
        '不要描述不存在的按钮或附件功能。回答简洁友好，使用中文。'
    )
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})
    resp = client.chat.completions.create(model=MODEL_CHAT, messages=messages)
    reply = resp.choices[0].message.content.strip()

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    save_history(history)
    return {"reply": reply, "next_stage": "idle", "kb_conversation_id": ""}
