import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="section narrow">
      <h1 className="page-title">Page not found</h1>
      <p>
        That page wandered off campus. <Link to="/">Head home</Link> or <Link to="/products">browse products</Link>.
      </p>
    </section>
  )
}
