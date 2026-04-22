import { useState, useRef } from 'react'
import { processLedger, downloadLedgerExcel } from '../api'

interface Props {
  onComplete: (reply: string) => void
  onCancel: () => void
}

export default function LedgerFlow({ onComplete, onCancel }: Props) {
  const [files, setFiles] = useState<File[]>([])
  const [logs, setLogs] = useState<string[]>([])
  const [processing, setProcessing] = useState(false)
  const [done, setDone] = useState(false)
  const [result, setResult] = useState<{ reply: string; case_count: number; archive_dir: string } | null>(null)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const logRef = useRef<HTMLDivElement>(null)

  function addFiles(newFiles: FileList | null) {
    if (!newFiles) return
    const arr = Array.from(newFiles).filter(
      f => /\.(pdf|docx|doc)$/i.test(f.name)
    )
    setFiles(prev => {
      const names = new Set(prev.map(f => f.name))
      return [...prev, ...arr.filter(f => !names.has(f.name))]
    })
  }

  async function handleProcess() {
    if (!files.length) return
    setProcessing(true)
    setLogs([])
    setError('')
    try {
      const res = await processLedger(files, log => {
        setLogs(prev => [...prev, log])
        setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50)
      })
      setResult(res)
      setDone(true)
      onComplete(res.reply)
    } catch (e: any) {
      setError(e.message || '处理失败')
      setProcessing(false)
    }
  }

  if (done && result) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="text-green-400 font-medium mb-3">✅ 台账更新完成</div>
        <div className="text-sm text-slate-300 mb-1">共 <span className="text-white font-bold">{result.case_count}</span> 个案件</div>
        <div className="text-xs text-slate-500 mb-4">📁 文书已归档至：{result.archive_dir}</div>
        <button
          onClick={downloadLedgerExcel}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg transition-colors"
        >
          📥 下载台账 Excel
        </button>
      </div>
    )
  }

  if (processing) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="flex items-center gap-2 text-slate-300 text-sm mb-3">
          <div className="animate-spin w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full flex-shrink-0" />
          正在处理文书…
        </div>
        <div
          ref={logRef}
          className="bg-slate-900/60 rounded-lg p-3 h-48 overflow-y-auto font-mono text-xs text-slate-400 space-y-1"
        >
          {logs.map((l, i) => (
            <div key={i} dangerouslySetInnerHTML={{ __html: l.replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-200">$1</strong>').replace(/`(.*?)`/g, '<code class="text-indigo-300">$1</code>') }} />
          ))}
          {!logs.length && <div className="text-slate-600">等待处理…</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
      <div className="text-sm font-medium text-slate-300 mb-3">请上传案件法律文书（PDF / DOCX / DOC，可多选）</div>
      {error && <div className="text-red-400 text-sm mb-3">❌ {error}</div>}

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files) }}
        className={`
          border-2 border-dashed rounded-xl p-6 cursor-pointer text-center transition-all mb-3
          ${drag ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-600 hover:border-slate-500'}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.doc"
          multiple
          className="hidden"
          onChange={e => addFiles(e.target.files)}
        />
        <div className="text-slate-400 text-sm mb-1">📂 点击或拖拽上传文书文件</div>
        <div className="text-slate-500 text-xs">支持 PDF / DOCX / DOC，可多选</div>
      </div>

      {files.length > 0 && (
        <div className="space-y-1 mb-4">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-slate-400 bg-slate-700/40 rounded-lg px-3 py-2">
              <span className="text-green-400">✓</span>
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-slate-500">{(f.size / 1024).toFixed(0)} KB</span>
              <button
                onClick={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                className="text-slate-500 hover:text-red-400 transition-colors"
              >✕</button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleProcess}
          disabled={!files.length}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          开始处理 {files.length > 0 && `（${files.length} 个文件）`}
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
