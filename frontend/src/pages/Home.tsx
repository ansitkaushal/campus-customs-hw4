import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api/client'
import ProductCard from '../components/ProductCard'

const collections = [
  { title: 'Residential Colleges', text: 'Rep your college, from Davenport to Grace Hopper.', key: 'colleges' },
  { title: 'Bulldog Athletics', text: 'Gear for every team, from football to fencing.', key: 'athletics' },
  { title: 'Graduate Schools', text: 'Law, Art, Music, Public Health, and more.', key: 'schools' },
  { title: 'Yale Family', text: 'For the proud moms, dads, and grandpas.', key: 'family' },
]

// A few signature pieces to feature on the homepage.
const FEATURED = ['basic-hoodie-big-yale', 'champion-reverse-weave-hoodie-1', 'yale-grandpa-crewneck', 'boola-boola-t-shirt']

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const [stats, setStats] = useState({ styles: 0, inStock: 0 })

  useEffect(() => {
    fetchProducts()
      .then((all) => {
        const picks = all.filter((p) => FEATURED.includes(p.product_id))
        setFeatured(picks.length ? picks : all.slice(0, 4))
        setStats({ styles: all.length, inStock: all.filter((p) => p.sizes_in_stock.length === 6).length })
      })
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow">New Haven, Connecticut · Game Day Ready</p>
          <h1>
            Wear your <span className="hero-accent">Yale pride.</span>
          </h1>
          <p>
            Campus Customs is a New Haven shop for officially licensed Yale apparel. We carry hoodies and crewnecks
            for game day, the reunion, and the walk across Old Campus.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">
              Shop the collection →
            </Link>
            <Link to="/about" className="hero-link">
              Our story
            </Link>
          </div>
        </div>
        <div className="scoreboard" aria-label="Store scoreboard">
          <div className="scoreboard-title">Campus Customs</div>
          <div className="scoreboard-grid">
            <div>
              <span className="score">{stats.styles || '—'}</span>
              <span className="score-label">Styles</span>
            </div>
            <div>
              <span className="score">{stats.inStock || '—'}</span>
              <span className="score-label">In every size</span>
            </div>
            <div>
              <span className="score">6</span>
              <span className="score-label">Sizes XS–XXL</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Shop by collection</h2>
        <div className="collections">
          {collections.map((c) => (
            <Link key={c.title} to={`/products?collection=${c.key}`} className="collection">
              <span className="patch-letter" aria-hidden="true">
                {c.title[0]}
              </span>
              <h3>{c.title}</h3>
              <p>{c.text}</p>
              <span>Browse →</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Big pride, big Yale</h2>
          <Link to="/products">View all →</Link>
        </div>
        <div className="grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="banner">
        <h2>Not sure what fits?</h2>
        <p>Ask Benny, our counter clerk, in the bottom-right corner about sizes, colors, and what's in stock.</p>
      </section>
    </>
  )
}
