/**
 * Source de vérité UNIQUE de la navigation par rôle.
 *
 * Ces tableaux pilotent À LA FOIS le menu latéral (Sidebar) et la génération
 * automatique des « rubriques » du Guide utilisateur. Conséquence : tout
 * ajout / renommage / retrait d'une fonctionnalité ici se répercute
 * automatiquement dans le menu ET dans le guide, sans double saisie.
 *
 * La description d'une rubrique provient (par ordre de priorité) :
 *   1. d'une entrée explicite dans ROUTE_DESCRIPTIONS (formulation par route),
 *   2. sinon du catalogue partagé FEATURE_DESCRIPTIONS via featureForPath().
 */
import type { ElementType } from 'react'
import {
  LayoutDashboard, Users, Building2, FileText,
  CreditCard, Settings, Calendar,
  Home, Archive, BookUser, PenSquare, BarChart3,
  Calculator, MessageSquare, MessagesSquare, Send, Wrench, Wallet, FileCheck,
  ShoppingBag, KeyRound, TrendingUp, Landmark, ShieldCheck, Megaphone,
  UserCheck, DoorOpen, ConciergeBell, BookText, HandCoins,
} from 'lucide-react'
import type { Role } from '@/types/auth'
import { featureForPath, FEATURE_DESCRIPTIONS } from '@/lib/features'

export interface NavItem {
  to?: string
  icon?: ElementType
  label: string
  roles?: Role[]
  isSeparator?: boolean
}

