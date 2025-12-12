import { BrowserRouter, Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import DashboardPage from './pages/DashboardPage'
import FeedbackPage from './pages/FeedbackPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import PatientPage from './pages/PatientPage'
import QueryPage from './pages/QueryPage'
import SettingsPage from './pages/SettingsPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <NavBar />
        <main className="app__content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/patient/:id?" element={<PatientPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
