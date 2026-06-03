import { useRef, useEffect, useState } from 'react'
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useAuthStore, roleHomePath } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { featureForPath, isFeatureAllowed, firstAllowedPath } from '@/lib/features'
import Login from '@/pages/Login'
import Landing from '@/pages/Landing'
import Dashboard from '@/pages/Dashboard'
import TenantList from '@/pages/tenants/TenantList'
import TenantDetail from '@/pages/tenants/TenantDetail'
import OwnerList from '@/pages/owners/OwnerList'
import OwnerDetail from '@/pages/owners/OwnerDetail'
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
import OffersManager from '@/pages/offers/OffersManager'
import LocataireOffres from '@/pages/locataire/LocataireOffres'
import MonAbonnement from '@/pages/subscription/MonAbonnement'
import MonProfil from '@/pages/profil/MonProfil'
import GuideUtilisateur from '@/pages/guide/GuideUtilisateur'
import ScoringList from '@/pages/scoring/ScoringList'
import FinancesParProprietaire from '@/pages/finances/FinancesParProprietaire'
import Actualisation from '@/pages/actualisation/Actualisation'
import DocumentsCaf from '@/pages/documents-caf/DocumentsCaf'

function RoleBasedRedirect() {
  const { user, isAuthenticated } = useAuthStore()
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  return <Navigate to={roleHomePath(user.role)} replace />
}

// Accueil public : landing marketing pour les visiteurs, redirection vers l'espace
// pour les utilisateurs déjà connectés.
function PublicHome() {
  const { user, isAuthenticated } = useAuthStore()
  if (isAuthenticated && user) return <Navigate to={roleHomePath(user.role)} replace />
  return <Landing />
}

function AppLayout() {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const [navOpen, setNavOpen] = useState(false)

  // Entitlements par plan (gestionnaire/GP) : charge + garde les routes.
  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio'
  const { features, loaded, loadFeatures } = useFeaturesStore()
  useEffect(() => {
    if (isManager) loadFeatures()
  }, [isManager, loadFeatures])

  // À chaque changement de page, on repositionne en haut. Le scroll réel est porté
  // par la fenêtre (conteneur en min-h-screen, pas de hauteur bornée) → window.scrollTo ;
  // on remet aussi <main> à 0 au cas où il deviendrait le conteneur scrollable.
  // On referme aussi le menu mobile à chaque navigation.
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0 })
    document.documentElement.scrollTop = 0
    mainRef.current?.scrollTo({ top: 0, left: 0 })
    setNavOpen(false)
  }, [location.pathname])

  // Vérification auth AVANT tout rendu de layout — élimine le flash de la sidebar
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Garde d'accès : une fonctionnalité non incluse dans le plan est inaccessible
  // même par URL directe → redirige vers la première route autorisée.
  if (isManager && loaded) {
    const feat = featureForPath(location.pathname)
    if (feat && !isFeatureAllowed(features, feat)) {
      return <Navigate to={firstAllowedPath(features)} replace />
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar mobileOpen={navOpen} onClose={() => setNavOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuClick={() => setNavOpen(true)} />
        <main ref={mainRef} className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/', element: <PublicHome /> },
  {
    element: <AppLayout />,
    children: [
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'tenants', element: <TenantList /> },
      { path: 'tenants/:id', element: <TenantDetail /> },
      { path: 'owners', element: <OwnerList /> },
      { path: 'owners/:id', element: <OwnerDetail /> },
      { path: 'properties', element: <PropertyList /> },
      { path: 'properties/:id', element: <PropertyDetail /> },
      { path: 'leases', element: <LeaseList /> },
      { path: 'leases/:id', element: <LeaseDetail /> },
      { path: 'scoring', element: <ScoringList /> },
      { path: 'payments', element: <PaymentList /> },
      { path: 'quittances', element: <QuittanceList /> },
      { path: 'avis-echeances', element: <AvisEcheanceList /> },
      { path: 'contacts', element: <ContactList /> },
      { path: 'automatisation', element: <Automatisation /> },
      { path: 'templates', element: <TemplateEditor /> },
      { path: 'profil', element: <MonProfil /> },
      { path: 'guide', element: <GuideUtilisateur /> },
      { path: 'notifications', element: <NotificationList /> },
      { path: 'admin', element: <AdminUsers /> },
      { path: 'finances/revenus', element: <FinancesParProprietaire view="revenus" /> },
      { path: 'finances/biens', element: <FinancesParProprietaire view="biens" /> },
      { path: 'finances/fiscal', element: <FinancesParProprietaire view="fiscal" /> },
      { path: 'actualisation', element: <Actualisation /> },
      { path: 'documents-caf', element: <DocumentsCaf /> },
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
      { path: 'offres', element: <OffersManager /> },
      { path: 'locataire/offres', element: <LocataireOffres /> },
      { path: 'abonnement', element: <MonAbonnement /> },
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
