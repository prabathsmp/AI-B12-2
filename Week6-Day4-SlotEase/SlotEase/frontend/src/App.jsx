import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import { PageLoader } from './components/ui'
import Landing from './pages/Landing'
import AuthPage from './pages/AuthPage'
import Booking from './pages/Booking'
import DashboardLayout from './pages/dashboard/Layout'
import Today from './pages/dashboard/Today'
import Calendar from './pages/dashboard/Calendar'
import Services from './pages/dashboard/Services'
import Hours from './pages/dashboard/Hours'
import Customers from './pages/dashboard/Customers'
import Stats from './pages/dashboard/Stats'
import Settings from './pages/dashboard/Settings'

function RequireAuth({ children }) {
  const { loading, user } = useAuth()
  if (loading) return <PageLoader />
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/dashboard" element={<RequireAuth><DashboardLayout /></RequireAuth>}>
        <Route index element={<Today />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="services" element={<Services />} />
        <Route path="hours" element={<Hours />} />
        <Route path="customers" element={<Customers />} />
        <Route path="stats" element={<Stats />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      {/* Public booking page: slotease.app/glow-salon */}
      <Route path="/:slug" element={<Booking />} />
    </Routes>
  )
}