// Navigation Gestionnaire mandataire / Admin
export const navGestionnaire: NavItem[] = [
  { label: 'Mise en location', isSeparator: true },
  { to: '/diffusion', icon: Megaphone, label: 'Publication des annonces' },
  { to: '/candidatures', icon: UserCheck, label: 'Candidatures' },
  { label: 'Gestion locative', isSeparator: true },
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/owners', icon: KeyRound, label: 'Propriétaires' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/scoring', icon: ShieldCheck, label: 'Scoring locataires' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/actualisation', icon: TrendingUp, label: 'Révision des loyers et charges' },
  { to: '/automatisation', icon: Send, label: 'Communication et automatisation' },
  { to: '/templates', icon: PenSquare, label: 'Atelier de documents' },
  { to: '/incidents', icon: MessagesSquare, label: 'Démarche' },
  { to: '/signalements', icon: ConciergeBell, label: 'Espace gardien' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/documents-caf', icon: Landmark, label: 'Espace CAF' },
  { to: '/sorties', icon: DoorOpen, label: 'Sortie du locataire' },
  { to: '/admin', icon: Settings, label: 'Gestion des utilisateurs' },
  { label: 'Finance et Comptabilité', isSeparator: true },
  { to: '/finances/revenus', icon: Wallet, label: 'Encaissements' },
  { to: '/comptabilite', icon: BookText, label: 'Comptabilité' },
  { to: '/comptabilite/mandant', icon: HandCoins, label: 'Compta mandant' },
  { to: '/finances/biens', icon: BarChart3, label: 'Performance biens' },
  { to: '/finances/fiscal', icon: Calculator, label: 'Liasse fiscale' },
]

// Le COMPTABLE voit le MÊME menu que le gestionnaire (lecture intégrale) ; ses
// actions d'écriture sont bloquées côté serveur sauf encaissement/avis/quittances,
// et masquées côté UI via canManage(). -> navForRole renvoie navGestionnaire.

// Navigation Propriétaire
export const navProprietaire: NavItem[] = [
  { label: 'Mise en location', isSeparator: true },
  { to: '/proprietaire/annonces', icon: Megaphone, label: 'Annonces de mes biens' },
  { to: '/candidatures', icon: UserCheck, label: 'Candidatures' },
  { label: 'Mon espace', isSeparator: true },
  { to: '/proprietaire', icon: LayoutDashboard, label: 'Mon tableau de bord' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Mes biens' },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/locataires', icon: Users, label: 'Mes locataires' },
  { to: '/proprietaire/incidents', icon: MessagesSquare, label: 'Démarche' },
  { to: '/proprietaire/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/proprietaire/messages', icon: MessageSquare, label: 'Messages' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
]

// Route → clé de rubrique propriétaire (pour filtrer la nav selon la visibilité
// réglée par le gestionnaire). Une route absente de la table est toujours visible.
export const PROPRIO_SECTION_BY_PATH: Record<string, string> = {
  '/proprietaire': 'dashboard',
  '/proprietaire/biens': 'biens',
  '/proprietaire/revenus': 'revenus',
  '/proprietaire/locataires': 'locataires',
  '/proprietaire/incidents': 'incidents',
  '/proprietaire/entretiens': 'entretiens',
  '/proprietaire/messages': 'messages',
  '/proprietaire/fiscal': 'fiscal',
  '/proprietaire/annonces': 'annonces',
  '/candidatures': 'candidatures',
}
export function proprioSectionForPath(to?: string): string | undefined {
  return to ? PROPRIO_SECTION_BY_PATH[to] : undefined
}

// Navigation Gestionnaire-Propriétaire : identique au mandataire SANS « Vue propriétaire »
export const navGestionnairePropio: NavItem[] = [
  { label: 'Mise en location', isSeparator: true },
  { to: '/diffusion', icon: Megaphone, label: 'Publication des annonces' },
  { to: '/candidatures', icon: UserCheck, label: 'Candidatures' },
  { label: 'Gestion locative', isSeparator: true },
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/scoring', icon: ShieldCheck, label: 'Scoring locataires' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/actualisation', icon: TrendingUp, label: 'Révision des loyers et charges' },
  { to: '/automatisation', icon: Send, label: 'Communication et automatisation' },
  { to: '/templates', icon: PenSquare, label: 'Atelier de documents' },
  { to: '/incidents', icon: MessagesSquare, label: 'Démarche' },
  { to: '/signalements', icon: ConciergeBell, label: 'Espace gardien' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/documents-caf', icon: Landmark, label: 'Espace CAF' },
  { to: '/sorties', icon: DoorOpen, label: 'Sortie du locataire' },
  { to: '/admin', icon: Settings, label: 'Gestion des utilisateurs' },
  { label: 'Finance et Comptabilité', isSeparator: true },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Encaissements' },
  { to: '/comptabilite', icon: BookText, label: 'Comptabilité' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Performance biens' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
]

// Navigation Locataire
export const navLocataire: NavItem[] = [
  { to: '/locataire', icon: Home, label: 'Mon espace' },
  { to: '/locataire/payer', icon: Wallet, label: 'Payer mon loyer' },
  { to: '/locataire/paiements', icon: CreditCard, label: 'Ma comptabilité' },
  { to: '/locataire/demarches', icon: MessagesSquare, label: 'Mes démarches' },
  { to: '/locataire/signaler', icon: ConciergeBell, label: 'Allô gardien !' },
  { to: '/locataire/documents', icon: Archive, label: 'Mes documents' },
  { to: '/locataire/offres', icon: ShoppingBag, label: 'Offres & Services' },
]

/** Menu du rôle (par défaut : gestionnaire mandataire / admin). */
export function navForRole(role?: string): NavItem[] {
  // Comptable = menu gestionnaire complet (lecture) ; écritures bloquées serveur.
  if (role === 'gestionnaire_proprio') return navGestionnairePropio
  if (role === 'proprietaire') return navProprietaire
  if (role === 'locataire') return navLocataire
  return navGestionnaire
}

/**
 * Descriptions par route (formulation adaptée au contexte du rôle) pour les
 * rubriques dont la route n'est pas couverte par le catalogue FEATURE_DESCRIPTIONS,
 * ou pour lesquelles on veut une formulation propre à l'espace concerné.
 */
export const ROUTE_DESCRIPTIONS: Record<string, string> = {
  // Gestionnaire / admin
  '/comptabilite': "Grand livre de toutes les transactions (appels de loyer, règlements, apurement, régularisations de charges), avec le logement concerné (et le propriétaire pour le mandataire).",
  '/comptabilite/mandant': "Compte rendu de gestion par propriétaire : loyers encaissés, honoraires retenus (taux configurable + TVA), reversements effectués et solde restant à reverser. Périodicité au choix (mensuel, trimestriel, semestriel, annuel) et export CRG en PDF.",
  '/owners': 'Les fiches des bailleurs : identité, RIB unique et biens rattachés.',
  '/scoring': 'Qualité de payeur de chaque locataire (note A–E) à partir des revenus, de l\'historique de paiement et de la relation, avec stratégie recommandée.',
  '/diffusion': 'Créez et personnalisez vos annonces (photos, description, critères), diffusez-les sur vos plateformes et suivez leurs performances (vues).',
  '/candidatures': 'Dossiers candidats centralisés : vérification des pièces, analyse et comparaison des profils, sélection du locataire le plus adapté.',
  '/sorties': "Sortie du locataire : préavis, état des lieux de sortie comparé à l'entrée, décompte du dépôt de garantie et clôture du dossier.",
  '/abonnement': 'Vos factures (PDF), votre formule et la gestion de votre abonnement.',
  // Espace propriétaire
  '/proprietaire/annonces': "Le statut de mise en location de vos biens (publiée, programmée, brouillon) et leurs performances (vues), en lecture seule.",
  '/proprietaire': "Vue d'ensemble : revenus, taux d'occupation et points d'attention sur vos biens.",
  '/proprietaire/biens': "Le détail de chaque bien confié et son statut d'occupation.",
  '/proprietaire/revenus': 'Les loyers perçus, par période et par bien.',
  '/proprietaire/locataires': 'Les locataires en place dans vos biens.',
  '/proprietaire/incidents': 'Le suivi (lecture seule) des démarches de vos locataires : demandes, échanges, relances et clôtures.',
  '/proprietaire/entretiens': 'Les interventions réalisées ou planifiées sur vos biens.',
  '/proprietaire/messages': 'Vos échanges avec votre gestionnaire.',
  '/proprietaire/fiscal': 'Le récapitulatif annuel pour votre déclaration de revenus fonciers.',
  // Espace locataire
  '/locataire': 'Le tableau de bord de votre location : bail, prochain avis et dernier paiement.',
  '/locataire/avis-echeances': "Vos appels de loyer (selon la fréquence du bail), téléchargeables en PDF.",
  '/locataire/payer': 'Le montant dû et les modalités de règlement de votre loyer.',
  '/locataire/paiements': "Votre comptabilité : solde actuel (reste à payer cumulé) et grand livre des appels de loyer et de vos règlements ; téléchargement de vos quittances.",
  '/locataire/demarches': "Vos échanges avec votre gestionnaire au sujet de votre logement (demandes, questions, incidents) et l'envoi de votre préavis de départ.",
  '/locataire/signaler': "Allô gardien ! Un souci dans la résidence ou l'immeuble (parties communes, ascenseur, sécurité des accès, propreté, espaces extérieurs, nuisances de voisinage…) ? Décrivez-le avec photo et niveau d'urgence : votre gestionnaire est alerté immédiatement.",
  '/signalements': "Votre poste de gardien : tous les signalements remontés par vos locataires (bruit, sécurité, propreté…), avec suivi par statut, logements à problème, historique et export.",
  '/locataire/documents': 'Votre bail, vos quittances et tous les documents liés à votre location.',
  '/locataire/offres': 'Les services proposés (assurance, box internet, etc.).',
}

/** Description d'une rubrique : route explicite, sinon catalogue, sinon vide. */
export function descriptionForRoute(to?: string): string {
  if (!to) return ''
  if (ROUTE_DESCRIPTIONS[to]) return ROUTE_DESCRIPTIONS[to]
  const key = featureForPath(to)
  return (key && FEATURE_DESCRIPTIONS[key]) || ''
}

// ── Titre d'onglet par route (« Le Comptoir Immo | <libellé> ») ────────────────
// On réutilise les libellés du menu. L'ordre place les navs les plus spécifiques
// d'abord pour le repli `_ALL_NAV`. Quelques pages hors menu ont un libellé dédié.
const _ALL_NAV: NavItem[] = [
  ...navLocataire, ...navProprietaire, ...navGestionnairePropio, ...navGestionnaire,
]
const EXTRA_TITLES: Record<string, string> = {
  '/profil': 'Mon profil',
  '/abonnement': 'Mon abonnement',
  '/notifications': 'Notifications',
  '/guide': 'Guide utilisateur',
}

/**
 * Libellé d'onglet pour un chemin : correspondance exacte d'abord (priorité au
 * menu du rôle courant), sinon plus long préfixe (pages de détail comme
 * /properties/:id ou /locataire/payer/regler/…), sinon undefined.
 */
export function titleForPath(pathname: string, role?: string): string | undefined {
  const norm = pathname.replace(/\/+$/, '') || '/'
  if (EXTRA_TITLES[norm]) return EXTRA_TITLES[norm]
  const find = (items: NavItem[]): string | undefined => {
    const exact = items.find(i => i.to === norm)
    if (exact) return exact.label
    let best: string | undefined
    let len = -1
    for (const i of items) {
      if (i.to && norm.startsWith(i.to + '/') && i.to.length > len) { best = i.label; len = i.to.length }
    }
    return best
  }
  return (role ? find(navForRole(role)) : undefined) || find(_ALL_NAV)
}
