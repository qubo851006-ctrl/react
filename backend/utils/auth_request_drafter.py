# -*- coding: utf-8 -*-
import os
import re
import json
import warnings
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

warnings.filterwarnings("ignore")
load_dotenv(override=True)

MODEL_CHAT = os.getenv("MODEL_CHAT", "glm-5-outside")


def _get_client():
    return OpenAI(
        api_key=os.getenv("AIRCHINA_API_KEY"),
        base_url=os.getenv("AIRCHINA_BASE_URL"),
        http_client=httpx.Client(verify=False),
    )


def _parse_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


_EXTRACT_PROMPT_TMPL = (
    "\u4f60\u662f\u4e00\u4e2a\u516c\u6587\u5904\u7406\u4e13\u5bb6\u3002"
    "\u8bf7\u4ece\u4ee5\u4e0b\u5448\u6279\u4ef6\u6587\u672c\u4e2d\u63d0\u53d6\u5173\u952e\u4fe1\u606f"
    "\uff0c\u4ee5JSON\u683c\u5f0f\u8fd4\u56de\u3002\n\n"
    "\u8981\u6c42\uff1a\n"
    "- \u6587\u4ef6\u7f16\u53f7\uff1a\u5982\u300e\u4e2d\u822a\u96c6\u56e2\u8d44\u4ea7\u5475[2024]231\u53f7\u300f"
    "\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u9879\u76ee\u540d\u79f0\uff1a\u9879\u76ee\u5b8c\u6574\u540d\u79f0\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u9879\u76ee\u6982\u51b5\uff1a\u542b\u89c4\u6a21\u3001\u9762\u79ef\u3001\u680b\u6570\u3001\u6295\u8d44"
    "\u60c5\u51b5\u7b49\uff0c\u5c3d\u91cf\u5b8c\u6574\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u603b\u6295\u8d44\u91d1\u989d\uff1a\u5982\u300e\u7ea6X.XX\u4ebf\u5143\u300f\u6216\u300eXXX\u4e07\u5143\u300f"
    "\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u88ab\u6388\u6743\u5355\u4f4d\uff1a\u627f\u529e\u8be5\u9879\u76ee\u7684\u5355\u4f4d/\u90e8\u95e8\u540d\u79f0"
    "\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u6388\u6743\u4e8b\u9879\uff1a\u5217\u8868\u5f62\u5f0f\uff0c\u4ece\u5448\u6279\u4ef6\u4e2d\u63d0\u70bc"
    "\u6240\u6709\u9700\u4e0a\u7ea7\u6388\u6743\u7684\u4e8b\u9879\uff0c\u6bcf\u670330\u5b57\u4ee5\u5185\n"
    "- \u62df\u7a3f\u90e8\u95e8\uff1a\u8d77\u8349\u672c\u6587\u4ef6\u7684\u90e8\u95e8\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u6587\u4ef6\u65e5\u671f\uff1a\u6587\u4ef6\u843d\u6b3e\u65e5\u671f\uff0c\u683c\u5f0fYYYY\u5e74MM\u6708DD\u65e5"
    "\uff0c\u627e\u4e0d\u5230\u586bnull\n"
    "- \u4e3b\u9001\u673a\u6784\uff1a\u5982\u300e\u515a\u7ec4\u300f\u300e\u603b\u7ecf\u7406\u529e\u516c\u4f1a\u300f"
    "\u300e\u8463\u4e8b\u4f1a\u300f\u7b49\uff0c\u627e\u4e0d\u5230\u586bnull\n\n"
    "\u53ea\u8fd4\u56deJSON\uff0c\u4e0d\u8981\u5176\u4ed6\u6587\u5b57\uff1a\n"
    '{"\\u6587\\u4ef6\\u7f16\\u53f7":null,"\\u9879\\u76ee\\u540d\\u79f0":null,'
    '"\\u9879\\u76ee\\u6982\\u51b5":null,"\\u603b\\u6295\\u8d44\\u91d1\\u989d":null,'
    '"\\u88ab\\u6388\\u6743\\u5355\\u4f4d":null,"\\u6388\\u6743\\u4e8b\\u9879":[],'
    '"\\u62df\\u7a3f\\u90e8\\u95e8":null,"\\u6587\\u4ef6\\u65e5\\u671f":null,'
    '"\\u4e3b\\u9001\\u673a\\u6784":null}\n\n'
    "\u5448\u6279\u4ef6\u6587\u672c\uff08\u524d10000\u5b57\uff09\uff1a\n"
    "{text}"
)

