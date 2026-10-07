import { useEffect, useRef } from 'react'
import { useChatResults } from '../context/ChatResultsContext'
import ProductCard from './ProductCard'

/** The chat agent's latest search results, rendered as regular product cards. */
export default function ChatResultsSection() {
  const { results, clearResults } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  // Bring new results into view when they arrive.
  useEffect(() => {
    if (results) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results])

  if (!results) return null

  return (
    <section ref={ref} className="chat-results" aria-live="polite" aria-label="Results from your chat">
      <div className="chat-results-head">
        <div>
          <p className="eyebrow dark">From your chat</p>
          <h2>{results.title}</h2>
          <p className="muted small">
            {results.products.length} {results.products.length === 1 ? 'item' : 'items'} for “{results.question}”
          </p>
        </div>
        <button className="chip" onClick={clearResults}>
          × Clear results
        </button>
      </div>
      <div className="grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
