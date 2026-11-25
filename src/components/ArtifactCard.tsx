import { Link } from "react-router-dom";
import type { Porcelain } from "../types/porcelain";
export default function ArtifactCard({ item }: { item: Porcelain }) {
  return (
    <Link
      to={"/library/" + item.id}
      className="panel group overflow-hidden transition hover:-translate-y-0.5 hover:border-gold/50"
    >
      <div className="flex h-36 items-center justify-center overflow-hidden bg-[#222c3c] sm:h-52">
        {item.imageUrl ? (
          <img
            src={item.imageUrl}
            alt={item.name}
            loading="lazy"
            className="h-full w-full object-contain p-2 transition-transform duration-300 group-hover:scale-[1.04] sm:p-3"
          />
        ) : (
          <span className="text-xs text-white/50">暂无照片</span>
        )}
      </div>
      <div className="p-3 sm:p-4">
        <span className="eyebrow text-[0.62rem]">
          {item.dynastyName} · {item.category}
        </span>
        <h2 className="mt-1.5 font-display text-base leading-snug sm:text-lg">
          {item.name}
        </h2>
        <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-ink-soft">
          {item.summary}
        </p>
      </div>
    </Link>
  );
}
