import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useAuthStore, roleHomePath } from '@/store/authStore'
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
import AvisEcheanceList from '@/pages/avis-echeances/AvisEcheanceList'
import ContactList from '@/pages/contacts/ContactList'
import Automatisation from '@/pages/automatisation/Automatisation'
import TemplateEditor from '@/pages/templates/TemplateEditor'
import ProprietaireDashboard from '@/pages/proprietaire/ProprietaireDashboard'
import ProprietaireBiens from '@/pages/proprietaire/ProprietaireBiens'
import ProprietaireLocataires from '@/pages/proprietaire/ProprietaireLocataires'
import ProprietaireRevenus from '@/pages/proprietaire/ProprietaireRevenus'
import ProprietaireFiscal from '@/pages/proprietaire/ProprietaireFiscal'
import LocataireDashboard from '@/pages/locataire/LocataireDashboard'
import LocataireAvis from '@/pages/locataire/LocataireAvis'
import LocatairePaiements from '@/pages/locataire/LocatairePaiements'
import LocataireDocuments from '@/pages/locataire/LocataireDocuments'
import LocataireMessages from '@/pages/locataire/LocataireMessages'
import LocatairePayer from '@/pages/locataire/LocatairePayer'
import IncidentList from '@/pages/incidents/IncidentList'
import EntretienList from '@/pages/entretien/EntretienList'
import ProprietaireEntretien from '@/pages/proprietaire/ProprietaireEntretien'
import ProprietaireIncidents from '@/pages/proprietaire/ProprietaireIncidents'
import ProprietaireMessages from '@/pages/proprietaire/ProprietaireMessages'
import QuittanceList from '@/pages/quittances/QuittanceList'

function RoleBasedRedirect() {
  const { user, isAuthenticated } = useAuthStore()
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  return <Navigate to={roleHomePath(user.role)} replace />
}

function AppLayout() {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  // Vérification auth AVANT tout rendu de layout — élimine le flash de la sidebar
  if (!isAuthenticated || !user) {
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
      { index: true, element: <RoleBasedRedirect /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'tenants', element: <TenantList /> },
      { path: 'tenants/:id', element: <TenantDetail /> },
      { path: 'properties', element: <PropertyList /> },
      { path: 'properties/:id', element: <PropertyDetail /> },
      { path: 'leases', element: <LeaseList /> },
      { path: 'leases/:id', element: <LeaseDetail /> },
      { path: 'payments', element: <PaymentList /> },
      { path: 'quittances', element: <QuittanceList /> },
      { path: 'avis-echeances', element: <AvisEcheanceList /> },
      { path: 'contacts', element: <ContactList /> },
      { path: 'automatisation', element: <Automatisation /> },
      { path: 'templates', element: <TemplateEditor /> },
      { path: 'notifications', element: <NotificationList /> },
      { path: 'admin', element: <AdminUsers /> },
      { path: 'proprietaire', element: <ProprietaireDashboard /> },
      { path: 'proprietaire/biens', element: <ProprietaireBiens /> },
      { path: 'proprietaire/revenus', element: <ProprietaireRevenus /> },
      { path: 'proprietaire/locataires', element: <ProprietaireLocataires /> },
      { path: 'proprietaire/fiscal', element: <ProprietaireFiscal /> },
      { path: 'locataire', element: <LocataireDashboard /> },
      { path: 'locataire/avis-echeances', element: <LocataireAvis /> },
      { path: 'locataire/paiements', element: <LocatairePaiements /> },
      { path: 'locataire/payer', element: <LocatairePayer /> },
      { path: 'locataire/messages', element: <LocataireMessages /> },
      { path: 'locataire/documents', element: <LocataireDocuments /> },
      { path: 'incidents', element: <IncidentList /> },
      { path: 'entretiens', element: <EntretienList /> },
      { path: 'proprietaire/entretiens', element: <ProprietaireEntretien /> },
      { path: 'proprietaire/incidents', element: <ProprietaireIncidents /> },
      { path: 'proprietaire/messages', element: <ProprietaireMessages /> },
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
  { path: '*', element: <RoleBasedRedirect /> },
])
