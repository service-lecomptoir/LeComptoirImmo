import { useEffect, useState } from 'react'
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
import InvoiceList from '@/pages/invoices/InvoiceList'
import SejourList from '@/pages/sejour/SejourList'

function AppLayout() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Ferme le drawer mobile à chaque navigation
  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuClick={() => setSidebarOpen(true)} />
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
      { path: 'sejour', element: <SejourList /> },
      { path: 'plans', element: <PlanList /> },
      { path: 'factures', element: <InvoiceList /> },
      { path: 'demandes', element: <SubscriptionList /> },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
])
