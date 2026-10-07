import { Link } from 'react-router-dom'
import { formatPrice, type ProductCardData } from '../api/client'
import { useReveal } from '../hooks/useReveal'
import { merchBadge } from '../lib/badges'

// Catalogue items and chat results share this card, so it only needs the common fields.
type CardProduct = Pick<
  ProductCardData,
  'product_id' | 'name' | 'description' | 'price' | 'image_url' | 'sizes_in_stock' | 'low_stock_sizes'
>

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

/**
 * One badge for the image corner. Kept rare on purpose (about 1 in 5 products today) so it
 * means something; per-size low stock is shown by the amber size chips instead.
 */
function stockBadge(p: CardProduct): { text: string; tone: 'out' | 'low' } | null {
  const inStock = p.sizes_in_stock ?? []
  if (inStock.length === 0) return { text: 'Sold out', tone: 'out' }
  if (inStock.length <= 3) return { text: inStock.length === 1 ? 'Only 1 size left' : `Only ${inStock.length} sizes left`, tone: 'low' }
  return null
}

export default function ProductCard({ product }: { product: CardProduct }) {
  const badge = stockBadge(product)
  const promo = merchBadge(product.product_id)
  const ref = useReveal<HTMLAnchorElement>()
  const inStock = new Set(product.sizes_in_stock ?? [])
  const low = new Set(product.low_stock_sizes ?? [])

  return (
    <Link ref={ref} to={`/products/${product.product_id}`} className="card reveal">
      {/* Hang-tag details: punched hole + string (decorative) */}
      <span className="tag-hole" aria-hidden="true" />
      {promo && <span className={`promo-badge ${promo === 'New Drop' ? 'new' : 'fav'}`}>{promo}</span>}
      <div className="card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badge && <span className={`stock-badge ${badge.tone}`}>{badge.text}</span>}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="card-desc">{product.description}</p>
        <div className="card-foot">
          <p className="price">{formatPrice(product.price)}</p>
          <ul className="size-row" aria-label="Sizes in stock">
            {SIZES.map((s) => (
              <li
                key={s}
                className={inStock.has(s) ? (low.has(s) ? 'low' : '') : 'out'}
                title={inStock.has(s) ? (low.has(s) ? `${s}: only a few left` : `${s}: in stock`) : `${s}: sold out`}
              >
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Link>
  )
}
