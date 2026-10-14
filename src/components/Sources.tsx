import type { Source } from '../types/porcelain'
export default function Sources({ sources = [] }: { sources?: Source[] }) {
  return sources.length ? (
    <ul className="mt-3 space-y-1 text-xs text-ink-soft">
      {sources.map((s, i) => (
        <li key={s.url + '-' + i}>
          <a
            href={s.url}
            target="_blank"
            rel="noreferrer"
            className="text-blue hover:underline"
          >
            [{s.id ?? i + 1}] {s.title}
          </a>{' '}
          · {s.institution} {s.license}
        </li>
      ))}
    </ul>
  ) : null
}
