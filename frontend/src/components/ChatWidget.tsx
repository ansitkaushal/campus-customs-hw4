import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { fetchChatHistory, formatPrice, streamChatMessage, type ChatMessage as SavedMessage } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useChatResults } from '../context/ChatResultsContext'
import { useChatUI } from '../context/ChatUIContext'
import ClerkAvatar, { CLERK_NAME } from './ClerkAvatar'

const HISTORY_SENT = 20 // recent turns sent with each message for context
const CHAT_CARDS = 4 // mini cards shown inside the chat; the rest go on the page

// resultsTitle marks replies whose products were also shown on the page; streaming marks the reply being written.
type ChatMessage = SavedMessage & { resultsTitle?: string | null; streaming?: boolean }

// Starter questions shown before the shopper's first message (different on a product page).
const GENERAL_SUGGESTIONS = ['What hoodies do you have?', 'Gift ideas under $60', 'Anything for hockey fans?', 'Show me Yale Mom gear']
const PRODUCT_SUGGESTIONS = ['Is this in stock in M?', 'What colors does this come in?', 'How much is this?', 'Show me similar items']

function greeting(firstName?: string): ChatMessage {
  return {
    role: 'assistant',
    content: `Hey${firstName ? ` ${firstName}` : ''}! I'm ${CLERK_NAME}, your Campus Customs counter clerk 🐾 Ask me about sizes, stock, prices, or gift ideas.`,
    products: [],
  }
}

/** Tiny Markdown subset for agent replies: **bold** and "- " bullet lines. */
function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  )
}

