import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { categoryOf, fetchProduct, formatPrice, type ProductDetail } from '../api/client'
import { useChatUI } from '../context/ChatUIContext'
import { useBag } from '../context/BagContext'
import { launchConfetti } from '../lib/motion'

function stockLabel(quantity: number): string {
  if (quantity === 0) return 'Sold out'
  if (quantity <= 3) return `Only ${quantity} left`
  return 'In stock'
}

export default function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState('')
  const { openWithDraft } = useChatUI()
  const { add } = useBag()
  const [size, setSize] = useState('')
  const [added, setAdded] = useState('')
  const addButton = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize('')
    setAdded('')
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setError("We couldn't find that product."))
  }, [productId])

  if (error)
    return (
      <section className="section">
        <p className="error">{error}</p>
        <Link to="/products">← Back to all products</Link>
      </section>
    )
  if (!product) return <section className="section muted">Loading…</section>

  const totalStock = product.stock.reduce((sum, s) => sum + s.quantity, 0)

  function addToBag() {
    if (!product || !size) return
    add({ product_id: product.product_id, name: product.name, size, price: product.price, image_url: product.image_url })
    setAdded(`Added ${product.name} (${size}) to your bag. Go Bulldogs!`)
    launchConfetti(addButton.current)
  }

  return (
    <section className="section">
      <Link to="/products" className="back-link">
        ← Back to all products
      </Link>
      <div className="product-detail">
        <div className="detail-img">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow dark">{categoryOf(product.garment_type)}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          <h3>Colors</h3>
          <div className="tag-row">
            {product.colors.map((c) => (
              <span key={c} className="tag">
                {c}
              </span>
            ))}
          </div>

          <h3>Sizes & availability</h3>
          {product.stock.length === 0 ? (
            <p className="muted">Stock information unavailable.</p>
          ) : (
            <table className="stock-table">
              <tbody>
                {product.stock.map((s) => (
                  <tr key={s.size} className={s.quantity === 0 ? 'soldout' : ''}>
                    <th>{s.size}</th>
                    <td>{stockLabel(s.quantity)}</td>
                    <td className="qty">{s.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="muted small">{totalStock} units available across all sizes.</p>

          <div className="buy-box">
            <fieldset className="size-picker">
              <legend>Pick your size</legend>
              {product.stock.map((s) => (
                <label key={s.size} className={s.quantity === 0 ? 'disabled' : ''}>
                  <input
                    type="radio"
                    name="size"
                    value={s.size}
                    checked={size === s.size}
                    disabled={s.quantity === 0}
                    onChange={() => {
                      setSize(s.size)
                      setAdded('')
                    }}
                  />
                  <span>{s.size}</span>
                </label>
              ))}
            </fieldset>
            <button ref={addButton} className="btn btn-gold" onClick={addToBag} disabled={!size}>
              {size ? `Add to bag · ${formatPrice(product.price)}` : 'Choose a size'}
            </button>
            <p className="added-note" role="status">
              {added}
            </p>
          </div>

          <div className="ask-box">
            <div>
              <strong>Questions about this item?</strong>
              <p className="muted small">Our assistant knows live stock, colors, and similar styles.</p>
            </div>
            <div className="ask-actions">
              <button className="btn btn-primary" onClick={() => openWithDraft('Do you have this in size ')}>
                💬 Ask about this item
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => openWithDraft('Can you show me items similar to this one?')}
              >
                Find similar
              </button>
            </div>
          </div>

          <p className="detail-type">Style: {product.garment_type}</p>
        </div>
      </div>
    </section>
  )
}
