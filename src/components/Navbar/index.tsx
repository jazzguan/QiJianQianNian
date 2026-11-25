import { NavLink } from "react-router-dom";
import { useAuth } from "../../stores/Platform";

const links = [
  { to: "/", label: "首页", end: true },
  { to: "/library", label: "文物库", end: false },
  { to: "/reconstruction", label: "三维复原", end: false },
  { to: "/engine-compare", label: "引擎对比", end: false },
  { to: "/timeline", label: "历史演化", end: false },
  { to: "/comparison", label: "形态对比", end: false },
  { to: "/ai-explain", label: "AI讲解", end: false },
  { to: "/learning", label: "学习中心", end: false },
];

// 手机底部栏只放六个一级入口，"引擎对比"从三维复原页进入。
const mobileLinks = links.filter(
  (link) => link.to !== "/ai-explain" && link.to !== "/engine-compare",
);

export function Navbar() {
  const { user } = useAuth();
  return (
    <>
      <header className="app-header sticky top-0 z-50 border-b border-ink/10 bg-ivory/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6 lg:min-h-16 lg:h-auto lg:py-3">
          <NavLink to="/" className="group flex items-center gap-3">
            <span className="font-display text-lg font-semibold tracking-wide text-ink sm:text-xl">
              器见千年
            </span>
            <span className="hidden text-xs tracking-[0.2em] text-ink-soft sm:inline">
              瓷器智能学习与演化分析
            </span>
          </NavLink>

          <nav className="hidden items-center gap-5 lg:flex lg:flex-wrap">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  "relative shrink-0 whitespace-nowrap py-1 text-sm tracking-[0.1em] transition-colors " +
                  (isActive ? "text-gold" : "text-ink-soft hover:text-ink")
                }
              >
                {({ isActive }) => (
                  <>
                    {l.label}
                    <span
                      className={
                        "absolute -bottom-0.5 left-1/2 h-px -translate-x-1/2 bg-gold transition-all " +
                        (isActive ? "w-full" : "w-0")
                      }
                    />
                  </>
                )}
              </NavLink>
            ))}
            <NavLink
              to="/auth"
              className="shrink-0 whitespace-nowrap text-sm text-gold"
            >
              {user?.username ?? "登录"}
            </NavLink>
          </nav>
          <NavLink
            to="/auth"
            className="max-w-28 truncate rounded-full border border-gold/35 px-3 py-1.5 text-xs text-gold lg:hidden"
          >
            {user?.username ?? "登录"}
          </NavLink>
        </div>
      </header>
      <nav className="mobile-bottom-nav lg:hidden" aria-label="手机端主导航">
        {mobileLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              "mobile-bottom-link " + (isActive ? "is-active" : "")
            }
          >
            <span className="mobile-bottom-dot" />
            <span>
              {link.label
                .replace("三维", "")
                .replace("历史", "")
                .replace("形态", "")
                .replace("中心", "")}
            </span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}

export default Navbar;
