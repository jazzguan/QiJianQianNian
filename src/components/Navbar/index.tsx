import { NavLink } from 'react-router-dom'
import { useAuth } from '../../stores/Platform'

const links = [
  { to: '/', label: '首页', end: true },
  { to: '/library', label: '文物库', end: false },
  { to: '/reconstruction', label: '三维复原', end: false },
  { to: '/timeline', label: '历史演化', end: false },
  { to: '/comparison', label: '形态对比', end: false },
  { to: '/ai-explain', label: 'AI讲解', end: false },
  { to: '/learning', label: '学习中心', end: false },
]

export function Navbar() {
  const { user } = useAuth()
  return (
    <header className="sticky top-0 z-50 border-b border-ink/10 bg-ivory/90 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        <NavLink to="/" className="group flex items-center gap-3">
          <span className="font-display text-xl font-semibold tracking-wide text-ink">
            器见千年
          </span>
          <span className="hidden text-xs tracking-[0.2em] text-ink-soft sm:inline">
            瓷器智能学习与演化分析
          </span>
        </NavLink>

        <nav className="flex flex-wrap items-center gap-4">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                'relative py-1 text-sm tracking-[0.1em] transition-colors ' +
                (isActive ? 'text-gold' : 'text-ink-soft hover:text-ink')
              }
            >
              {({ isActive }) => (
                <>
                  {l.label}
                  <span
                    className={
                      'absolute -bottom-0.5 left-1/2 h-px -translate-x-1/2 bg-gold transition-all ' +
                      (isActive ? 'w-full' : 'w-0')
                    }
                  />
                </>
              )}
            </NavLink>
          ))}
          <NavLink to="/auth" className="text-sm text-gold">
            {user?.username ?? '登录'}
          </NavLink>
        </nav>
      </div>
    </header>
  )
}

export default Navbar
