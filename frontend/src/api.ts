import type { TrainingResult, LedgerPreview, LedgerCaseData } from './types'

const BASE = '/api'

export async function getHistory() {
  const r = await fetch(`${BASE}/chat/history`)
  return r.json()
}

export async function clearHistory() {
  await fetch(`${BASE}/chat/history`, { method: 'DELETE' })
}

export async function sendChat(message: string, useKb: boolean, kbConvId: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, use_kb: useKb, kb_conversation_id: kbConvId }),
  })
  return r.json()
}

// ── 培训统计 ──────────────────────────────────────────────────

export async function extractTraining(
  noticePdf: File,
  signinImg: File,
  department: string,
): Promise<TrainingResult> {
  const form = new FormData()
  form.append('notice_pdf', noticePdf)
  form.append('signin_img', signinImg)
  form.append('department', department)
  const r = await fetch(`${BASE}/training/extract`, { method: 'POST', body: form })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function writeTraining(data: Omit<TrainingResult, 'excel_path' | 'confidence' | 'reflection_note'>) {
  const r = await fetch(`${BASE}/training/write`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function downloadTrainingExcel() {
  window.open(`${BASE}/training/download-excel`, '_blank')
}

// ── 案件台账 ──────────────────────────────────────────────────

export async function extractLedger(
  files: File[],
  onLog: (log: string) => void,
): Promise<LedgerPreview> {
  const form = new FormData()
  for (const f of files) form.append('files', f)

  const resp = await fetch(`${BASE}/ledger/extract`, { method: 'POST', body: form })
  if (!resp.ok) throw new Error(await resp.text())

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let previewData: any = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()!
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const data = JSON.parse(line.slice(6))
        if (data.log) onLog(data.log)
        if (data.preview) previewData = data
      } catch { /* ignore */ }
    }
  }
  return previewData
}

export async function writeLedger(
  caseData: LedgerCaseData,
  matchIdx: number | null,
  archiveDir: string,
): Promise<{ ok: boolean; case_count: number; reply: string }> {
  const r = await fetch(`${BASE}/ledger/write`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_data: caseData, match_idx: matchIdx, archive_dir: archiveDir }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function clearLedger() {
  const r = await fetch(`${BASE}/ledger/clear`, { method: 'POST' })
  return r.json()
}

export function downloadLedgerExcel() {
  window.open(`${BASE}/ledger/download-excel`, '_blank')
}

// ── 授权请示 ──────────────────────────────────────────────────

export async function processAuthRequest(pdfFile: File) {
  const form = new FormData()
  form.append('pdf_file', pdfFile)
  const r = await fetch(`${BASE}/auth-request/process`, { method: 'POST', body: form })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function downloadDocx(base64: string, filename: string) {
  const bytes = atob(base64)
  const arr = new Uint8Array(bytes.length)
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
  const blob = new Blob([arr], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