_DRAFT_PROMPT_TMPL = (
    "\u4f60\u662f\u4e00\u540d\u7cbe\u901a\u56fd\u6709\u4f01\u4e1a\u516c\u6587\u5199\u4f5c\u7684\u4e13\u5bb6\u3002"
    "\u8bf7\u6839\u636e\u4ee5\u4e0b\u4fe1\u606f\u8d77\u8349\u4e00\u4efd\u6b63\u5f0f\u7684\u6388\u6743\u8bf7\u793a\u3002\n\n"
    "\u8f93\u5165\u4fe1\u606f\uff1a\n"
    "- \u5448\u6279\u4ef6\u6587\u4ef6\u7f16\u53f7\uff1a{wh}\n"
    "- \u9879\u76ee\u540d\u79f0\uff1a{xm}\n"
    "- \u9879\u76ee\u6982\u51b5\uff1a{xg}\n"
    "- \u603b\u6295\u8d44\u91d1\u989d\uff1a{zj}\n"
    "- \u88ab\u6388\u6743\u5355\u4f4d\uff1a{bq}\n"
    "- \u6388\u6743\u4e8b\u9879\uff1a\n{sq}\n"
    "- \u62df\u7a3f\u90e8\u95e8\uff1a{zd}\n"
    "- \u6587\u4ef6\u65e5\u671f\uff1a{rq}\n\n"
    "\u6309\u4ee5\u4e0b\u683c\u5f0f\u751f\u6210\uff0c\u53ea\u8f93\u51fa\u6587\u6863\u6b63\u6587\uff0c\u4e0d\u8981\u6709\u4efb\u4f55\u89e3\u91ca\uff1a\n\n"
    "\u6807\u9898\uff1a\u5173\u4e8e[{xm_short}]\u76f8\u5173\u5de5\u4f5c\u6388\u6743\u7684\u8bf7\u793a\n\n"
    "\u603b\u88c1\uff1a\n\n"
    "\u4e00\u3001\u9879\u76ee\u6982\u51b5\n"
    "[\u5f15\u7528\u5448\u6279\u4ef6\u6587\u4ef6\u7f16\u53f7\uff0c\u7b80\u8ff0\u9879\u76ee\u80cc\u666f\u3001\u89c4\u6a21\u53ca\u6295\u8d44\u60c5\u51b5]\n\n"
    "\u4e8c\u3001\u6388\u6743\u4e8b\u9879\n"
    "1. [\u5c06\u6388\u6743\u4e8b\u9879\u5c55\u5f00\uff0c\u63aa\u8bcd\u6b63\u5f0f\u5b8c\u6574\uff0c\u6709\u5177\u4f53\u6743\u9650\u8fb9\u754c\uff0c\u6bcf\u6761\u4e0d\u5c11\u4e8e30\u5b57]\n"
    "2. ...\n\n"
    "\u4e09\u3001\u8bf7\u793a\u610f\u89c1\n"
    "\u4ee5\u4e0a\u8bf7\u793a\u59a5\u5426\uff0c\u8bf7\u6279\u793a\u3002\n\n"
    "{zd}\n"
    "{rq}"
)


def extract_approval_info(pdf_text):
    prompt = _EXTRACT_PROMPT_TMPL.replace("{text}", pdf_text[:10000])
    resp = _get_client().chat.completions.create(
        model=MODEL_CHAT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.1,
    )
    try:
        return _parse_json(resp.choices[0].message.content)
    except Exception:
        return {
            "\u6587\u4ef6\u7f16\u53f7": None,
            "\u9879\u76ee\u540d\u79f0": None,
            "\u9879\u76ee\u6982\u51b5": None,
            "\u603b\u6295\u8d44\u91d1\u989d": None,
            "\u88ab\u6388\u6743\u5355\u4f4d": None,
            "\u6388\u6743\u4e8b\u9879": [],
            "\u62df\u7a3f\u90e8\u95e8": None,
            "\u6587\u4ef6\u65e5\u671f": None,
            "\u4e3b\u9001\u673a\u6784": None,
        }


def draft_auth_request(info):
    items = info.get("\u6388\u6743\u4e8b\u9879") or []
    items_text = "\n".join(
        "{0}. {1}".format(i + 1, item) for i, item in enumerate(items)
    ) if items else "\uff08\u5f85\u8865\u5145\uff09"

    xm = info.get("\u9879\u76ee\u540d\u79f0") or "\uff08\u672a\u63d0\u53d6\u5230\uff09"
    prompt = (
        _DRAFT_PROMPT_TMPL
        .replace("{wh}", info.get("\u6587\u4ef6\u7f16\u53f7") or "\uff08\u672a\u63d0\u53d6\u5230\uff09")
        .replace("{xm}", xm)
        .replace("{xm_short}", xm[:10] if len(xm) > 10 else xm)
        .replace("{xg}", info.get("\u9879\u76ee\u6982\u51b5") or "\uff08\u672a\u63d0\u53d6\u5230\uff09")
        .replace("{zj}", info.get("\u603b\u6295\u8d44\u91d1\u989d") or "\uff08\u672a\u63d0\u53d6\u5230\uff09")
        .replace("{bq}", info.get("\u88ab\u6388\u6743\u5355\u4f4d") or "\uff08\u672a\u63d0\u53d6\u5230\uff09")
        .replace("{sq}", items_text)
        .replace("{zd}", info.get("\u62df\u7a3f\u90e8\u95e8") or "\uff08\u62df\u7a3f\u90e8\u95e8\uff09")
        .replace("{rq}", info.get("\u6587\u4ef6\u65e5\u671f") or "\uff08\u6587\u4ef6\u65e5\u671f\uff09")
    )
    resp = _get_client().chat.completions.create(
        model=MODEL_CHAT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def save_as_docx(content, output_path):
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin   = Cm(3.17)
        section.right_margin  = Cm(3.17)

    for line in content.splitlines():
        line_s = line.strip()
        if not line_s:
            doc.add_paragraph("")
            continue

        # title line
        if line_s.startswith("\u6807\u9898\uff1a"):
            title_text = line_s[3:].strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(title_text)
            run.bold = True
            run.font.size = Pt(16)

        # section heading (一、二、三、)
        elif re.match(r"^[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\u3001", line_s):
            p = doc.add_paragraph()
            run = p.add_run(line_s)
            run.bold = True
            run.font.size = Pt(12)

        # numbered list (1. 2. ...)
        elif re.match(r"^\d+\.", line_s):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.add_run(line_s).font.size = Pt(12)

        else:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.add_run(line_s).font.size = Pt(12)

    doc.save(output_path)
