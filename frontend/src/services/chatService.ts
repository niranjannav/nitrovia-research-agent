import api from './api'

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatSource {
  file_name: string
  page: number | null
  sheet_name: string | null
  content: string
  similarity: number
}

export interface ChatIndexResponse {
  already_indexed: string[]
  newly_indexed: string[]
  failed: string[]
}

export interface ChatAskResponse {
  answer: string
  sources: ChatSource[]
}

export const chatService = {
  async indexFiles(fileIds: string[]): Promise<ChatIndexResponse> {
    const response = await api.post<ChatIndexResponse>('/chat/index', {
      file_ids: fileIds,
    })
    return response.data
  },

  async askQuestion(
    fileIds: string[],
    message: string,
    conversationHistory: ConversationMessage[]
  ): Promise<ChatAskResponse> {
    const response = await api.post<ChatAskResponse>('/chat/ask', {
      file_ids: fileIds,
      message,
      conversation_history: conversationHistory,
    })
    return response.data
  },
}
