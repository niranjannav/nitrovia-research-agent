import { useState, useRef, useEffect, useCallback } from 'react'
import { chatService, ConversationMessage, ChatSource } from '../../services/chatService'

interface SelectedFile {
  id: string
  name: string
  type: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  isLoading?: boolean
}

interface DocumentChatProps {
  selectedFiles: SelectedFile[]
  onGenerateReport: () => void
  showReportConfig: boolean
}

export default function DocumentChat({ selectedFiles, onGenerateReport, showReportConfig }: DocumentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [indexingStatus, setIndexingStatus] = useState<'idle' | 'indexing' | 'ready' | 'error'>('idle')
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const fileIds = selectedFiles.map((f) => f.id)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Index files when component mounts
  useEffect(() => {
    if (fileIds.length === 0) return
    let cancelled = false

    const indexFiles = async () => {
      setIndexingStatus('indexing')
      try {
        await chatService.indexFiles(fileIds)
        if (!cancelled) {
          setIndexingStatus('ready')
          setMessages([
            {
              id: 'welcome',
              role: 'assistant',
              content: `I've analyzed ${selectedFiles.length} document${selectedFiles.length > 1 ? 's' : ''}. Ask me anything about the content!`,
            },
          ])
        }
      } catch {
        if (!cancelled) setIndexingStatus('error')
      }
    }

    indexFiles()
    return () => { cancelled = true }
  }, [fileIds.join(',')]) // eslint-disable-line react-hooks/exhaustive-deps

  const buildHistory = useCallback((): ConversationMessage[] => {
    return messages
      .filter((m) => !m.isLoading && m.id !== 'welcome')
      .map((m) => ({ role: m.role, content: m.content }))
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isSending || indexingStatus !== 'ready') return

    const userMsgId = `user-${Date.now()}`
    const loadingMsgId = `loading-${Date.now()}`

    setInput('')
    setIsSending(true)

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', content: text },
      { id: loadingMsgId, role: 'assistant', content: '', isLoading: true },
    ])

    try {
      const history = buildHistory()
      const response = await chatService.askQuestion(fileIds, text, history)

      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsgId
            ? { id: loadingMsgId, role: 'assistant', content: response.answer, sources: response.sources }
            : m
        )
      )
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsgId
            ? { id: loadingMsgId, role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }
            : m
        )
      )
    } finally {
      setIsSending(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev)
      if (next.has(msgId)) next.delete(msgId)
      else next.add(msgId)
      return next
    })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat header with generate report toggle */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-sm font-medium text-gray-700">Document Chat</span>
          {indexingStatus === 'indexing' && (
            <span className="text-xs text-amber-600 flex items-center gap-1">
              <span className="animate-spin inline-block w-3 h-3 border border-amber-500 border-t-transparent rounded-full" />
              Analyzing documents…
            </span>
          )}
          {indexingStatus === 'error' && (
            <span className="text-xs text-red-600">Failed to index documents</span>
          )}
        </div>
        <button
          onClick={onGenerateReport}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
            showReportConfig
              ? 'bg-primary-600 text-white border-primary-600'
              : 'bg-white text-primary-600 border-primary-300 hover:bg-primary-50'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {showReportConfig ? 'Hide Report Config' : 'Generate Research Report'}
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {indexingStatus === 'indexing' && messages.length === 0 && (
          <div className="flex items-center justify-center h-32 text-gray-500">
            <div className="text-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto" />
              <p className="text-sm">Reading and indexing your documents…</p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>
              {/* Avatar */}
              <div className={`flex items-end gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {msg.role === 'user' ? 'U' : 'AI'}
                </div>

                <div className={`rounded-2xl px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-sm'
                    : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                }`}>
                  {msg.isLoading ? (
                    <div className="flex items-center gap-1.5 py-0.5">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  )}
                </div>
              </div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className={`mt-1.5 ${msg.role === 'user' ? 'text-right' : 'text-left'} pl-9`}>
                  <button
                    onClick={() => toggleSources(msg.id)}
                    className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                    <svg
                      className={`w-3 h-3 transition-transform ${expandedSources.has(msg.id) ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {expandedSources.has(msg.id) && (
                    <div className="mt-2 space-y-1.5">
                      {msg.sources.map((src, i) => (
                        <div key={i} className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs text-left shadow-sm">
                          <div className="flex items-center gap-1.5 font-medium text-gray-700 mb-1">
                            <FileTypeIcon fileType={src.file_name.split('.').pop() || ''} />
                            <span>{src.file_name}</span>
                            {src.page && <span className="text-gray-400">· page {src.page}</span>}
                            {src.sheet_name && <span className="text-gray-400">· {src.sheet_name}</span>}
                            <span className="ml-auto text-gray-400">{Math.round(src.similarity * 100)}% match</span>
                          </div>
                          <p className="text-gray-500 line-clamp-2 leading-relaxed">{src.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              indexingStatus === 'indexing'
                ? 'Analyzing documents…'
                : indexingStatus === 'error'
                ? 'Indexing failed — try refreshing'
                : 'Ask a question about your documents… (Enter to send)'
            }
            disabled={indexingStatus !== 'ready' || isSending}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 max-h-32 overflow-y-auto"
            style={{ minHeight: '42px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = Math.min(target.scrollHeight, 128) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending || indexingStatus !== 'ready'}
            className="w-10 h-10 flex-shrink-0 bg-primary-600 text-white rounded-xl flex items-center justify-center hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5 ml-1">
          Shift+Enter for new line · Answers are grounded in your documents
        </p>
      </div>
    </div>
  )
}

function FileTypeIcon({ fileType }: { fileType: string }) {
  const colors: Record<string, string> = {
    pdf: 'text-red-500',
    docx: 'text-blue-500',
    doc: 'text-blue-500',
    xlsx: 'text-green-600',
    xls: 'text-green-600',
    pptx: 'text-orange-500',
    ppt: 'text-orange-500',
  }
  return (
    <span className={`font-mono uppercase text-[10px] font-bold ${colors[fileType] || 'text-gray-500'}`}>
      {fileType}
    </span>
  )
}