function renderMarkdown(text: string): ReactNode {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`}>
          {bullets.map((b, i) => (
            <li key={i}>{renderInline(b)}</li>
          ))}
        </ul>,
      )
      bullets = []
    }
  }
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*[-*•]\s+(.*)/)
    if (m) {
      bullets.push(m[1])
    } else {
      flush()
      if (line.trim()) blocks.push(<p key={`p-${blocks.length}`}>{renderInline(line)}</p>)
    }
  }
  flush()
  return blocks
}

export default function ChatWidget() {
  const { user, loading } = useAuth()
  const { showResults, clearResults } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()
  // On a single-item page (/products/:id), tell the agent which product "this" means.
  const viewingProductId = location.pathname.match(/^\/products\/([^/]+)$/)?.[1] ?? null
  const { open, setOpen, draft, clearDraft } = useChatUI()
  const [messages, setMessages] = useState<ChatMessage[]>([greeting()])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [status, setStatus] = useState('') // e.g. "Checking stock…" while a tool runs
  const [sentThisVisit, setSentThisVisit] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestions = viewingProductId ? PRODUCT_SUGGESTIONS : GENERAL_SUGGESTIONS

  // "Ask about this item" (and similar buttons) open the chat with a question ready to edit.
  useEffect(() => {
    if (draft === null) return
    setInput(draft)
    clearDraft()
    setTimeout(() => {
      const el = inputRef.current
      el?.focus()
      el?.setSelectionRange(el.value.length, el.value.length)
    }, 50)
  }, [draft, clearDraft])

  // Reset the conversation when the shopper logs in or out; restore saved chat for members.
  useEffect(() => {
    if (loading) return
    clearResults()
    const hello = greeting(user?.first_name)
    if (!user) {
      setMessages([hello])
      return
    }
    fetchChatHistory()
      .then((saved) => setMessages([hello, ...saved]))
      .catch(() => setMessages([hello]))
  }, [user, loading])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending, open, status])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  /** Update the reply that's currently being streamed (always the last message). */
  function updateStreaming(patch: Partial<ChatMessage>) {
    setMessages((m) => {
      const last = m[m.length - 1]
      if (!last?.streaming) return m
      return [...m.slice(0, -1), { ...last, ...patch }]
    })
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    // Guest context: earlier turns (minus the canned greeting) with the products each reply showed.
    const history = messages
      .slice(1)
      .slice(-HISTORY_SENT)
      .map(({ role, content, products }) => ({ role, content, product_ids: products.map((p) => p.product_id) }))
    const page = { path: location.pathname, product_id: viewingProductId }
    setInput('')
    setSentThisVisit((n) => n + 1)
    setMessages((m) => [
      ...m,
      { role: 'user', content: text, products: [] },
      { role: 'assistant', content: '', products: [], streaming: true },
    ])
    setSending(true)
    setStatus('')
    try {
      const { reply, products, results_title } = await streamChatMessage(text, history, page, (event) => {
        if (event.type === 'status') setStatus(event.text)
        else if (event.type === 'reset') updateStreaming({ content: '' })
        else if (event.type === 'delta') {
          setStatus('')
          updateStreaming({ content: event.reply })
        }
      })
      updateStreaming({ content: reply, products, resultsTitle: results_title, streaming: false })
      // Browse/search answers also go on the page as a results grid.
      if (results_title && products.length) {
        showResults({ title: results_title, question: text, products })
        if (location.pathname !== '/products') navigate('/products')
      }
    } catch (err) {
      const content = err instanceof Error ? err.message : 'Sorry, something went wrong. Please try again.'
      updateStreaming({ content, streaming: false })
    } finally {
      setSending(false)
      setStatus('')
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label={`Chat with ${CLERK_NAME}, the shopping assistant`}>
          <header className="chat-header">
            <ClerkAvatar size={40} className="chat-header-avatar" />
            <div>
              <strong>{CLERK_NAME} · Campus Customs</strong>
              <small>
                <span className="online-dot" aria-hidden="true" /> At the counter
                {user ? ` · chatting with ${user.first_name}` : ' · log in to save your chat'}
              </small>
            </div>
            <button aria-label="Close chat" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>
          <div className="chat-messages">
            {messages.map((m, i) =>
              m.streaming && !m.content ? null : (
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className="chat-row">
                  {m.role === 'assistant' && <ClerkAvatar size={28} className="chat-avatar" />}
                  <div className={`bubble ${m.role}`}>{m.role === 'assistant' ? renderMarkdown(m.content) : m.content}</div>
                </div>
                {m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.slice(0, CHAT_CARDS).map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt={p.name} loading="lazy" />
                        <span className="chat-product-name">{p.name}</span>
                        <span className="chat-product-price">{formatPrice(p.price)}</span>
                      </Link>
                    ))}
                  </div>
                )}
                {m.resultsTitle && (
                  <button
                    className="chat-view-all"
                    onClick={() => {
                      const question = messages[i - 1]?.content ?? m.resultsTitle!
                      showResults({ title: m.resultsTitle!, question, products: m.products })
                      navigate('/products')
                    }}
                  >
                    {m.products.length > CHAT_CARDS
                      ? `See all ${m.products.length} on the page →`
                      : 'Show on the page →'}
                  </button>
                )}
              </div>
              ),
            )}
            {sending && !messages[messages.length - 1]?.content && (
              <div className="chat-typing">
                <ClerkAvatar size={28} className="chat-avatar" />
                <div className="bubble assistant typing" aria-label={`${CLERK_NAME} is typing`}>
                  <span />
                  <span />
                  <span />
                </div>
                {status && <span className="chat-status">{status}</span>}
              </div>
            )}
            {!sending && sentThisVisit === 0 && (
              <div className="chat-suggestions" aria-label="Suggested questions">
                {suggestions.map((q) => (
                  <button key={q} className="chat-suggestion" onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={viewingProductId ? 'Ask about this item: sizes, colors, price…' : 'Ask about a hoodie, size, or price…'}
              aria-label="Chat message"
              maxLength={2000}
            />
            <button type="submit" disabled={sending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className={`chat-launcher ${open ? 'is-open' : ''}`}
        aria-label={open ? 'Close chat' : `Chat with ${CLERK_NAME}`}
        onClick={() => setOpen(!open)}
      >
        {open ? <span className="launcher-close">×</span> : <ClerkAvatar size={56} />}
        {!open && <span className="launcher-label">Ask {CLERK_NAME}</span>}
      </button>
    </div>
  )
}
