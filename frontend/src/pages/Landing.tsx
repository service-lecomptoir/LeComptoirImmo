import { useEffect, useState } from 'react'
import type { ElementType } from 'react'
import { BRAND } from '@/lib/brand'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Check, Building2, Users, Calendar, CreditCard,
  FileCheck, TrendingUp, Zap, PenSquare, Calculator, Infinity as InfinityIcon,
  Menu, X, Info, Megaphone, UserCheck, BarChart3, FileText, Send, MessagesSquare,
  Wrench, BookUser, ShoppingBag, Landmark, DoorOpen, Settings, Wallet, Bot, ListChecks,
  Clock, LayoutGrid, ShieldCheck, Boxes, Quote, Plus as PlusIcon, Minus, MapPin,
} from 'lucide-react'
import SubscriptionModal from '@/pages/SubscriptionModal'
import { publicPlansApi, type PublicPlan } from '@/api/publicPlans'
import { useCatalogStore, type CatalogItem } from '@/store/catalogStore'
import { LogoMark } from '@/components/common/Logo'

const NAVY = BRAND.navy
const ORANGE = BRAND.orange

// Icône d'illustration par fonctionnalité (la section « Fonctionnalités » est
// générée depuis le catalogue ; seule l'icône reste choisie ici).
const ICON_BY_FEATURE: Record<string, ElementType> = {
  diffusion: Megaphone, candidatures: UserCheck, dashboard: BarChart3, properties: Building2,
  tenants: Users, leases: FileText, avis_echeances: Calendar, payments: CreditCard,
  quittances: FileCheck, actualisation: TrendingUp, automatisation: Send, templates: PenSquare,
  incidents: MessagesSquare, entretiens: Wrench, contacts: BookUser, offres: ShoppingBag,
  documents_caf: Landmark, sortie_locataire: DoorOpen, admin: Settings, finances: Wallet,
  performance_biens: BarChart3, liasse_fiscale: Calculator, agents_ia: Bot,
}

const NAV = [
  { href: '#comment-ca-marche', label: 'Comment ça marche' },
  { href: '#fonctionnalites', label: 'Fonctionnalités' },
  { href: '#tarification', label: 'Tarification' },
  { href: '#faq', label: 'FAQ' },
]

// « Pourquoi Le Comptoir Immo » : atouts mis en avant.
const WHY = [
  {
    icon: Clock,
    title: 'Vous gagnez du temps',
    text: "Avis d'échéances, quittances, relances et révisions de loyer se génèrent et s'envoient automatiquement.",
  },
  {
    icon: LayoutGrid,
    title: 'Fini les tableurs',
    text: 'Biens, propriétaires, locataires, baux, documents et comptabilité réunis au même endroit.',
  },
  {
    icon: ShieldCheck,
    title: 'Conforme et sécurisé',
    text: 'Données hébergées en France, conformité RGPD et sauvegardes quotidiennes de vos informations.',
  },
  {
    icon: Boxes,
    title: 'Une seule plateforme',
    text: 'Gestion locative, comptabilité, syndic de copropriété et espace dédié à vos locataires.',
  },
]

// Témoignages illustratifs (exemples, pas de clients réels).
const TESTIMONIALS = [
  {
    initials: 'CD',
    name: 'Camille D.',
    role: 'Gérante d’agence, Lyon',
    quote: "Les quittances et les relances partent toutes seules. Je récupère plusieurs heures chaque mois.",
  },
  {
    initials: 'TR',
    name: 'Thomas R.',
    role: 'Propriétaire bailleur, Bordeaux',
    quote: "Je suis mes loyers et mes documents en temps réel, sans avoir à appeler qui que ce soit.",
  },
  {
    initials: 'NB',
    name: 'Nadia B.',
    role: 'Administratrice de biens, Lille',
    quote: "La comptabilité mandant et les comptes rendus de gestion me font gagner un temps précieux.",
  },
]

