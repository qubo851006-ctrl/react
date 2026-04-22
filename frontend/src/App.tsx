import { useState, useEffect, useRef } from 'react'
import type { Message, Stage } from './types'
import { getHistory, clearHistory, sendChat, clearLedger, downloadTrainingExcel, downloadLedgerExcel } from './api'
import Sidebar from './components/Sidebar'
import ChatMessage from './components/ChatMessage'
import TrainingFlow from './components/TrainingFlow'
import LedgerFlow from './components/LedgerFlow'
import AuthFlow from './components/AuthFlow'

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [stage, setStage] = useState<Stage>('idle')
  const [input, setInput] = useState('')
  const [useKb, setUseKb] = useState(false)
  const [kbConvId, setKbConvId] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getHistory().then(({ messages: msgs }) => {
      setMessages(msgs)
    })
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, stage])

  useEffect(() => {
    if (stage === 'download_training_excel') {
      downloadTrainingExcel()
      setStage('idle')
    } else if (stage === 'download_ledger_excel') {
      downloadLedgerExcel()
      setStage('idle')
    }
  }, [stage])

  function addMessage(role: 'user' | 'assistant', content: string) {
    setMessages(prev => [...prev, { role, content }])
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || sending || stage !== 'idle') return
    setInput('')
    addMessage('user', text)
    setSending(true)
    setStage('thinking')
    try {
      const res = await sendChat(text, useKb, kbConvId)
      addMessage('assistant', res.reply)
      if (res.kb_conversation_id) setKbConvId(res.kb_conversation_id)
      setStage(res.next_stage as Stage)
    } catch {
      addMessage('assistant', '❌ 请求失败，请检查后端服务是否启动。')
      setStage('idle')
    } finally {
      setSending(false)
    }
  }

  function triggerSkill(skill: 'training' | 'ledger' | 'auth') {
    const map = {
      training: {
        msg: '📊 培训统计及归档',
        reply: '好的！请上传以下两个文件：\n\n- 📄 **培训通知**（PDF 格式）\n- ✍️ **签到表**（图片格式：JPG / PNG）',
        stage: 'waiting_files' as Stage,
      },
      ledger: {
        msg: '⚖️ 案件台账生成',
        reply: '好的！请上传案件的法律文书文件（支持 **PDF / DOCX / DOC**，可多选）。\n\n系统会自动识别文书类型，并判断是否为台账中的已有案件。',
        stage: 'waiting_ledger_files' as Stage,
      },
      auth: {
        msg: '📝 授权请示起草',
        reply: '好的！请上传**呈批件 PDF**，系统将自动提取关键信息并生成授权请示 Word 文档。\n\n- 支持文字版 PDF（直接提取）\n- 支持扫描版 PDF（自动 OCR 识别）',
        stage: 'waiting_auth_file' as Stage,
      },
    }
    const { msg, reply, stage: nextStage } = map[skill]
    addMessage('user', msg)
    addMessage('assistant', reply)
    setStage(nextStage)
  }

  function handleCancel() {
    addMessage('assistant', '已取消，如需重新操作请告诉我。')
    setStage('idle')
  }

  async function handleClearLedger() {
    const res = await clearLedger()
    addMessage('assistant', res.message)
  }

  async function handleClearChat() {
    await clearHistory()
    setMessages([])
    setKbConvId('')
  }

  function handleToggleKb(v: boolean) {
    setUseKb(v)
    if (!v) setKbConvId('')
  }

  const isIdle = stage === 'idle'

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-950">
      <Sidebar
        stage={stage}
        useKb={useKb}
        onSkill={triggerSkill}
        onClearLedger={handleClearLedger}
        onClearChat={handleClearChat}
        onToggleKb={handleToggleKb}
      />

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-slate-700/50 bg-slate-900/50 backdrop-blur">
          <h1 className="text-base font-semibold text-white m-0">法务合规部智能体V1</h1>
          <p className="text-xs text-slate-500 mt-0.5">AI 驱动的企业培训与法务管理系统</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}

          {/* Stage-specific inline panels */}
          {stage === 'waiting_files' && (
            <TrainingFlow
              onComplete={reply => { addMessage('assistant', reply); setStage('idle') }}
              onCancel={handleCancel}
            />
          )}
          {stage === 'waiting_ledger_files' && (
            <LedgerFlow
              onComplete={reply => { addMessage('assistant', reply); setStage('idle') }}
              onCancel={handleCancel}
            />
          )}
          {stage === 'waiting_auth_file' && (
            <AuthFlow
              onComplete={reply => { addMessage('assistant', reply); setStage('idle') }}
              onCancel={handleCancel}
            />
          )}

          {stage === 'thinking' && (
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-4">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              思考中…
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-slate-700/50 bg-slate-900/30">
          <div className="flex gap-3 items-center">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder={isIdle ? '有什么可以帮您？' : '请完成当前操作…'}
              disabled={!isIdle || sending}
              className="
                flex-1 bg-slate-800 border border-slate-700 rounded-xl
                px-4 py-3 text-sm text-white placeholder-slate-500
                outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30
                disabled:opacity-50 disabled:cursor-not-allowed transition-colors
              "
            />
            <button
              onClick={handleSend}
              disabled={!isIdle || !input.trim() || sending}
              className="
                px-4 py-3 bg-indigo-600 hover:bg-indigo-500
                disabled:opacity-40 disabled:cursor-not-allowed
                text-white text-sm rounded-xl transition-colors
                flex items-center gap-2
              "
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          {useKb && (
            <div className="text-xs text-indigo-400 mt-2 flex items-center gap-1">
              <span>📚</span> 知识库模式已启用
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
