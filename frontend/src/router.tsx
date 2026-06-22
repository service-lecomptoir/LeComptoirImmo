import { useRef, useEffect, useState, lazy, Suspense } from 'react'
import type { ComponentType } from 'react'
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom'

// Recharge la page (une seule fois / 10 s) quand un chunk lazy a disparu après un
// déploiement : l'onglet ouvert référence d'anciens fichiers hashés supprimés
// → on récupère le nouvel index.html + les chunks à jour au lieu de planter.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function lazyPage<T extends ComponentType<any>>(factory: () => Promise<{ default: T }>) {
  return lazy(() =>
    factory().catch((err) => {
      const KEY = 'chunk-reload-ts'
      const last = Number(sessionStorage.getItem(KEY) || '0')
      if (Date.now() - last > 10000) {
        sessionStorage.setItem(KEY, String(Date.now()))
        window.location.reload()
        return new Promise<{ default: T }>(() => {}) // jamais résolue : reload en cours
      }
      throw err
    }),
  )
}
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { ForcePasswordChange } from '@/components/auth/ForcePasswordChange'
import { useAuthStore, roleHomePath } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { featureForPath, isFeatureAllowed, firstAllowedPath } from '@/lib/features'
import { titleForPath } from '@/lib/navigation'
// Login & Landing restent en import direct : ils servent au tout premier rendu
// (avant authentification) → pas de bénéfice à les différer.
import Login from '@/pages/Login'
import Landing from '@/pages/Landing'
import { RouteError } from '@/components/common/RouteError'

