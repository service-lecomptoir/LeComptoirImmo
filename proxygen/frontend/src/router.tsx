import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useAuthStore } from '@/store/authStore'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import GestionnaireList from '@/pages/gestionnaires/GestionnaireList'
import GestionnaireDetail from '@/pages/gestionnaires/GestionnaireDetail'
import PlanList from '@/pages/plans/PlanList'
import SubscriptionList from '@/pages/subscriptions/SubscriptionList'

function AppLayout() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'gestionnaires', element: <GestionnaireList /> },
      { path: 'gestionnaires/:id', element: <GestionnaireDetail /> },
      { path: 'plans', element: <PlanList /> },
      { path: 'demandes', element: <SubscriptionList /> },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
])
