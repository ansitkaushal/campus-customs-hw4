import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { categoryOf, fetchProducts, type Product } from '../api/client'
import ProductCard from '../components/ProductCard'
import ChatResultsSection from '../components/ChatResultsSection'

// Homepage collections match on product name only: nearly every product is
// tagged "college sweatshirt", so a tag search for "college" is useless.
const COLLECTIONS: Record<string, { label: string; words: string[] }> = {
  colleges: {
    label: 'Residential Colleges',
    words: ['benjamin franklin', 'berkeley', 'branford', 'davenport', 'grace hopper', 'jonathan edwards',
      'morse', 'pauli murray', 'pierson', 'saybrook', 'silliman', 'timothy dwight', 'trumbull', 'ezra stiles'],
  },
  athletics: {
    label: 'Bulldog Athletics',
    words: ['sports', 'left chest', 'diving', 'football', 'hockey', 'lacrosse', 'fencing', 'squash',
      'sailing', 'soccer', 'volleyball', 'tennis', 'baseball', 'basketball', 'golf', 'track'],
  },
  schools: { label: 'Graduate Schools', words: ['school'] },
  family: {
    label: 'Yale Family',
    words: ['mom', 'dad', 'grandpa', 'grandma', 'uncle', 'aunt', 'brother', 'sister', 'cousin'],
  },
}

type SortKey = 'featured' | 'price-asc' | 'price-desc' | 'name' | 'in-stock'

const SORTS: Record<SortKey, { label: string; compare: (a: Product, b: Product) => number }> = {
  featured: { label: 'Featured', compare: () => 0 }, // keep the API order
  'price-asc': { label: 'Price: low to high', compare: (a, b) => a.price - b.price || a.name.localeCompare(b.name) },
  'price-desc': { label: 'Price: high to low', compare: (a, b) => b.price - a.price || a.name.localeCompare(b.name) },
  name: { label: 'Name: A–Z', compare: (a, b) => a.name.localeCompare(b.name) },
  'in-stock': {
    label: 'Most sizes in stock',
    compare: (a, b) => b.sizes_in_stock.length - a.sizes_in_stock.length || a.name.localeCompare(b.name),
  },
}

function inCollection(p: Product, key: string): boolean {
  const c = COLLECTIONS[key]
  if (!c) return true
  const name = p.name.toLowerCase()
  return c.words.some((w) => new RegExp(`\\b${w}\\b`).test(name))
}

function matches(p: Product, query: string): boolean {
  const q = query.toLowerCase()
  const haystack = [p.name, p.description, p.garment_type, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
  return haystack.includes(q)
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? 'All'
  const collection = params.get('collection') ?? ''
  const sort = (params.get('sort') ?? 'featured') as SortKey
  const maxParam = Number(params.get('max'))

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  const categories = useMemo(
    () => ['All', ...Array.from(new Set(products.map((p) => categoryOf(p.garment_type)))).sort()],
    [products],
  )

  // Price slider bounds come from the catalogue itself ($32–$98 today).
  const [minPrice, maxPrice] = useMemo(() => {
    if (!products.length) return [0, 100]
    const prices = products.map((p) => p.price)
    return [Math.min(...prices), Math.max(...prices)]
  }, [products])
  const priceCap = maxParam > 0 ? Math.min(maxParam, maxPrice) : maxPrice

  const visible = products
    .filter(
      (p) =>
        (category === 'All' || categoryOf(p.garment_type) === category) &&
        inCollection(p, collection) &&
        p.price <= priceCap &&
        (!query || matches(p, query)),
    )
    .sort(SORTS[sort]?.compare ?? SORTS.featured.compare)

  function update(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value && value !== 'All' && value !== 'featured') next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  return (
    <section className="section">
      <ChatResultsSection />
      <h1 className="page-title">{COLLECTIONS[collection]?.label ?? 'Shop all Yale apparel'}</h1>
      {COLLECTIONS[collection] && (
        <button className="chip" onClick={() => update('collection', '')}>
          × Clear collection
        </button>
      )}

      <div className="filters">
        <input
          type="search"
          value={query}
          onChange={(e) => update('q', e.target.value)}
          placeholder="Search hoodies, colleges, sports…"
          aria-label="Search products"
        />
        <div className="chips">
          {categories.map((c) => (
            <button key={c} className={`chip ${c === category ? 'active' : ''}`} onClick={() => update('category', c)}>
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="toolbar">
        <label className="toolbar-field">
          Sort by
          <select value={sort} onChange={(e) => update('sort', e.target.value)}>
            {(Object.keys(SORTS) as SortKey[]).map((k) => (
              <option key={k} value={k}>
                {SORTS[k].label}
              </option>
            ))}
          </select>
        </label>
        <label className="toolbar-field price-field">
          Max price: <strong>${priceCap.toFixed(0)}</strong>
          <input
            type="range"
            min={minPrice}
            max={maxPrice}
            step={1}
            value={priceCap}
            onChange={(e) => update('max', Number(e.target.value) >= maxPrice ? '' : e.target.value)}
            aria-label="Maximum price"
          />
        </label>
        {(priceCap < maxPrice || sort !== 'featured') && (
          <button
            className="chip"
            onClick={() => {
              const next = new URLSearchParams(params)
              next.delete('max')
              next.delete('sort')
              setParams(next, { replace: true })
            }}
          >
            Reset sort & price
          </button>
        )}
      </div>

      {loading && <p className="muted">Loading products…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <p className="muted">
          {visible.length} {visible.length === 1 ? 'item' : 'items'}
          {priceCap < maxPrice && ` up to $${priceCap.toFixed(0)}`}
        </p>
      )}
      {!loading && !error && visible.length === 0 && (
        <p className="empty">No items match. Try a higher max price or a different category, or ask our assistant.</p>
      )}

      <div className="grid">
        {visible.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
