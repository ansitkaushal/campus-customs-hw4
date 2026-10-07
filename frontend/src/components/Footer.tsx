import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <h4>Campus Customs</h4>
          <p>Yale gear, printed and stocked in New Haven.</p>
        </div>
        <div>
          <h4>Visit</h4>
          <p>
            57 Broadway
            <br />
            New Haven, CT 06511
          </p>
        </div>
        <div>
          <h4>Shop</h4>
          <p>
            <Link to="/products">All products</Link>
            <br />
            <Link to="/about">About us</Link>
          </p>
        </div>
      </div>
      <p className="footer-note">© {new Date().getFullYear()} Campus Customs · Class project demo</p>
    </footer>
  )
}
