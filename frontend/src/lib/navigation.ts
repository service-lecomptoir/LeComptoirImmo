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
  Home, Receipt, BookUser, Zap, PenSquare, BarChart3,
  Calculator, MessageSquare, Wrench, Wallet, FileCheck,
  ShoppingBag, Package, KeyRound, TrendingUp, Landmark, ShieldCheck,
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
  { label: 'Gestion locative', isSeparator: true },
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/owners', icon: KeyRound, label: 'Propriétaires (bailleurs)' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/scoring', icon: ShieldCheck, label: 'Scoring locataires' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/actualisation', icon: TrendingUp, label: 'Révision des loyers et charges' },
  { to: '/automatisation', icon: Zap, label: "Règles d'automatisation" },
  { to: '/templates', icon: PenSquare, label: 'Ma papeterie' },
  { to: '/incidents', icon: MessageSquare, label: 'Démarche' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/documents-caf', icon: Landmark, label: 'Documents CAF' },
  { to: '/admin', icon: Settings, label: 'Gestion des utilisateurs' },
  { label: 'Finances', isSeparator: true },
  { to: '/finances/revenus', icon: Wallet, label: 'Revenus' },
  { to: '/finances/biens', icon: BarChart3, label: 'Performance biens' },
  { to: '/finances/fiscal', icon: Calculator, label: 'Liasse fiscale' },
  { label: 'Mon compte', isSeparator: true },
  { to: '/abonnement', icon: Package, label: 'Mon abonnement' },
]

// Navigation Propriétaire
export const navProprietaire: NavItem[] = [
  { to: '/proprietaire', icon: LayoutDashboard, label: 'Mon tableau de bord' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Mes biens' },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/locataires', icon: Users, label: 'Mes locataires' },
  { to: '/proprietaire/incidents', icon: MessageSquare, label: 'Démarche' },
  { to: '/proprietaire/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/proprietaire/messages', icon: MessageSquare, label: 'Messages' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
]

// Navigation Gestionnaire-Propriétaire : identique au mandataire SANS « Vue propriétaire »
export const navGestionnairePropio: NavItem[] = [
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
  { to: '/automatisation', icon: Zap, label: "Règles d'automatisation" },
  { to: '/templates', icon: PenSquare, label: 'Ma papeterie' },
  { to: '/incidents', icon: MessageSquare, label: 'Démarche' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/documents-caf', icon: Landmark, label: 'Documents CAF' },
  { to: '/admin', icon: Settings, label: 'Gestion des utilisateurs' },
  { label: 'Mes finances', isSeparator: true },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Performance biens' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
  { label: 'Mon compte', isSeparator: true },
  { to: '/abonnement', icon: Package, label: 'Mon abonnement' },
]

// Navigation Locataire
export const navLocataire: NavItem[] = [
  { to: '/locataire', icon: Home, label: 'Mon espace' },
  { to: '/locataire/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/locataire/payer', icon: Wallet, label: 'Payer mon loyer' },
  { to: '/locataire/paiements', icon: CreditCard, label: 'Mes paiements' },
  { to: '/locataire/messages', icon: MessageSquare, label: 'Mes démarches' },
  { to: '/locataire/documents', icon: Receipt, label: 'Mes documents' },
  { to: '/locataire/offres', icon: ShoppingBag, label: 'Offres & Services' },
]

/** Menu du rôle (par défaut : gestionnaire mandataire / admin). */
export function navForRole(role?: string): NavItem[] {
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
  '/owners': 'Les fiches des bailleurs : identité, RIB unique et biens rattachés.',
  '/scoring': 'Qualité de payeur de chaque locataire (note A–E) à partir des revenus, de l\'historique de paiement et de la relation, avec stratégie recommandée.',
  '/abonnement': 'Vos factures (PDF), votre formule et la gestion de votre abonnement.',
  // Espace propriétaire
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
  '/locataire/paiements': "L'historique de vos règlements et le téléchargement de vos quittances.",
  '/locataire/messages': 'Faites une demande à tout moment et suivez son évolution : échanges, relance, validation ou refus de la clôture proposée.',
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
