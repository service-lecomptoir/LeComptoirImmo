import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Check, Building2, Users, Calendar, CreditCard,
  FileCheck, TrendingUp, Zap, PenSquare, MessageSquare, Calculator, Infinity as InfinityIcon,
} from 'lucide-react'
import SubscriptionModal from '@/pages/SubscriptionModal'
import { publicPlansApi, type PublicPlan } from '@/api/publicPlans'
import { FEATURE_LABELS } from '@/lib/features'

const NAVY = '#0D2F5C'
const ORANGE = '#F07800'
const FEATURE_ORDER = Object.keys(FEATURE_LABELS)

const NAV = [
  { href: '#comment-ca-marche', label: 'Comment ça marche' },
  { href: '#fonctionnalites', label: 'Fonctionnalités' },
  { href: '#tarification', label: 'Tarification' },
]

const STEPS = [
  { n: 1, title: 'Créez votre espace', text: "Votre agence ou votre patrimoine est prêt en quelques minutes — aucun logiciel à installer." },
  { n: 2, title: 'Ajoutez biens, locataires et contrats', text: "Centralisez propriétaires, locataires, baux et documents au même endroit." },
  { n: 3, title: 'Automatisez la gestion locative', text: "Avis d'échéances, quittances, relances et révisions de loyer générés automatiquement." },
]

const FEATURES = [
  { icon: Building2, title: 'Biens & propriétaires', text: 'Gérez tout votre patrimoine et vos propriétaires avec leurs coordonnées et RIB.' },
  { icon: Users, title: 'Locataires & contrats', text: 'Fiches locataires, baux, co-titulaires et suivi de l’occupation.' },
  { icon: Calendar, title: "Avis d'échéances", text: 'Génération automatique des avis selon la fréquence et la règle d’appel.' },
  { icon: CreditCard, title: 'Paiements', text: 'Encaissements, déclarations, relances et soldes en temps réel.' },
  { icon: FileCheck, title: 'Quittances de loyer', text: 'Quittances PDF à votre charte, prêtes à envoyer au locataire.' },
  { icon: TrendingUp, title: 'Actualisation IRL & charges', text: 'Révision annuelle des loyers (IRL) et régularisation des charges.' },
  { icon: Zap, title: 'Automatisation', text: 'Tâches récurrentes automatisées pour gagner un temps précieux.' },
  { icon: PenSquare, title: 'Ma papeterie', text: 'Vos modèles de documents personnalisés (logo, en-tête, mentions).' },
  { icon: MessageSquare, title: 'Messages & incidents', text: 'Échangez avec vos locataires et suivez les incidents et entretiens.' },
  { icon: Calculator, title: 'Finances & liasse fiscale', text: 'Performance par bien, revenus et liasse fiscale en un clic.' },
]

function Header({ onDemo }: { onDemo: () => void }) {
  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-gray-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <a href="#top" className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: ORANGE }}>
            <span className="text-white font-bold text-xs">LC</span>
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

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={onDemo}
            className="hidden sm:inline-flex text-sm font-medium px-3.5 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
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
      </div>
    </header>
  )
}

function Hero({ onDemo }: { onDemo: () => void }) {
  return (
    <section id="top" className="relative overflow-hidden" style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #1A4A8A 100%)` }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20 sm:py-28 text-center">
        <span className="inline-block px-3 py-1 rounded-full text-xs font-medium text-white/90 bg-white/10 mb-6">
          La gestion locative, simplifiée
        </span>
        <h1 className="text-3xl sm:text-5xl font-bold text-white leading-tight max-w-3xl mx-auto">
          Gérez vos biens, locataires et loyers depuis un seul espace
        </h1>
        <p className="mt-5 text-base sm:text-lg text-blue-100 max-w-2xl mx-auto">
          Le Comptoir Immo automatise vos avis d'échéances, quittances, relances et révisions de loyer —
          pour les gestionnaires et les propriétaires.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={onDemo}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-lg hover:opacity-90 transition-opacity"
            style={{ background: ORANGE }}
          >
            Demander une démo
          </button>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-white/10 hover:bg-white/20 transition-colors"
          >
            Vers le site <ArrowRight size={16} />
          </Link>
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

function Features() {
  return (
    <section id="fonctionnalites" className="py-20 sm:py-24 bg-gray-50 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl sm:text-3xl font-bold" style={{ color: NAVY }}>Fonctionnalités</h2>
          <p className="mt-3 text-gray-500">Tout ce qu'il faut pour gérer la location de A à Z, sans tableur.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(f => {
            const Icon = f.icon
            return (
              <div key={f.title} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4" style={{ background: `${ORANGE}1A`, color: ORANGE }}>
                  <Icon size={20} />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1.5">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.text}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function PlanCard({ plan, onDemo, highlight }: { plan: PublicPlan; onDemo: () => void; highlight: boolean }) {
  const allFeatures = plan.features === null
  const included = allFeatures ? FEATURE_ORDER : FEATURE_ORDER.filter(k => plan.features!.includes(k))
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
        <ul className="space-y-2">
          {included.map(k => (
            <li key={k} className="flex items-start gap-2 text-sm text-gray-600">
              <Check size={16} className="mt-0.5 shrink-0" style={{ color: ORANGE }} />
              {FEATURE_LABELS[k]}
            </li>
          ))}
        </ul>
      </div>

      <button
        onClick={onDemo}
        className="mt-6 w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90"
        style={{ background: highlight ? ORANGE : NAVY }}
      >
        Demander une démo
      </button>
    </div>
  )
}

function Pricing({ onDemo }: { onDemo: () => void }) {
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
            <button onClick={onDemo} className="mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold text-white" style={{ background: NAVY }}>
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
            <span className="text-white font-bold text-[10px]">LC</span>
          </div>
          <span className="font-semibold text-sm" style={{ color: NAVY }}>Le Comptoir Immo</span>
        </div>
        <p className="text-xs text-gray-400">© {new Date().getFullYear()} Le Comptoir Immo — Gestion locative</p>
        <Link to="/login" className="text-sm font-medium inline-flex items-center gap-1.5" style={{ color: NAVY }}>
          Vers le site <ArrowRight size={14} />
        </Link>
      </div>
    </footer>
  )
}

export default function Landing() {
  const [demoOpen, setDemoOpen] = useState(false)
  const onDemo = () => setDemoOpen(true)
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
      <SubscriptionModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </div>
  )
}
