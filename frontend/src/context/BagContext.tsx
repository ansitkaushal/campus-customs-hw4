import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

/**
 * A minimal shopping bag kept in localStorage. There's no checkout yet; it exists
 * so "Add to bag" gives real feedback (count in the nav + a little celebration).
 */
export interface BagItem {
  product_id: string
  name: string
  size: string
  price: number
  image_url: string
  quantity: number
}

interface BagState {
  items: BagItem[]
  count: number
  add: (item: Omit<BagItem, 'quantity'>) => void
}

const STORAGE_KEY = 'cc_bag'
const BagContext = createContext<BagState | null>(null)

function loadBag(): BagItem[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

export function BagProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<BagItem[]>(loadBag)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const add: BagState['add'] = (item) =>
    setItems((current) => {
      const existing = current.find((i) => i.product_id === item.product_id && i.size === item.size)
      if (existing) return current.map((i) => (i === existing ? { ...i, quantity: i.quantity + 1 } : i))
      return [...current, { ...item, quantity: 1 }]
    })

  const count = items.reduce((sum, i) => sum + i.quantity, 0)

  return <BagContext.Provider value={{ items, count, add }}>{children}</BagContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useBag(): BagState {
  const ctx = useContext(BagContext)
  if (!ctx) throw new Error('useBag must be used inside <BagProvider>')
  return ctx
}
