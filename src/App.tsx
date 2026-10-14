import { Route, Routes, Outlet } from 'react-router-dom'
import Navbar from './components/Navbar'
import { PorcelainModelManagerProvider } from './stores/PorcelainModelManager'
import Home from './pages/Home'
import Reconstruction from './pages/Reconstruction'
import TimelinePage from './pages/Timeline'
import Comparison from './pages/Comparison'
import AIExplain from './pages/AIExplain'
import Library from './pages/Library'
import Artifact from './pages/Artifact'
import Auth from './pages/Auth'
import Learning from './pages/Learning'
import { AuthProvider, CatalogProvider } from './stores/Platform'

function Layout() {
  return (
    <div className="flex min-h-full flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-ink/10 py-10 text-center">
        <p className="font-display text-sm tracking-[0.3em] text-ink">
          器见千年
        </p>
        <p className="mt-2 text-xs text-ink-soft">
          从一件瓷器，看见千年形制演化
        </p>
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <CatalogProvider>
        <PorcelainModelManagerProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/reconstruction" element={<Reconstruction />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/comparison" element={<Comparison />} />
              <Route path="/ai-explain" element={<AIExplain />} />
              <Route path="/library" element={<Library />} />
              <Route path="/library/:id" element={<Artifact />} />
              <Route path="/learning" element={<Learning />} />
              <Route path="/auth" element={<Auth />} />
            </Route>
          </Routes>
        </PorcelainModelManagerProvider>
      </CatalogProvider>
    </AuthProvider>
  )
}
