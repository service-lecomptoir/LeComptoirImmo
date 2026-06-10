import { useRef, useEffect, useState, lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useAuthStore, roleHomePath } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { featureForPath, isFeatureAllowed, firstAllowedPath } from '@/lib/features'
// Login & Landing restent en import direct : ils servent au tout premier rendu
// (avant authentification) → pas de bénéfice à les différer.
import Login from '@/pages/Login'
import Landing from '@/pages/Landing'

// ── Pages authentifiées : chargées à la demande (code-splitting) ──────────────
// Chaque route ne télécharge son JS que lorsqu'on y navigue → bundle initial
// bien plus léger, premier affichage plus rapide.
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const TenantList = lazy(() => import('@/pages/tenants/TenantList'))
const TenantDetail = lazy(() => import('@/pages/tenants/TenantDetail'))
const OwnerList = lazy(() => import('@/pages/owners/OwnerList'))
const OwnerDetail = lazy(() => import('@/pages/owners/OwnerDetail'))
const PropertyList = lazy(() => import('@/pages/properties/PropertyList'))
const PropertyDetail = lazy(() => import('@/pages/properties/PropertyDetail'))
const LeaseList = lazy(() => import('@/pages/leases/LeaseList'))
const LeaseDetail = lazy(() => import('@/pages/leases/LeaseDetail'))
const PaymentList = lazy(() => import('@/pages/payments/PaymentList'))
const NotificationList = lazy(() => import('@/pages/notifications/NotificationList'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AvisEcheanceList = lazy(() => import('@/pages/avis-echeances/AvisEcheanceList'))
const ContactList = lazy(() => import('@/pages/contacts/ContactList'))
const Automatisation = lazy(() => import('@/pages/automatisation/Automatisation'))
const TemplateEditor = lazy(() => import('@/pages/templates/TemplateEditor'))
const ProprietaireDashboard = lazy(() => import('@/pages/proprietaire/ProprietaireDashboard'))
const ProprietaireBiens = lazy(() => import('@/pages/proprietaire/ProprietaireBiens'))
const ProprietaireLocataires = lazy(() => import('@/pages/proprietaire/ProprietaireLocataires'))
const ProprietaireRevenus = lazy(() => import('@/pages/proprietaire/ProprietaireRevenus'))
const ProprietaireFiscal = lazy(() => import('@/pages/proprietaire/ProprietaireFiscal'))
const LocataireDashboard = lazy(() => import('@/pages/locataire/LocataireDashboard'))
const LocataireAvis = lazy(() => import('@/pages/locataire/LocataireAvis'))
const LocatairePaiements = lazy(() => import('@/pages/locataire/LocatairePaiements'))
const LocataireDocuments = lazy(() => import('@/pages/locataire/LocataireDocuments'))
const LocataireMessages = lazy(() => import('@/pages/locataire/LocataireMessages'))
const LocatairePayer = lazy(() => import('@/pages/locataire/LocatairePayer'))
const IncidentList = lazy(() => import('@/pages/incidents/IncidentList'))
const EntretienList = lazy(() => import('@/pages/entretien/EntretienList'))
const ProprietaireEntretien = lazy(() => import('@/pages/proprietaire/ProprietaireEntretien'))
const ProprietaireIncidents = lazy(() => import('@/pages/proprietaire/ProprietaireIncidents'))
const ProprietaireMessages = lazy(() => import('@/pages/proprietaire/ProprietaireMessages'))
const QuittanceList = lazy(() => import('@/pages/quittances/QuittanceList'))
const OffersManager = lazy(() => import('@/pages/offers/OffersManager'))
const LocataireOffres = lazy(() => import('@/pages/locataire/LocataireOffres'))
const MonAbonnement = lazy(() => import('@/pages/subscription/MonAbonnement'))
const MonProfil = lazy(() => import('@/pages/profil/MonProfil'))
const GuideUtilisateur = lazy(() => import('@/pages/guide/GuideUtilisateur'))
const ScoringList = lazy(() => import('@/pages/scoring/ScoringList'))
const FinancesParProprietaire = lazy(() => import('@/pages/finances/FinancesParProprietaire'))
const Actualisation = lazy(() => import('@/pages/actualisation/Actualisation'))
const DocumentsCaf = lazy(() => import('@/pages/documents-caf/DocumentsCaf'))
const DiffusionPage = lazy(() => import('@/pages/publishing/DiffusionPage'))
const PropertyPublish = lazy(() => import('@/pages/publishing/PropertyPublish'))
const AnnoncePublic = lazy(() => import('@/pages/public/AnnoncePublic'))
const CandidaturesPage = lazy(() => import('@/pages/candidatures/CandidaturesPage'))
const SortiesPage = lazy(() => import('@/pages/sorties/SortiesPage'))

// Indicateur de chargement pendant le téléchargement d'une page différée (lazy).
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  )
}

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
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/', element: <PublicHome /> },
  {
    path: '/annonce/:token',
    element: (
      <Suspense fallback={<PageLoader />}>
        <AnnoncePublic />
      </Suspense>
    ),
  },
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
      { path: 'properties/:id/publish', element: <PropertyPublish /> },
      { path: 'diffusion', element: <DiffusionPage /> },
      { path: 'candidatures', element: <CandidaturesPage /> },
      { path: 'sorties', element: <SortiesPage /> },
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
