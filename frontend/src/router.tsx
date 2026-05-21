import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import TenantList from '@/pages/tenants/TenantList'
import TenantDetail from '@/pages/tenants/TenantDetail'
import PropertyList from '@/pages/properties/PropertyList'
import PropertyDetail from '@/pages/properties/PropertyDetail'
import LeaseList from '@/pages/leases/LeaseList'
import LeaseDetail from '@/pages/leases/LeaseDetail'
import PaymentList from '@/pages/payments/PaymentList'
import NotificationList from '@/pages/notifications/NotificationList'
import AdminUsers from '@/pages/admin/AdminUsers'

// Layout principal avec sidebar
function AppLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-auto">
          <ProtectedRoute />
        </main>
      </div>
    </div>
  )
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'tenants', element: <TenantList /> },
      { path: 'tenants/:id', element: <TenantDetail /> },
      { path: 'properties', element: <PropertyList /> },
      { path: 'properties/:id', element: <PropertyDetail /> },
      { path: 'leases', element: <LeaseList /> },
      { path: 'leases/:id', element: <LeaseDetail /> },
      { path: 'payments', element: <PaymentList /> },
      { path: 'notifications', element: <NotificationList /> },
      { path: 'admin', element: <AdminUsers /> },
      {
        path: 'unauthorized',
        element: (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <h2 className="text-xl font-bold text-gray-900">Accès refusé</h2>
              <p className="text-gray-500 mt-2">Vous n'avez pas les permissions nécessaires.</p>
            </div>
          </div>
        ),
      },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
])
