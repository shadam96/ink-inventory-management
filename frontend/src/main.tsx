import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './i18n'
import { applyDocumentDirection } from './i18n/applyDocumentDirection'
import { Toaster } from 'sonner'

// Sync <html lang>/<html dir> with i18next *before* React mounts to avoid
// a flash of the wrong direction on first paint.
applyDocumentDirection()

// Install prompt is disabled for now; also suppress Chrome's native
// "Add to Home screen" mini-infobar, which appears if this isn't prevented.
window.addEventListener('beforeinstallprompt', (e) => e.preventDefault())

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
    <Toaster position="top-center" richColors />
  </React.StrictMode>,
)
