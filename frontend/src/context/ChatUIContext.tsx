import { createContext, useContext, useState, type ReactNode } from 'react'

/** Lets any page open the chat panel, optionally with a question typed in for the shopper. */
interface ChatUIState {
  open: boolean
  setOpen: (open: boolean) => void
  draft: string | null
  /** Open the chat with `text` in the input box (not sent), ready for the shopper to edit. */
  openWithDraft: (text: string) => void
  clearDraft: () => void
}

const ChatUIContext = createContext<ChatUIState | null>(null)

export function ChatUIProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<string | null>(null)

  return (
    <ChatUIContext.Provider
      value={{
        open,
        setOpen,
        draft,
        openWithDraft: (text) => {
          setDraft(text)
          setOpen(true)
        },
        clearDraft: () => setDraft(null),
      }}
    >
      {children}
    </ChatUIContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatUI(): ChatUIState {
  const ctx = useContext(ChatUIContext)
  if (!ctx) throw new Error('useChatUI must be used inside <ChatUIProvider>')
  return ctx
}
