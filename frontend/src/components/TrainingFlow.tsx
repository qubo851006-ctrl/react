import { useState, useRef } from 'react'
import { processTraining, downloadTrainingExcel } from '../api'
import type { TrainingResult } from '../types'

interface Props {
  onComplete: (reply: string) => void
  onCancel: () => void
}

type Step = 'upload' | 'dept' | 'processing' | 'done'

export default function TrainingFlow({ onComplete, onCancel }: Props) {
  const [step, setStep] = useState<Step>('upload')
  const [noticePdf, setNoticePdf] = useState<File | null>(null)
  const [signinImg, setSigninImg] = useState<File | null>(null)
  const [department, setDepartment] = useState('')
  const [result, setResult] = useState<TrainingResult | null>(null)
  const [error, setError] = useState('')
  const deptRef = useRef<HTMLInputElement>(null)

  const canUpload = noticePdf && signinImg

  async function handleProcess() {
    if (!noticePdf || !signinImg) return
    setStep('processing')
    setError('')
    try {
      const res = await processTraining(noticePdf, signinImg, department)
      setResult(res)
      setStep('done')
      const reply = `✅ 培训统计完成！主题：${res.topic}，参与人数：${res.count} 人，类别：${res.category}`
      onComplete(reply)
    } catch (e: any) {
      setError(e.message || '处理失败')
      setStep('upload')
    }
  }

  if (step === 'processing') {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="flex items-center gap-3 text-slate-300">
          <div className="animate-spin w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full" />
          <span>正在识别处理，请稍候…</span>
        </div>
      </div>
    )
  }

  if (step === 'done' && result) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="text-green-400 font-medium mb-4">✅ 处理完成</div>
        <table className="w-full text-sm">
          <tbody>
            {[
              ['培训主题', result.topic],
              ['培训地点', result.location],
              ['培训日期', result.date],
              ['主办部门', result.department],
              ['参与人数', `${result.count} 人`],
              ['培训类别', result.category],
            ].map(([k, v]) => (
              <tr key={k} className="border-b border-slate-700/50">
                <td className="py-2 pr-4 text-slate-400 w-24">{k}</td>
                <td className="py-2 text-slate-200 font-medium">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          onClick={downloadTrainingExcel}
          className="mt-4 flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg transition-colors"
        >
          📥 下载统计表 Excel
        </button>
      </div>
    )
  }

  if (step === 'dept') {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
        <div className="text-sm text-slate-300 mb-4">
          文件已收到：<span className="text-indigo-400">{noticePdf?.name}</span>、<span className="text-indigo-400">{signinImg?.name}</span>
          <br />请填写主办部门（可留空跳过）：
        </div>
        <div className="flex gap-2">
          <input
            ref={deptRef}
            type="text"
            placeholder="主办部门（可选）"
            value={department}
            onChange={e => setDepartment(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleProcess()}
            className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500"
            autoFocus
          />
          <button
            onClick={handleProcess}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors"
          >
            开始处理
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

  // step === 'upload'
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 my-3">
      <div className="text-sm font-medium text-slate-300 mb-4">请上传以下两个文件：</div>
      {error && <div className="text-red-400 text-sm mb-3">❌ {error}</div>}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <FileDropZone
          label="📄 培训通知（PDF）"
          accept=".pdf"
          file={noticePdf}
          onFile={setNoticePdf}
        />
        <FileDropZone
          label="✍️ 签到表（图片）"
          accept=".jpg,.jpeg,.png"
          file={signinImg}
          onFile={setSigninImg}
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setStep('dept')}
          disabled={!canUpload}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          下一步
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

function FileDropZone({
  label, accept, file, onFile,
}: { label: string; accept: string; file: File | null; onFile: (f: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-xl p-4 cursor-pointer transition-all text-center
        ${drag ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-600 hover:border-slate-500'}
        ${file ? 'border-green-500/50 bg-green-500/5' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}
      />
      <div className="text-sm text-slate-400 mb-1">{label}</div>
      {file ? (
        <div className="text-xs text-green-400">✓ {file.name}</div>
      ) : (
        <div className="text-xs text-slate-500">点击或拖拽上传</div>
      )}
    </div>
  )
}
