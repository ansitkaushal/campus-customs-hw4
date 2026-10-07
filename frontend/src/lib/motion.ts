/** Shared motion helpers. Every animation checks prefersReducedMotion() first. */

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

const CONFETTI_COLORS = ['#0c2340', '#00356b', '#f2b705', '#ffd75e', '#ffffff']

/**
 * A short burst of paper confetti from an element (e.g. the "Add to bag" button).
 * Pure DOM + CSS, cleans itself up, and does nothing when reduced motion is on.
 */
export function launchConfetti(origin: HTMLElement | null, pieces = 36): void {
  if (!origin || prefersReducedMotion()) return
  const box = origin.getBoundingClientRect()
  const layer = document.createElement('div')
  layer.className = 'confetti-layer'
  layer.setAttribute('aria-hidden', 'true')

  for (let i = 0; i < pieces; i++) {
    const piece = document.createElement('span')
    piece.className = 'confetti-piece'
    const angle = (Math.random() - 0.5) * Math.PI * 1.2 - Math.PI / 2 // mostly upward
    const distance = 90 + Math.random() * 140
    piece.style.left = `${box.left + box.width / 2}px`
    piece.style.top = `${box.top + box.height / 2}px`
    piece.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length]
    piece.style.setProperty('--dx', `${Math.cos(angle) * distance}px`)
    piece.style.setProperty('--dy', `${Math.sin(angle) * distance}px`)
    piece.style.setProperty('--spin', `${Math.round((Math.random() - 0.5) * 720)}deg`)
    piece.style.animationDelay = `${Math.random() * 80}ms`
    layer.appendChild(piece)
  }

  document.body.appendChild(layer)
  window.setTimeout(() => layer.remove(), 1400)
}
