import { useState, useRef, useEffect, useCallback, Component } from 'react'
import type { ReactNode, ErrorInfo } from 'react'
import {
  TamboProvider,
  useTambo,
  useTamboThreadInput,
  ComponentRenderer,
} from '@tambo-ai/react'
import type { TamboThreadMessage, Content } from '@tambo-ai/react'
import { dataAnalysisComponents } from './tamboConfig'
import DataPreview from './DataPreview'
import type { ParsedExcelData } from '../../utils/excelParser'
import { summarizeDataForContext } from '../../utils/excelParser'

interface DataAnalysisModeProps {
  data: ParsedExcelData
  fileName: string
  onBack: () => void
}

export default function DataAnalysisMode({ data, fileName, onBack }: DataAnalysisModeProps) {
  const apiKey = import.meta.env.VITE_TAMBO_API_KEY

  if (!apiKey) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Header fileName={fileName} onBack={onBack} />
        <DataPreview data={data} fileName={fileName} />
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          <p className="font-medium">Tambo API Key Required</p>
          <p className="mt-1">
            Set <code className="bg-amber-100 px-1 py-0.5 rounded text-xs">VITE_TAMBO_API_KEY</code> in
            your <code className="bg-amber-100 px-1 py-0.5 rounded text-xs">.env</code> file to enable
            AI-powered data analysis chat. Get your API key at{' '}
            <a
              href="https://tambo.co"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium"
            >
              tambo.co
            </a>
          </p>
        </div>
      </div>
    )
  }

  const dataSummary = summarizeDataForContext(data)

  return (
    <TamboProvider
      apiKey={apiKey}
      userKey="data-analysis-user"
      components={dataAnalysisComponents}
      contextHelpers={{
        datasetContext: () => dataSummary,
        fullDataJSON: () => JSON.stringify(data.rows.slice(0, 100)),
      }}
      initialMessages={[
        {
          role: 'assistant',
          content: [
            {
              type: 'text',
              text: `I've loaded your Excel file **"${fileName}"** with ${data.rows.length} rows and ${data.headers.length} columns (${data.headers.join(', ')}). Ask me anything about your data! I can create charts, filter tables, and compute summary statistics.`,
            },
          ],
        },
      ]}
    >
      <div className="max-w-4xl mx-auto space-y-4">
        <Header fileName={fileName} onBack={onBack} />
        <DataPreview data={data} fileName={fileName} />
        <ChatErrorBoundary>
          <ChatInterface />
        </ChatErrorBoundary>
      </div>
    </TamboProvider>
  )
}

function Header({ fileName, onBack }: { fileName: string; onBack: () => void }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Analysis</h1>
        <p className="text-gray-600 mt-1 text-sm">
          Chat with your data from <span className="font-medium">{fileName}</span>
        </p>
      </div>
      <button
        onClick={onBack}
        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        ← Back to Upload
      </button>
    </div>
  )
}

class ChatErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[DataAnalysis] Chat error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800">
          <p className="font-medium">Something went wrong rendering the response</p>
          <p className="mt-1 text-xs text-red-600">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-2 px-3 py-1 text-xs bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function ChatInterface() {
  const { messages, isStreaming, currentThreadId } = useTambo()
  const { value, setValue, submit, isPending } = useTamboThreadInput()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [localError, setLocalError] = useState<string | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!value.trim() || isPending) return
    setLocalError(null)
    try {
      await submit()
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to send message')
    }
  }

  const suggestions = [
    'Show me a summary of this data',
    'Create a bar chart of the top values',
    'What are the key trends?',
    'Filter rows where values are above average',
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Chat messages */}
      <div className="h-[500px] overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            threadId={currentThreadId}
          />
        ))}

        {isStreaming && (
          <div className="flex items-center gap-2 text-gray-400 text-sm pl-2">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span>Analyzing...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions (show when no user messages yet) */}
      {messages.filter((m) => m.role === 'user').length === 0 && (
        <div className="px-4 pb-2">
          <p className="text-xs text-gray-400 mb-2">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setValue(suggestion)}
                className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full border border-gray-200 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {localError && (
        <div className="mx-4 mb-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-xs">
          {localError}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-100 p-3 flex gap-2"
      >
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask about your data..."
          disabled={isPending}
          className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-gray-50"
        />
        <button
          type="submit"
          disabled={isPending || !value.trim()}
          className="px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {isPending ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Sending
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              Send
            </>
          )}
        </button>
      </form>
    </div>
  )
}

function MessageBubble({
  message,
  threadId,
}: {
  message: TamboThreadMessage
  threadId: string
}) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] space-y-2 ${
          isUser
            ? 'bg-primary-600 text-white rounded-2xl rounded-br-md px-4 py-2.5'
            : 'space-y-3'
        }`}
      >
        {message.content.map((block: Content, i: number) => {
          if (block.type === 'text') {
            return (
              <div
                key={i}
                className={
                  isUser
                    ? 'text-sm'
                    : 'text-sm text-gray-700 bg-gray-50 rounded-2xl rounded-bl-md px-4 py-2.5'
                }
              >
                {block.text}
              </div>
            )
          }
          if (block.type === 'component') {
            return (
              <ComponentRenderer
                key={block.id || i}
                content={block}
                threadId={threadId}
                messageId={message.id}
                fallback={
                  <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-400">
                    Loading component...
                  </div>
                }
              />
            )
          }
          return null
        })}
      </div>
    </div>
  )
}
