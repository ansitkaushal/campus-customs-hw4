export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
  sizes_in_stock: string[]
  low_stock_sizes: string[]
}

export interface StockLevel {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  stock: StockLevel[]
}

export interface ProductCardData {
  product_id: string
  name: string
  category: string
  garment_type: string
  description: string
  price: number
  image_url: string
  sizes_in_stock: string[]
  low_stock_sizes: string[]
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  product_ids?: string[]
}

/** Where the shopper is when they send a message, so "this one" can be resolved. */
export interface PageContext {
  path: string
  product_id: string | null
}

export interface ChatMessage extends ChatTurn {
  products: ProductCardData[]
}

/** Response of POST /api/chat. When results_title is set, the products also go on the page. */
export interface ChatReply {
  reply: string
  products: ProductCardData[]
  results_title: string | null
}

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface SignupData {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

/** POST JSON and surface FastAPI's `detail` message on errors. */
async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = data?.detail
    // Pydantic validation errors arrive as a list.
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(' ') : detail
    throw new Error(message || `Request failed (${res.status})`)
  }
  return res.status === 204 ? (undefined as T) : (res.json() as Promise<T>)
}

export const signup = (data: SignupData) => postJson<User>('/api/auth/signup', data)
export const login = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })
export const logout = () => postJson<void>('/api/auth/logout')

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me', { credentials: 'same-origin' })
  return res.ok ? (res.json() as Promise<User>) : null
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

/**
 * Send one message to the shopping agent with the current page.
 * `history` is only used for guests; logged-in history is loaded from the database.
 */
export const sendChatMessage = (message: string, history: ChatTurn[], page: PageContext) =>
  postJson<ChatReply>('/api/chat', { message, history, page })

/** Events from POST /api/chat/stream (one JSON object per line). */
export type ChatStreamEvent =
  | { type: 'status'; text: string }
  | { type: 'reset' }
  | { type: 'delta'; reply: string }
  | ({ type: 'done' } & ChatReply)
  | { type: 'error'; message: string }

/**
 * Streaming version of sendChatMessage: calls onEvent as the reply is written
 * and resolves with the final reply + product cards.
 */
export async function streamChatMessage(
  message: string,
  history: ChatTurn[],
  page: PageContext,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<ChatReply> {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ message, history, page }),
  })
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => null)
    throw new Error(data?.detail || `Request failed (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? '' // keep a partial last line for the next chunk
    for (const line of lines) {
      if (!line.trim()) continue
      const event = JSON.parse(line) as ChatStreamEvent
      if (event.type === 'error') throw new Error(event.message)
      onEvent(event)
      if (event.type === 'done') {
        const { reply, products, results_title } = event
        return { reply, products, results_title }
      }
    }
    if (done) throw new Error('The connection closed before the reply finished. Please try again.')
  }
}

/** Saved chat for the logged-in shopper; guests get []. */
export const fetchChatHistory = () => getJson<ChatMessage[]>('/api/chat/history')

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

/** Collapse the catalogue's 22 raw garment types into shopper-friendly groups. */
export function categoryOf(garmentType: string): string {
  const t = garmentType.toLowerCase()
  if (t.includes('quarter-zip')) return 'Quarter-Zips'
  if (t.includes('hood')) return 'Hoodies'
  if (t.includes('jacket') || t.includes('full-zip')) return 'Jackets & Fleece'
  if (t.includes('crewneck') || t.includes('mockneck')) return 'Crewnecks'
  if (t.includes('long-sleeve')) return 'Long Sleeves'
  return 'T-Shirts'
}
