import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductPage from './pages/ProductPage'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'
import NotFound from './pages/NotFound'
import Account from './pages/Account'
import { AuthProvider } from './context/AuthContext'
import { ChatResultsProvider } from './context/ChatResultsContext'
import { ChatUIProvider } from './context/ChatUIContext'
import { BagProvider } from './context/BagContext'

export default function App() {
  return (
    <AuthProvider>
      <ChatResultsProvider>
        <ChatUIProvider>
          <BagProvider>
            <div className="app">
              <NavBar />
              <main className="main">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/products" element={<Products />} />
                  <Route path="/products/:productId" element={<ProductPage />} />
                  <Route path="/about" element={<About />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/signup" element={<Signup />} />
                  <Route path="/account" element={<Account />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </main>
              <Footer />
              <ChatWidget />
            </div>
          </BagProvider>
        </ChatUIProvider>
      </ChatResultsProvider>
    </AuthProvider>
  )
}
