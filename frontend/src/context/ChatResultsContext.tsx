import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductCardData } from '../api/client'

/** Products the chat agent found for a browse/search question, shown on the Products page. */
export interface ChatResults {
  title: string
  question: string
  products: ProductCardData[]
}

interface ChatResultsState {
  results: ChatResults | null
  showResults: (results: ChatResults) => void
  clearResults: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)

  return (
    <ChatResultsContext.Provider
      value={{ results, showResults: setResults, clearResults: () => setResults(null) }}
    >
      {children}
    </ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
