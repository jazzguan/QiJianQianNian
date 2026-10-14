import { Link } from 'react-router-dom'
import type { Porcelain } from '../types/porcelain'
export default function ArtifactCard({ item }: { item: Porcelain }) {
  return (
    <Link
      to={'/library/' + item.id}
      className="panel overflow-hidden transition hover:border-gold/50"
    >
      <img
        src={item.imageUrl}
        alt={item.name}
        loading="lazy"
        className="h-56 w-full bg-ivory-deep object-contain p-3"
      />
      <div className="p-4">
        <span className="eyebrow">
          {item.dynastyName} · {item.category}
        </span>
        <h2 className="mt-2 font-display text-lg">{item.name}</h2>
        <p className="mt-2 line-clamp-2 text-xs text-ink-soft">
          {item.summary}
        </p>
      </div>
    </Link>
  )
}