// FAQ : questions adaptées à Le Comptoir Immo.
const FAQ_ITEMS = [
  {
    q: 'Faut-il installer un logiciel ?',
    a: "Non. Le Comptoir Immo est 100 % en ligne : il suffit d’un navigateur, sans installation ni mise à jour à gérer.",
  },
  {
    q: 'Est-ce accessible sur mobile et tablette ?',
    a: "Oui. L’application s’adapte aux mobiles et tablettes, et vos locataires disposent de leur propre espace pour consulter quittances, paiements et signalements.",
  },
  {
    q: 'Où sont hébergées mes données ?',
    a: "Vos données sont hébergées en France, sur une infrastructure dédiée.",
  },
  {
    q: 'Êtes-vous conforme au RGPD ?',
    a: "Oui. Nous respectons le RGPD, les accès sont protégés et les informations sensibles sont chiffrées.",
  },
  {
    q: 'Mes données sont-elles sauvegardées ?',
    a: "Oui. Vos données font l’objet de sauvegardes quotidiennes, avec des tests de restauration réguliers.",
  },
  {
    q: 'Puis-je gérer plusieurs biens et plusieurs propriétaires ?',
    a: "Oui. La plateforme est pensée pour un portefeuille : patrimoine personnel, SCI, copropriétés et gestion pour le compte de tiers (mandataire).",
  },
  {
    q: 'Mes locataires ont-ils un accès ?',
    a: "Oui. Chaque locataire dispose d’un espace pour suivre ses loyers, télécharger ses quittances, payer en ligne et signaler un incident.",
  },
  {
    q: 'Puis-je inviter mon comptable ou un collaborateur ?',
    a: "Oui. Vous pouvez créer des comptes utilisateurs avec des accès adaptés, par exemple un rôle Comptable en lecture et encaissement.",
  },
  {
    q: 'Puis-je exporter mes données ?',
    a: "Oui. Vos documents et la plupart de vos listes sont téléchargeables en PDF à tout moment.",
  },
  {
    q: 'Y a-t-il un engagement ?',
    a: "Non, nos formules sont sans engagement et résiliables à tout moment.",
  },
  {
    q: 'Comment démarrer ?',
    a: "Demandez une démo : notre équipe vous recontacte rapidement et la mise en place se fait en quelques minutes.",
  },
]

const STEPS = [
  { n: 1, title: 'Créez votre espace', text: "Votre agence ou votre patrimoine est prêt en quelques minutes, sans aucun logiciel à installer." },
  { n: 2, title: 'Ajoutez biens, locataires et contrats', text: "Réunissez propriétaires, locataires, baux et documents au même endroit, en toute simplicité." },
  { n: 3, title: 'Automatisez la gestion locative', text: "Avis d'échéances, quittances, relances et révisions de loyer se génèrent et s'envoient tout seuls." },
]

