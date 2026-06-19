import { useEffect, useState } from 'react'
import type { ElementType } from 'react'
import { BRAND } from '@/lib/brand'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Check, Building2, Users, Calendar, CreditCard,
  FileCheck, TrendingUp, Zap, PenSquare, Calculator, Infinity as InfinityIcon,
  Menu, X, Info, Megaphone, UserCheck, BarChart3, FileText, Send, MessagesSquare,
  Wrench, BookUser, ShoppingBag, Landmark, DoorOpen, Settings, Wallet, Bot, ListChecks,
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

function FeatureItem({ featureKey }: { featureKey: string }) {
  const labels = useCatalogStore(s => s.labels)
  const descriptions = useCatalogStore(s => s.descriptions)
  const desc = descriptions[featureKey]
  return (
    <li className="flex items-start gap-2 text-sm text-gray-600">
      <Check size={16} className="mt-0.5 shrink-0" style={{ color: ORANGE }} />
      <span className="inline-flex items-center gap-1.5">
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
  const included = plan.features === null ? orderedKeys : orderedKeys.filter(k => plan.features!.includes(k))
  // « Toutes » dès que l'intégralité des modules est incluse (null OU tout coché).
  const allFeatures = included.length === orderedKeys.length
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
      <div className="mt-4 flex items-end gap-1">
        <span className="text-3xl font-extrabold" style={{ color: NAVY }}>{plan.monthly_price.toFixed(0)} €</span>
        <span className="text-sm text-gray-400 mb-1">/ mois</span>
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-sm font-medium text-gray-700">
        {plan.property_limit === null ? (
          <><InfinityIcon size={15} style={{ color: ORANGE }} /> Biens illimités</>
        ) : (
          <>Jusqu'à {plan.property_limit} bien{plan.property_limit > 1 ? 's' : ''}</>
        )}
      </div>

      <div className="mt-5 pt-5 border-t border-gray-100 flex-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
          {allFeatures ? 'Toutes les fonctionnalités' : 'Fonctionnalités incluses'}
        </p>
        {allFeatures ? (
          <p className="flex items-start gap-2 text-sm text-gray-600">
            <Check size={16} className="mt-0.5 shrink-0" style={{ color: ORANGE }} />
            Accès à l'ensemble des modules de la plateforme.
          </p>
        ) : (
          <ul className="space-y-2">
            {included.map(k => (
              <FeatureItem key={k} featureKey={k} />
            ))}
          </ul>
        )}
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
            {plans.map((p, i) => (
              <PlanCard key={p.id} plan={p} onDemo={onDemo} highlight={plans.length > 1 && i === Math.floor((plans.length - 1) / 2)} />
            ))}
          </div>
        )}
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
        <p className="text-xs text-gray-400">© {new Date().getFullYear()} Le Comptoir Immo : Gestion locative</p>
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
        <Features />
        <Pricing onDemo={onDemo} />
      </main>
      <Footer />
      <SubscriptionModal open={demoOpen} onClose={() => setDemoOpen(false)} initialPlanId={demoPlanId} />
    </div>
  )
}
