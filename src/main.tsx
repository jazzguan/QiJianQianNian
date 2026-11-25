import ReactDOM from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { Capacitor } from '@capacitor/core'
import App from './App'
import './index.css'

const Router = Capacitor.isNativePlatform() ? HashRouter : BrowserRouter

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Router>
    <App />
  </Router>,
)
