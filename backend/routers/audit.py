# -*- coding: utf-8 -*-
import io
import json
import re
import tempfile
from pathlib import Path

import openpyxl
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel

from config import MODEL_CHAT
from llm_client import get_llm_client

router = APIRouter(prefix="/api/audit")


# ── 数据模型 ──────────────────────────────────────────────────────


class AuditRow(BaseModel):
    seq: int
    issue: str
    description: str
    category: str = ""
    domain: str = ""


class DownloadRequest(BaseModel):
    rows: list[AuditRow]
    original_filename: str = "审计问题分析结果"


# ── 工具函数 ──────────────────────────────────────────────────────


def _find_header_row(ws) -> int | None:
    """找到含「发现问题」的标题行，返回行号（1-based）。"""
    for row_idx in range(1, min(ws.max_row + 1, 10)):
        for col_idx in range(1, ws.max_column + 1):
            cell_val = ws.cell(row_idx, col_idx).value
            if cell_val and "发现问题" in str(cell_val):
                return row_idx
    return None


def _col_index(ws, header_row: int, keyword: str) -> int | None:
    """在标题行中找含 keyword 的列号（1-based）。"""
    for col_idx in range(1, ws.max_column + 1):
        val = ws.cell(header_row, col_idx).value
        if val and keyword in str(val):
            return col_idx
    return None


def _extract_rows(wb: openpyxl.Workbook) -> list[dict]:
    """提取第一个 sheet 中的审计发现行数据。"""
    ws = wb.active
    header_row = _find_header_row(ws)
    if header_row is None:
        raise ValueError("未找到包含「发现问题」的标题行，请检查 Excel 格式。")

    seq_col = _col_index(ws, header_row, "序号") or 1
    issue_col = _col_index(ws, header_row, "发现问题")
    desc_col = _col_index(ws, header_row, "问题描述")

    if issue_col is None:
        raise ValueError("未找到「发现问题」列。")

    rows = []
    for row_idx in range(header_row + 1, ws.max_row + 1):
        seq_val = ws.cell(row_idx, seq_col).value
        issue_val = ws.cell(row_idx, issue_col).value
        desc_val = ws.cell(row_idx, desc_col).value if desc_col else ""

        if not issue_val:
            continue

        try:
            seq = int(seq_val) if seq_val is not None else row_idx - header_row
        except (ValueError, TypeError):
            seq = row_idx - header_row

        rows.append({
            "seq": seq,
            "issue": str(issue_val).strip(),
            "description": str(desc_val).strip() if desc_val else "",
        })

    return rows


def _build_prompt(rows: list[dict], categories: list[str], domains: list[str]) -> str:
    rows_json = json.dumps(
        [{"序号": r["seq"], "发现问题": r["issue"], "问题描述": r["description"][:200]}
         for r in rows],
        ensure_ascii=False,
        indent=2,
    )

    # 预置各类别说明（仅对已知类别生成，其余跳过）
    cat_hints = {
        "内控缺陷": "内部控制制度本身设计存在缺失或不合理之处",
        "制度执行": "制度本身合理，但实际执行中未严格落实",
        "资金管理": "涉及资金使用、费用报销、结算支付等",
        "采购管理": "涉及采购程序、供应商资质、评审定标等",
    }
    domain_hints = {
        "工程业务": "工程项目立项、建设、验收等",
        "酒店业务": "酒店日常运营、服务管理等",
        "物业管理": "物业服务、设施维护等",
        "资产管理": "固定资产台账、处置、盘点等",
    }

    cat_lines = "\n".join(
        f"- {c}：{cat_hints[c]}" if c in cat_hints else f"- {c}"
        for c in categories
    )
    domain_lines = "\n".join(
        f"- {d}：{domain_hints[d]}" if d in domain_hints else f"- {d}"
        for d in domains
    )

    return f"""你是企业内部审计专家。请对以下审计发现问题进行分类，共两个独立维度，分别判断。

【维度一：问题类别】
描述问题的性质，从以下选项中选一个最匹配的：{categories}
{cat_lines}

【维度二：业务领域】
描述问题所属的业务板块，从以下选项中选一个最匹配的：{domains}
{domain_lines}

【发现问题列表（JSON）】：
{rows_json}

请严格按如下格式返回，只输出JSON数组，不含任何其他文字：
[{{"序号": 1, "问题类别": "...", "业务领域": "..."}}, ...]"""


def _parse_llm_output(text: str, rows: list[dict]) -> list[dict]:
    """从 LLM 输出中提取 JSON 数组，补全缺失行。"""
    # 尝试提取 JSON 数组
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        raise ValueError(f"LLM 返回格式异常，无法解析 JSON：{text[:200]}")

    parsed = json.loads(match.group())
    result_map = {item["序号"]: item for item in parsed}

    result = []
    for r in rows:
        classified = result_map.get(r["seq"], {})
        result.append({
            **r,
            "category": classified.get("问题类别", ""),
            "domain": classified.get("业务领域", ""),
        })
    return result


# ── 路由 ──────────────────────────────────────────────────────────


@router.post("/analyze")
async def analyze_audit(
    file: UploadFile = File(...),
    categories: str = Form('["内控缺陷","制度执行","资金管理","采购管理"]'),
    domains: str = Form('["工程业务","酒店业务","物业管理","资产管理"]'),
):
    try:
        cats = json.loads(categories)
        doms = json.loads(domains)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"分类参数格式错误：{e}")

    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content))
        rows = _extract_rows(wb)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel 解析失败：{e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Excel 中未找到有效数据行。")

    prompt = _build_prompt(rows, cats, doms)
    try:
        client = get_llm_client()
        resp = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        llm_text = resp.choices[0].message.content or ""
        classified_rows = _parse_llm_output(llm_text, rows)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}")

    return {"rows": classified_rows, "total": len(classified_rows)}


@router.post("/download")
async def download_audit_excel(req: DownloadRequest):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "审计问题分析"

    # 样式定义
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    wrap_align = Alignment(wrap_text=True, vertical="top")

    headers = ["序号", "发现问题", "问题描述", "问题类别", "业务领域"]
    col_widths = [8, 30, 60, 14, 14]

    # 写标题行
    for col_idx, (header, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        ws.column_dimensions[cell.column_letter].width = width

    ws.row_dimensions[1].height = 20

    # 新增类别列的填充色（高亮区分）
    cat_fill = PatternFill("solid", fgColor="EBF5FB")
    dom_fill = PatternFill("solid", fgColor="E9F7EF")

    for row_idx, row in enumerate(req.rows, start=2):
        ws.cell(row_idx, 1, row.seq).alignment = center_align
        ws.cell(row_idx, 2, row.issue).alignment = wrap_align
        ws.cell(row_idx, 3, row.description).alignment = wrap_align
        cat_cell = ws.cell(row_idx, 4, row.category)
        cat_cell.alignment = center_align
        cat_cell.fill = cat_fill
        dom_cell = ws.cell(row_idx, 5, row.domain)
        dom_cell.alignment = center_align
        dom_cell.fill = dom_fill

    # 冻结标题行
    ws.freeze_panes = "A2"

    # 写入临时文件并返回
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    wb.save(tmp_path)

    safe_name = req.original_filename.replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=tmp_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{safe_name}_分类结果.xlsx",
    )
