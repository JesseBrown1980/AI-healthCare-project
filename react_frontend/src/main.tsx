import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './i18n/config' // Initialize i18n
import './index.css'
import './styles/global.css'
import './components/ui/ui.css'
import './components/charts/charts.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
