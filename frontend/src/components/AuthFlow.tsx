import { useState, useRef } from 'react'
import { processAuthRequest, downloadDocx } from '../api'
import ReactMarkdown from 'react-markdown'

interface Props {
  onComplete: (reply: string) => void
  onCancel: () => void
}

export default function AuthFlow({ onComplete, onCancel }: Props) {
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<{ content: string; docx_base64: string; filename: string } | null>(null)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleProcess() {
    if (!pdfFile) return
    setProcessing(true)
    setError('')
    try {
      const res = await processAuthRequest(pdfFile)
      setResult(res)
    } catch (e: any) {
      setError(e.message || '处理失败')
    } finally {
      setProcessing(false)
    }
  }

  if (processing && !result) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="flex items-center gap-3 text-slate-300">
          <div className="animate-spin w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full" />
          <div>
            <div className="text-sm">正在生成授权请示…</div>
            <div className="text-xs text-slate-500 mt-0.5">提取字段 → AI起草 → 生成Word</div>
          </div>
        </div>
      </div>
    )
  }

  if (result) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="text-green-400 font-medium mb-4">✅ 授权请示已生成</div>
        <div className="bg-slate-900/60 rounded-xl p-4 max-h-80 overflow-y-auto mb-4">
          <div className="prose prose-sm prose-invert max-w-none prose-p:my-1">
            <ReactMarkdown>{result.content}</ReactMarkdown>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadDocx(result.docx_base64, result.filename)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg transition-colors"
          >
            📥 下载 Word 文档
          </button>
          <button
            onClick={() => onComplete(`✅ 授权请示已生成：${result.filename}`)}
            className="px-4 py-2 text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            完成
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
      <div className="text-sm font-medium text-slate-300 mb-3">请上传呈批件（PDF 格式）</div>
      {error && <div className="text-red-400 text-sm mb-3">❌ {error}</div>}

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setPdfFile(f) }}
        className={`
          border-2 border-dashed rounded-xl p-8 cursor-pointer text-center transition-all mb-4
          ${drag ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-600 hover:border-slate-500'}
          ${pdfFile ? 'border-green-500/50 bg-green-500/5' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={e => e.target.files?.[0] && setPdfFile(e.target.files[0])}
        />
        {pdfFile ? (
          <>
            <div className="text-green-400 text-2xl mb-2">✓</div>
            <div className="text-sm text-slate-300">{pdfFile.name}</div>
            <div className="text-xs text-slate-500 mt-1">{(pdfFile.size / 1024).toFixed(0)} KB</div>
          </>
        ) : (
          <>
            <div className="text-3xl mb-2">📄</div>
            <div className="text-sm text-slate-400">点击或拖拽上传 PDF</div>
            <div className="text-xs text-slate-500 mt-1">支持文字版和扫描版（自动 OCR）</div>
          </>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleProcess}
          disabled={!pdfFile}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          开始生成
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-2 text-slate-400 hover:text-slate-200 text-sm transition-colors"
        >
          取消
        </button>
      </div>
    </div>
  )
}