// ── Pages authentifiées : chargées à la demande (code-splitting) ──────────────
// Chaque route ne télécharge son JS que lorsqu'on y navigue → bundle initial
// bien plus léger, premier affichage plus rapide.
const Dashboard = lazyPage(() => import('@/pages/Dashboard'))
const TenantList = lazyPage(() => import('@/pages/tenants/TenantList'))
const TenantDetail = lazyPage(() => import('@/pages/tenants/TenantDetail'))
const OwnerList = lazyPage(() => import('@/pages/owners/OwnerList'))
const OwnerDetail = lazyPage(() => import('@/pages/owners/OwnerDetail'))
const PropertyList = lazyPage(() => import('@/pages/properties/PropertyList'))
const PropertyDetail = lazyPage(() => import('@/pages/properties/PropertyDetail'))
const LeaseList = lazyPage(() => import('@/pages/leases/LeaseList'))
const LeaseDetail = lazyPage(() => import('@/pages/leases/LeaseDetail'))
const PaymentList = lazyPage(() => import('@/pages/payments/PaymentList'))
const NotificationList = lazyPage(() => import('@/pages/notifications/NotificationList'))
const AdminUsers = lazyPage(() => import('@/pages/admin/AdminUsers'))
const MentionsLegales = lazyPage(() => import('@/pages/legal/MentionsLegales'))
const Confidentialite = lazyPage(() => import('@/pages/legal/Confidentialite'))
const AvisEcheanceList = lazyPage(() => import('@/pages/avis-echeances/AvisEcheanceList'))
const ContactList = lazyPage(() => import('@/pages/contacts/ContactList'))
const Automatisation = lazyPage(() => import('@/pages/automatisation/Automatisation'))
const TemplateEditor = lazyPage(() => import('@/pages/templates/TemplateEditor'))
const ProprietaireDashboard = lazyPage(() => import('@/pages/proprietaire/ProprietaireDashboard'))
const ProprietaireBiens = lazyPage(() => import('@/pages/proprietaire/ProprietaireBiens'))
const ProprietaireAnnonces = lazyPage(() => import('@/pages/proprietaire/ProprietaireAnnonces'))
const ProprietaireLocataires = lazyPage(() => import('@/pages/proprietaire/ProprietaireLocataires'))
const ProprietaireRevenus = lazyPage(() => import('@/pages/proprietaire/ProprietaireRevenus'))
const ProprietaireFiscal = lazyPage(() => import('@/pages/proprietaire/ProprietaireFiscal'))
const LocataireDashboard = lazyPage(() => import('@/pages/locataire/LocataireDashboard'))
const LocataireAvis = lazyPage(() => import('@/pages/locataire/LocataireAvis'))
const LocatairePaiements = lazyPage(() => import('@/pages/locataire/LocatairePaiements'))
const LocataireDocuments = lazyPage(() => import('@/pages/locataire/LocataireDocuments'))
const LocatairePayer = lazyPage(() => import('@/pages/locataire/LocatairePayer'))
const LocatairePayerForm = lazyPage(() => import('@/pages/locataire/LocatairePayerForm'))
const LocataireCarteSumup = lazyPage(() => import('@/pages/locataire/LocataireCarteSumup'))
const MesOptions = lazyPage(() => import('@/pages/profil/MesOptions'))
const LocataireDemarches = lazyPage(() => import('@/pages/locataire/LocataireDemarches'))
const IncidentList = lazyPage(() => import('@/pages/incidents/IncidentList'))
const EntretienList = lazyPage(() => import('@/pages/entretien/EntretienList'))
const ProprietaireEntretien = lazyPage(() => import('@/pages/proprietaire/ProprietaireEntretien'))
const ProprietaireIncidents = lazyPage(() => import('@/pages/proprietaire/ProprietaireIncidents'))
const ProprietaireMessages = lazyPage(() => import('@/pages/proprietaire/ProprietaireMessages'))
const QuittanceList = lazyPage(() => import('@/pages/quittances/QuittanceList'))
const OffersManager = lazyPage(() => import('@/pages/offers/OffersManager'))
const LocataireOffres = lazyPage(() => import('@/pages/locataire/LocataireOffres'))
const MonAbonnement = lazyPage(() => import('@/pages/subscription/MonAbonnement'))
const MonProfil = lazyPage(() => import('@/pages/profil/MonProfil'))
const GuideUtilisateur = lazyPage(() => import('@/pages/guide/GuideUtilisateur'))
const ScoringList = lazyPage(() => import('@/pages/scoring/ScoringList'))
const FinancesParProprietaire = lazyPage(() => import('@/pages/finances/FinancesParProprietaire'))
const ComptabiliteGestion = lazyPage(() => import('@/pages/finances/ComptabiliteGestion'))
const ComptaMandant = lazyPage(() => import('@/pages/finances/ComptaMandant'))
const Actualisation = lazyPage(() => import('@/pages/actualisation/Actualisation'))
const DocumentsCaf = lazyPage(() => import('@/pages/documents-caf/DocumentsCaf'))
const DiffusionPage = lazyPage(() => import('@/pages/publishing/DiffusionPage'))
const PropertyPublish = lazyPage(() => import('@/pages/publishing/PropertyPublish'))
const AnnoncePublic = lazyPage(() => import('@/pages/public/AnnoncePublic'))
const CandidatureUpload = lazyPage(() => import('@/pages/public/CandidatureUpload'))
const CandidatureVisit = lazyPage(() => import('@/pages/public/CandidatureVisit'))
const CandidaturesPage = lazyPage(() => import('@/pages/candidatures/CandidaturesPage'))
const SortiesPage = lazyPage(() => import('@/pages/sorties/SortiesPage'))
const SignalementList = lazyPage(() => import('@/pages/signalements/SignalementList'))
const LocataireSignaler = lazyPage(() => import('@/pages/locataire/LocataireSignaler'))

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

  // Titre de l'onglet : « Le Comptoir Immo | <page courante> » (selon la sidebar).
  useEffect(() => {
    const t = titleForPath(location.pathname, user?.role)
    document.title = t ? `Le Comptoir Immo | ${t}` : 'Le Comptoir Immo'
  }, [location.pathname, user?.role])

  // Vérification auth AVANT tout rendu de layout — élimine le flash de la sidebar
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Compte en mot de passe temporaire (gestionnaire provisionné par Alice, ou
  // propriétaire / locataire créé par un gestionnaire) : on force la définition
  // d'un mot de passe personnel avant tout accès, quel que soit le rôle.
  if (user.must_change_password) {
    return <ForcePasswordChange />
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
    path: '/mentions-legales',
    errorElement: <RouteError />,
    element: <Suspense fallback={<PageLoader />}><MentionsLegales /></Suspense>,
  },
  {
    path: '/confidentialite',
    errorElement: <RouteError />,
    element: <Suspense fallback={<PageLoader />}><Confidentialite /></Suspense>,
  },
  {
    path: '/annonce/:token',
    errorElement: <RouteError />,
    element: (
      <Suspense fallback={<PageLoader />}>
        <AnnoncePublic />
      </Suspense>
    ),
  },
  {
    path: '/candidature/:token',
    errorElement: <RouteError />,
    element: (
      <Suspense fallback={<PageLoader />}>
        <CandidatureUpload />
      </Suspense>
    ),
  },
  {
    path: '/candidature/:token/visite',
    errorElement: <RouteError />,
    element: (
      <Suspense fallback={<PageLoader />}>
        <CandidatureVisit />
      </Suspense>
    ),
  },
  {
    element: <AppLayout />,
    errorElement: <RouteError />,
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
      { path: 'profil/options', element: <MesOptions /> },
      { path: 'guide', element: <GuideUtilisateur /> },
      { path: 'notifications', element: <NotificationList /> },
      { path: 'admin', element: <AdminUsers /> },
      { path: 'comptabilite', element: <ComptabiliteGestion /> },
      { path: 'comptabilite/mandant', element: <ComptaMandant /> },
      { path: 'finances/revenus', element: <FinancesParProprietaire view="revenus" /> },
      { path: 'finances/biens', element: <FinancesParProprietaire view="biens" /> },
      { path: 'finances/fiscal', element: <FinancesParProprietaire view="fiscal" /> },
      { path: 'actualisation', element: <Actualisation /> },
      { path: 'documents-caf', element: <DocumentsCaf /> },
      { path: 'proprietaire', element: <ProprietaireDashboard /> },
      { path: 'proprietaire/biens', element: <ProprietaireBiens /> },
      { path: 'proprietaire/annonces', element: <ProprietaireAnnonces /> },
      { path: 'proprietaire/revenus', element: <ProprietaireRevenus /> },
      { path: 'proprietaire/locataires', element: <ProprietaireLocataires /> },
      { path: 'proprietaire/fiscal', element: <ProprietaireFiscal /> },
      { path: 'locataire', element: <LocataireDashboard /> },
      { path: 'locataire/avis-echeances', element: <LocataireAvis /> },
      { path: 'locataire/paiements', element: <LocatairePaiements /> },
      { path: 'locataire/demarches', element: <LocataireDemarches /> },
      { path: 'locataire/payer', element: <LocatairePayer /> },
      { path: 'locataire/payer/regler/:method', element: <LocatairePayerForm /> },
      { path: 'locataire/payer/carte', element: <LocataireCarteSumup /> },
      { path: 'locataire/documents', element: <LocataireDocuments /> },
      { path: 'incidents', element: <IncidentList /> },
      { path: 'signalements', element: <SignalementList /> },
      { path: 'locataire/signaler', element: <LocataireSignaler /> },
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
