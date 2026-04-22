import type { Message } from '../types'
import ReactMarkdown from 'react-markdown'

interface Props {
  message: Message
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-sm flex-shrink-0 mr-2.5 mt-0.5">
          🤖
        </div>
      )}
      <div
        className={`
          max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-slate-800 text-slate-200 rounded-bl-sm border border-slate-700/50'}
        `}
      >
        {isUser ? (
          <span>{message.content}</span>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none
            prose-p:my-1 prose-ul:my-1 prose-li:my-0.5
            prose-table:text-xs prose-th:py-1.5 prose-td:py-1.5
            prose-code:bg-slate-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
          ">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-sm flex-shrink-0 ml-2.5 mt-0.5">
          👤
        </div>
      )}
    </div>
  )
}
