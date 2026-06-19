import { useCallback, useEffect, useMemo } from 'react'
import type { ElementType } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { useCatalogStore } from '@/store/catalogStore'
import { featureForPath, isFeatureAllowed } from '@/lib/features'
import { BookOpen, Lightbulb, ListChecks } from 'lucide-react'
import { navForRole, descriptionForRoute } from '@/lib/navigation'

// ─── Guide ENTIÈREMENT généré ─────────────────────────────────────────────────
// Aucune prose écrite à la main par fonctionnalité : tout (libellés, descriptions,
// regroupement par section, filtrage par formule) provient de la source de vérité
// unique — lib/navigation.ts (menu) + le catalogue de fonctionnalités exposé par
// l'API (/public/features) côté entitlements. Conséquence : toute fonctionnalité
// ajoutée, renommée, retirée ou (dés)activée par l'abonnement met le guide à jour
// AUTOMATIQUEMENT, sans intervention.

interface StepItem { to: string; label: string; icon: ElementType; desc: string }
interface StepGroup { section: string; items: StepItem[] }

function buildSteps(
  role: string | undefined,
  features: string[] | null,
  descFor: (to: string) => string,
): StepGroup[] {
  const groups: StepGroup[] = []
  let current: StepGroup | null = null
  for (const item of navForRole(role)) {
    if (item.isSeparator) {
      current = { section: item.label, items: [] }
      groups.push(current)
      continue
    }
    if (!item.to) continue
    if (!isFeatureAllowed(features, featureForPath(item.to))) continue
    if (!current) { current = { section: 'Premiers pas', items: [] }; groups.push(current) }
    current.items.push({
      to: item.to, label: item.label,
      icon: item.icon ?? ListChecks, desc: descFor(item.to),
    })
  }
  return groups.filter(g => g.items.length > 0)
}

function StepIllustration({ icon: Icon, n }: { icon: ElementType; n: number }) {
  return (
    <div className="relative w-full sm:w-44 h-28 rounded-xl overflow-hidden shrink-0
                    bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
      <div className="absolute -top-6 -right-6 w-20 h-20 rounded-full bg-white/10" />
      <div className="absolute -bottom-8 -left-4 w-24 h-24 rounded-full bg-white/10" />
      <Icon size={46} strokeWidth={1.5} className="text-white relative z-10" />
      <span className="absolute top-2 left-2 w-6 h-6 rounded-full bg-white text-blue-700
                       text-xs font-bold flex items-center justify-center z-10">{n}</span>
    </div>
  )
}

// En-tête (badge + titre + intro) par rôle. Générique et stable : ne décrit pas
// les fonctionnalités une par une (celles-ci sont listées dynamiquement plus bas).
interface Header { badge: string; title: string; intro: string }
const HEADERS: Record<string, Header> = {
  gestionnaire: {
    badge: 'Gestionnaire mandataire',
    title: 'Gérer les biens de vos propriétaires',
    intro: "Administrez les biens de vos propriétaires de bout en bout : mise en location, "
      + "contrats, loyers, communication et documents officiels. Voici vos rubriques, dans "
      + "l'ordre logique de mise en route — elles s'adaptent à votre formule.",
  },
  gestionnaire_proprio: {
    badge: 'Gestionnaire propriétaire',
    title: 'Gérer vos propres biens de A à Z',
    intro: "Vous êtes à la fois gestionnaire et propriétaire : tous les outils de gestion, "
      + "plus une vue financière (revenus, performance, liasse fiscale). Voici vos rubriques, "
      + "dans l'ordre de mise en route.",
  },
  proprietaire: {
    badge: 'Propriétaire',
    title: 'Suivre vos biens et vos revenus',
    intro: "Votre espace vous donne une vue claire sur vos biens confiés en gestion : revenus, "
      + "locataires, démarches et documents fiscaux. La gestion quotidienne est assurée par "
      + "votre mandataire ; vous suivez et consultez.",
  },
  locataire: {
    badge: 'Locataire',
    title: 'Votre logement et vos loyers, simplement',
    intro: "Votre espace réunit tout ce qui concerne votre location : bail, avis d'échéance, "
      + "paiement du loyer, quittances et échanges avec votre gestionnaire. Voici vos rubriques.",
  },
}
function headerForRole(role?: string): Header {
  if (role && HEADERS[role]) return HEADERS[role]
  return HEADERS.gestionnaire // admin + défaut
}

export default function GuideUtilisateur() {
  const { user } = useAuthStore()
  const h = headerForRole(user?.role)

  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio' || user?.role === 'admin'
  const { features, loadFeatures } = useFeaturesStore()
  useEffect(() => { if (isManager) loadFeatures() }, [isManager, loadFeatures])

  // Descriptions : priorité au catalogue dynamique pour les rubriques portant une
  // fonctionnalité ; repli sur la formulation par route (espaces proprio/locataire).
  const catalogDescriptions = useCatalogStore(s => s.descriptions)
  const loadCatalog = useCatalogStore(s => s.loadCatalog)
  useEffect(() => { loadCatalog() }, [loadCatalog])
  const descFor = useCallback((to: string) => {
    const key = featureForPath(to)
    return (key && catalogDescriptions[key]) || descriptionForRoute(to)
  }, [catalogDescriptions])

  const groups = useMemo(() => buildSteps(user?.role, features, descFor), [user?.role, features, descFor])
  const totalSteps = groups.reduce((n, gr) => n + gr.items.length, 0)

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      {/* En-tête */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-500 rounded-2xl p-6 sm:p-8 text-white mb-6">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen size={18} />
          <span className="text-xs font-semibold uppercase tracking-wider bg-white/20 px-2.5 py-1 rounded-full">
            Guide d'utilisation · {h.badge}
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold mb-2">{h.title}</h1>
        <p className="text-blue-50 text-sm sm:text-base leading-relaxed">{h.intro}</p>
      </div>

      {/* Rubriques (générées dynamiquement depuis le menu + formule) */}
      <section className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Vos rubriques, pas à pas</h2>
          <span className="text-xs text-gray-400">{totalSteps} rubrique{totalSteps > 1 ? 's' : ''}</span>
        </div>
        {(() => {
          let n = 0
          return groups.map(group => (
            <div key={group.section} className="mb-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2.5">{group.section}</h3>
              <div className="space-y-3">
                {group.items.map(it => {
                  n += 1
                  const Icon = it.icon
                  return (
                    <div key={it.to} className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col sm:flex-row gap-4">
                      <StepIllustration icon={Icon} n={n} />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900">{it.label}</p>
                        <p className="text-sm text-gray-600 mt-0.5 leading-relaxed">
                          {it.desc || "Accédez à cette rubrique depuis le menu pour en profiter."}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))
        })()}
      </section>

      {/* Note */}
      <section className="bg-amber-50 border border-amber-200 rounded-xl p-5 sm:p-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-amber-900 mb-2">
          <Lightbulb size={18} className="text-amber-600" /> Bon à savoir
        </h2>
        <p className="text-sm text-amber-900 leading-relaxed">
          Ce guide est généré automatiquement à partir de vos rubriques et de votre formule :
          il reste toujours à jour. Cliquez sur une rubrique dans le menu de gauche pour l'utiliser.
        </p>
      </section>
    </div>
  )
}