function Header({ onDemo }: { onDemo: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-gray-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <a href="#top" onClick={() => setOpen(false)} className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: ORANGE }}>
            <LogoMark size={20} className="text-white" />
          </div>
          <span className="font-semibold text-[15px]" style={{ color: NAVY }}>Le Comptoir Immo</span>
        </a>

        <nav className="hidden md:flex items-center gap-7">
          {NAV.map(n => (
            <a key={n.href} href={n.href} className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              {n.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={onDemo}
            className="text-sm font-medium px-3.5 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Demander une démo
          </button>
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-lg text-white transition-opacity hover:opacity-90"
            style={{ background: NAVY }}
          >
            Vers le site <ArrowRight size={15} />
          </Link>
        </div>

        {/* Bouton hamburger (mobile) */}
        <button
          onClick={() => setOpen(o => !o)}
          className="md:hidden p-2 -mr-2 rounded-lg text-gray-700 hover:bg-gray-100"
          aria-label="Menu"
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Panneau de navigation mobile */}
      {open && (
        <div className="md:hidden border-t border-gray-100 bg-white">
          <nav className="px-4 py-3 flex flex-col gap-1">
            {NAV.map(n => (
              <a
                key={n.href}
                href={n.href}
                onClick={() => setOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
              >
                {n.label}
              </a>
            ))}
            <button
              onClick={() => { setOpen(false); onDemo() }}
              className="text-left px-3 py-2.5 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
            >
              Demander une démo
            </button>
            <Link
              to="/login"
              onClick={() => setOpen(false)}
              className="mt-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-sm font-semibold text-white"
              style={{ background: NAVY }}
            >
              Vers le site <ArrowRight size={15} />
            </Link>
          </nav>
        </div>
      )}
    </header>
  )
}

function HeroPreview() {
  const kpis = [
    { label: 'Loyers perçus', value: '24 800 €' },
    { label: "Taux d'occupation", value: '96 %' },
    { label: 'Quittances émises', value: '38' },
  ]
  const bars = [40, 65, 50, 80, 60, 90, 75]
  return (
    <div className="relative">
      <div className="rounded-2xl bg-white shadow-2xl overflow-hidden ring-1 ring-black/5">
        <div className="flex items-center gap-1.5 px-4 py-3 border-b border-gray-100 bg-gray-50">
          <span className="w-2.5 h-2.5 rounded-full bg-red-300" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
          <span className="w-2.5 h-2.5 rounded-full bg-green-300" />
          <span className="ml-3 text-[11px] text-gray-400">Tableau de bord : Le Comptoir Immo</span>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-3 gap-3">
            {kpis.map(k => (
              <div key={k.label} className="rounded-xl border border-gray-100 p-3">
                <p className="text-[10px] text-gray-400 leading-tight">{k.label}</p>
                <p className="text-sm font-bold mt-0.5" style={{ color: NAVY }}>{k.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-gray-100 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] font-semibold text-gray-500">Revenus mensuels</p>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: `${ORANGE}1A`, color: ORANGE }}>+12 %</span>
            </div>
            <div className="flex items-end gap-2 h-24">
              {bars.map((h, i) => (
                <div key={i} className="flex-1 rounded-t-md" style={{ height: `${h}%`, background: i === bars.length - 1 ? ORANGE : '#C7D2E4' }} />
              ))}
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {['Quittance : Appartement Rivoli', "Avis d'échéance : Studio Bastille"].map((t, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2">
                <span className="text-[11px] text-gray-600 truncate">{t}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-600 shrink-0">Payé</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="absolute -bottom-4 -left-4 bg-white rounded-xl shadow-xl px-3 py-2 ring-1 ring-black/5 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${ORANGE}1A`, color: ORANGE }}>
          <Zap size={14} />
        </div>
        <div>
          <p className="text-[10px] text-gray-400 leading-none">Automatisé</p>
          <p className="text-[11px] font-semibold text-gray-700 leading-tight">Quittances envoyées</p>
        </div>
      </div>
    </div>
  )
}

function Hero({ onDemo }: { onDemo: () => void }) {
  return (
    <section id="top" className="relative overflow-hidden" style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #1A4A8A 100%)` }}>
      {/* halos décoratifs */}
      <div className="pointer-events-none absolute -top-24 -right-24 w-96 h-96 rounded-full opacity-20 blur-3xl" style={{ background: ORANGE }} />
      <div className="pointer-events-none absolute -bottom-32 -left-24 w-96 h-96 rounded-full opacity-10 blur-3xl bg-white" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24 grid lg:grid-cols-2 gap-12 items-center">
        <div className="text-center lg:text-left">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium text-white/90 bg-white/10 mb-6">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: ORANGE }} /> Logiciel de gestion locative
          </span>
          <h1 className="text-3xl sm:text-5xl font-bold text-white leading-[1.1]">
            Toute votre gestion locative<br className="hidden sm:block" /> dans un seul outil
          </h1>
          <p className="mt-5 text-base sm:text-lg text-blue-100 max-w-xl mx-auto lg:mx-0">
            Avis d'échéances, quittances, relances, révision des loyers (IRL) et liasse fiscale —
            automatisés. Pour les gestionnaires comme pour les propriétaires.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center lg:justify-start justify-center gap-3">
            <button
              onClick={onDemo}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-lg hover:opacity-90 transition-opacity"
              style={{ background: ORANGE }}
            >
              Demander une démo
            </button>
            <Link
              to="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-white/10 hover:bg-white/20 transition-colors"
            >
              Vers le site <ArrowRight size={16} />
            </Link>
          </div>
          <div className="mt-7 flex flex-wrap items-center justify-center lg:justify-start gap-x-5 gap-y-2 text-xs text-blue-100/90">
            {['Sans installation', 'Sans engagement', 'Mise en place rapide'].map(t => (
              <span key={t} className="inline-flex items-center gap-1.5"><Check size={14} style={{ color: ORANGE }} /> {t}</span>
            ))}
          </div>
        </div>

        <div className="hidden lg:block">
          <HeroPreview />
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section id="comment-ca-marche" className="py-20 sm:py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Comment ça marche</h2>
          <p className="mt-3 text-gray-500">Trois étapes pour passer d'une gestion dispersée à un pilotage automatisé.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {STEPS.map(s => (
            <div key={s.n} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold mb-4" style={{ background: NAVY }}>
                {s.n}
              </div>
              <h3 className="font-semibold text-gray-900 mb-1.5">{s.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{s.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FeatureCard({ item }: { item: CatalogItem }) {
  const Icon = ICON_BY_FEATURE[item.key] ?? ListChecks
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
      <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4" style={{ background: `${ORANGE}1A`, color: ORANGE }}>
        <Icon size={20} />
      </div>
      <h3 className="font-semibold text-gray-900 mb-1.5">{item.label}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{item.description}</p>
    </div>
  )
}

function Features() {
  // Section entièrement générée depuis le catalogue (regroupée par catégorie).
  const items = useCatalogStore(s => s.items)
  const groups: { category: string; items: CatalogItem[] }[] = []
  for (const it of items) {
    let g = groups.find(x => x.category === it.category)
    if (!g) { g = { category: it.category, items: [] }; groups.push(g) }
    g.items.push(it)
  }
  const showHeaders = groups.length > 1 || (groups[0]?.category ?? '') !== ''

  return (
    <section id="fonctionnalites" className="py-20 sm:py-24 bg-gray-50 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Fonctionnalités</h2>
          <p className="mt-3 text-gray-500">Tout ce qu'il faut pour gérer la location de A à Z, sans tableur.</p>
        </div>
        <div className="space-y-12">
          {groups.map(g => (
            <div key={g.category || 'all'}>
              {showHeaders && g.category && (
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-5">{g.category}</h3>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {g.items.map(it => <FeatureCard key={it.key} item={it} />)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FeatureRow({ featureKey, included }: { featureKey: string; included: boolean }) {
  const labels = useCatalogStore(s => s.labels)
  const descriptions = useCatalogStore(s => s.descriptions)
  const desc = descriptions[featureKey]
  return (
    <li className={`flex items-start gap-2 text-sm ${included ? 'text-gray-600' : 'text-gray-400'}`}>
      {included ? (
        <Check size={16} className="mt-0.5 shrink-0" style={{ color: ORANGE }} />
      ) : (
        <X size={16} className="mt-0.5 shrink-0 text-gray-300" />
      )}
      <span className={`inline-flex items-center gap-1.5 ${included ? '' : 'line-through'}`}>
        {labels[featureKey] ?? featureKey}
        {desc && (
          <span className="group relative inline-flex items-center">
            <Info size={13} className="text-gray-300 hover:text-gray-500 cursor-help" aria-label={desc} />
            <span
              role="tooltip"
              className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-52 rounded-lg bg-gray-900 text-white text-[11px] leading-snug px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity z-20 shadow-lg"
            >
              {desc}
              <span className="absolute left-1/2 -translate-x-1/2 top-full border-4 border-transparent border-t-gray-900" />
            </span>
          </span>
        )}
      </span>
    </li>
  )
}

function PlanCard({ plan, onDemo, highlight }: { plan: PublicPlan; onDemo: (planId?: string) => void; highlight: boolean }) {
  const orderedKeys = useCatalogStore(s => s.orderedKeys)
  const audienceByKey = useCatalogStore(s => s.audienceByKey)
  const isMandataire = plan.manager_type === 'mandataire'
  const type = plan.manager_type || 'proprietaire'
  // Périmètre du plan = fonctionnalités communes + celles de son type.
  const scope = orderedKeys.filter(k => {
    const a = audienceByKey[k] || 'all'
    return a === 'all' || a === type
  })
  // Incluse si la liste du plan est « toutes » (null) ou contient la clé.
  const isIncluded = (k: string) => plan.features === null || plan.features.includes(k)
  return (
    <div
      className={`relative bg-white rounded-2xl border p-6 flex flex-col ${highlight ? 'shadow-xl' : 'border-gray-100 shadow-sm'}`}
      style={highlight ? { borderColor: ORANGE } : undefined}
    >
      {highlight && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[11px] font-semibold text-white" style={{ background: ORANGE }}>
          Le plus choisi
        </span>
      )}
      <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
      {plan.description && <p className="mt-1 text-sm text-gray-500 min-h-[40px]">{plan.description}</p>}
      {isMandataire ? (
        <div className="mt-4">
          <span className="text-2xl font-extrabold" style={{ color: NAVY }}>Sur devis</span>
          <p className="text-sm text-gray-400">Tarif sur mesure</p>
        </div>
      ) : (
        <div className="mt-4 flex items-end gap-1">
          <span className="text-3xl font-extrabold" style={{ color: NAVY }}>{plan.monthly_price.toFixed(0)} €</span>
          <span className="text-sm text-gray-400 mb-1">/ mois</span>
        </div>
      )}
      <div className="mt-3 flex items-center gap-1.5 text-sm font-medium text-gray-700">
        {plan.property_limit === null ? (
          <><InfinityIcon size={15} style={{ color: ORANGE }} /> Biens illimités</>
        ) : (
          <>Jusqu'à {plan.property_limit} bien{plan.property_limit > 1 ? 's' : ''}</>
        )}
      </div>

      <div className="mt-5 pt-5 border-t border-gray-100 flex-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Fonctionnalités</p>
        <ul className="space-y-2">
          {scope.map(k => (
            <FeatureRow key={k} featureKey={k} included={isIncluded(k)} />
          ))}
        </ul>
      </div>

      <button
        onClick={() => onDemo(plan.id)}
        className="mt-6 w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90"
        style={{ background: highlight ? ORANGE : NAVY }}
      >
        Demander une démo
      </button>
    </div>
  )
}

function Pricing({ onDemo }: { onDemo: (planId?: string) => void }) {
  const [plans, setPlans] = useState<PublicPlan[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    publicPlansApi.list()
      .then(r => setPlans(r.data))
      .catch(() => setError(true))
  }, [])

  // On affiche la tarification des gestionnaires PROPRIÉTAIRES ; les offres
  // mandataire sont « sur devis » (sans prix).
  const proprio = (plans ?? []).filter(p => p.manager_type !== 'mandataire')
  const mandataire = (plans ?? []).filter(p => p.manager_type === 'mandataire')

  return (
    <section id="tarification" className="py-20 sm:py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Tarification</h2>
          <p className="mt-3 text-gray-500">Des formules claires selon votre volume de biens. Sans engagement.</p>
        </div>

        {error || (plans && plans.length === 0) ? (
          <div className="text-center text-gray-500">
            <p>Nos formules vous seront présentées sur demande.</p>
            <button onClick={() => onDemo()} className="mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold text-white" style={{ background: NAVY }}>
              Demander une démo
            </button>
          </div>
        ) : !plans ? (
          <div className="flex justify-center py-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: NAVY }} />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
              {proprio.map((p, i) => (
                <PlanCard key={p.id} plan={p} onDemo={onDemo} highlight={proprio.length > 1 && i === Math.floor((proprio.length - 1) / 2)} />
              ))}
            </div>

            {mandataire.length > 0 && (
              <div className="mt-16">
                <div className="text-center max-w-2xl mx-auto mb-10">
                  <h3 className="text-xl sm:text-2xl font-bold" style={{ color: NAVY }}>Gestion mandataire</h3>
                  <p className="mt-2 text-gray-500">Pour la gestion pour le compte de tiers : tarif sur mesure, sur demande.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
                  {mandataire.map(p => (
                    <PlanCard key={p.id} plan={p} onDemo={onDemo} highlight={false} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}

function WhyUs() {
  return (
    <section id="pourquoi" className="py-20 sm:py-24 bg-gray-50 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Pourquoi Le Comptoir Immo</h2>
          <p className="mt-3 text-gray-500">Un outil pensé pour les gestionnaires comme pour les propriétaires.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {WHY.map(w => {
            const Icon = w.icon
            return (
              <div key={w.title} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4" style={{ background: `${NAVY}14`, color: NAVY }}>
                  <Icon size={20} />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1.5">{w.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{w.text}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function Testimonials() {
  return (
    <section id="temoignages" className="py-20 sm:py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Ils gèrent plus sereinement</h2>
          <p className="mt-3 text-gray-500">Exemples illustratifs de ce que permet la plateforme au quotidien.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TESTIMONIALS.map(t => (
            <figure key={t.initials} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 flex flex-col">
              <Quote size={22} className="mb-3" style={{ color: ORANGE }} />
              <blockquote className="text-sm text-gray-600 leading-relaxed flex-1">« {t.quote} »</blockquote>
              <figcaption className="mt-5 flex items-center gap-3">
                <span
                  className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold text-white shrink-0"
                  style={{ background: NAVY }}
                  aria-hidden="true"
                >
                  {t.initials}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-gray-900">{t.name}</span>
                  <span className="block text-xs text-gray-400">{t.role}</span>
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
        <p className="mt-8 text-center text-xs text-gray-400">
          Témoignages illustratifs, à titre d'exemple.
        </p>
      </div>
    </section>
  )
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-100 rounded-xl bg-white overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-gray-900">{q}</span>
        <span className="shrink-0 text-gray-400">
          {open ? <Minus size={18} /> : <PlusIcon size={18} />}
        </span>
      </button>
      {open && (
        <p className="px-5 pb-4 -mt-1 text-sm text-gray-500 leading-relaxed">{a}</p>
      )}
    </div>
  )
}

function Faq({ onDemo }: { onDemo: () => void }) {
  return (
    <section id="faq" className="py-20 sm:py-24 bg-gray-50 scroll-mt-16">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Questions fréquentes</h2>
          <p className="mt-3 text-gray-500">Tout ce qu'il faut savoir avant de démarrer.</p>
        </div>
        <div className="space-y-3">
          {FAQ_ITEMS.map(it => <FaqItem key={it.q} q={it.q} a={it.a} />)}
        </div>
        <div className="mt-10 text-center">
          <p className="text-sm text-gray-500 inline-flex items-center gap-1.5">
            <MapPin size={15} style={{ color: ORANGE }} /> Une autre question ?
          </p>
          <div className="mt-3">
            <button
              onClick={onDemo}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: NAVY }}
            >
              Demander une démo
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-gray-100 py-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: ORANGE }}>
            <LogoMark size={17} className="text-white" />
          </div>
          <span className="font-semibold text-sm" style={{ color: NAVY }}>Le Comptoir Immo</span>
        </div>
        <div className="text-xs text-gray-400 text-center">
          <p>© {new Date().getFullYear()} Le Comptoir Immo : Gestion locative</p>
          <p className="mt-1">
            <Link to="/mentions-legales" className="hover:text-gray-600">Mentions légales</Link>
            {' · '}
            <Link to="/confidentialite" className="hover:text-gray-600">Confidentialité</Link>
          </p>
        </div>
        <Link to="/login" className="text-sm font-medium inline-flex items-center gap-1.5" style={{ color: NAVY }}>
          Vers le site <ArrowRight size={14} />
        </Link>
      </div>
    </footer>
  )
}

export default function Landing() {
  const [demoOpen, setDemoOpen] = useState(false)
  const [demoPlanId, setDemoPlanId] = useState<string | undefined>(undefined)
  const loadCatalog = useCatalogStore(s => s.loadCatalog)
  useEffect(() => { loadCatalog() }, [loadCatalog])
  const onDemo = (planId?: string) => { setDemoPlanId(planId); setDemoOpen(true) }
  return (
    <div className="min-h-screen bg-white">
      <Header onDemo={onDemo} />
      <main>
        <Hero onDemo={onDemo} />
        <HowItWorks />
        <WhyUs />
        <Features />
        <Testimonials />
        <Pricing onDemo={onDemo} />
        <Faq onDemo={() => onDemo()} />
      </main>
      <Footer />
      <SubscriptionModal open={demoOpen} onClose={() => setDemoOpen(false)} initialPlanId={demoPlanId} />
    </div>
  )
}
