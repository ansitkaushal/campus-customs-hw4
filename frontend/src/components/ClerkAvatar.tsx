/** "Benny", the Campus Customs counter clerk: a friendly bulldog in a varsity cap, drawn in SVG. */
export const CLERK_NAME = 'Benny'

export default function ClerkAvatar({ size = 36, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      className={`clerk-avatar ${className}`}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={`${CLERK_NAME}, the Campus Customs clerk`}
    >
      <circle cx="32" cy="32" r="32" fill="#f2b705" />
      {/* ears */}
      <path d="M13 22 L9 10 L22 17 Z" fill="#8a6a4a" />
      <path d="M51 22 L55 10 L42 17 Z" fill="#8a6a4a" />
      {/* head */}
      <ellipse cx="32" cy="36" rx="20" ry="18" fill="#f4e6cf" />
      {/* jowls */}
      <ellipse cx="24" cy="44" rx="9" ry="7" fill="#ead6b6" />
      <ellipse cx="40" cy="44" rx="9" ry="7" fill="#ead6b6" />
      {/* eyes */}
      <circle cx="24" cy="33" r="3" fill="#0c2340" />
      <circle cx="40" cy="33" r="3" fill="#0c2340" />
      <circle cx="25" cy="32" r="1" fill="#fff" />
      <circle cx="41" cy="32" r="1" fill="#fff" />
      {/* nose + smile */}
      <ellipse cx="32" cy="40" rx="5" ry="3.5" fill="#0c2340" />
      <path d="M26 46 Q32 51 38 46" stroke="#0c2340" strokeWidth="2" fill="none" strokeLinecap="round" />
      {/* varsity cap */}
      <path d="M12 22 Q32 4 52 22 Z" fill="#0c2340" />
      <rect x="10" y="20" width="44" height="5" rx="2.5" fill="#0c2340" />
      <text x="32" y="19" textAnchor="middle" fontSize="9" fontWeight="700" fill="#f2b705" fontFamily="Georgia, serif">
        Y
      </text>
    </svg>
  )
}
