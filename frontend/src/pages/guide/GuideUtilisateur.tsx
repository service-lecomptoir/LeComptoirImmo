import { useEffect, useMemo } from 'react'
import type { ElementType } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { featureForPath, isFeatureAllowed } from '@/lib/features'
import { BookOpen, CheckCircle2, Lightbulb, HelpCircle, ListChecks } from 'lucide-react'
import { navForRole, descriptionForRoute } from '@/lib/navigation'

// ─── Types du contenu de guide ────────────────────────────────────────────────
interface Faq { q: string; a: string }

interface Guide {
  badge: string
  title: string
  intro: string
  prerequisites: string[]
  tips: string[]
  faq: Faq[]
}

// ─── Pas à pas généré DYNAMIQUEMENT depuis le menu du rôle ────────────────────
// Source de vérité unique : lib/navigation.ts (+ filtre par formule via les
// fonctionnalités du plan). Tout ajout / renommage / retrait / réorganisation
// d'une rubrique, ou une fonctionnalité (dés)activée par l'abonnement, met le
// pas à pas à jour AUTOMATIQUEMENT (libellé, icône, description, regroupement par
// section). Chaque étape illustrée reprend l'icône de la rubrique.
interface StepItem { to: string; label: string; icon: ElementType; desc: string }
interface StepGroup { section: string; items: StepItem[] }

function buildSteps(role: string | undefined, features: string[] | null): StepGroup[] {
  const groups: StepGroup[] = []
  let current: StepGroup | null = null
  for (const item of navForRole(role)) {
    if (item.isSeparator) {
      current = { section: item.label, items: [] }
      groups.push(current)
      continue
    }
    if (!item.to) continue
    // Respecte la formule : on n'affiche que les rubriques réellement accessibles.
    if (!isFeatureAllowed(features, featureForPath(item.to))) continue
    if (!current) { current = { section: 'Premiers pas', items: [] }; groups.push(current) }
    current.items.push({
      to: item.to, label: item.label,
      icon: item.icon ?? ListChecks, desc: descriptionForRoute(item.to),
    })
  }
  return groups.filter(g => g.items.length > 0)
}

// Illustration d'étape : panneau décoratif construit à partir de l'icône de la
// rubrique (donc une nouvelle fonctionnalité est illustrée sans travail manuel).
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

// ─── Contenu par rôle ───────────────────────────────────────────────────────────
const GUIDE_MANDATAIRE: Guide = {
  badge: 'Gestionnaire mandataire',
  title: 'Gérer les biens de vos propriétaires',
  intro:
    "En tant que gestionnaire mandataire, vous administrez des biens pour le compte de propriétaires : " +
    "vous créez les fiches, rédigez les contrats, suivez les loyers et éditez les documents officiels " +
    "(avis d'échéance, quittances). Ce guide vous accompagne pas à pas, dans l'ordre logique de mise en route.",
  prerequisites: [
    "Disposer des informations de chaque propriétaire (identité, coordonnées et RIB pour le reversement des loyers).",
    "Avoir les caractéristiques de chaque bien (adresse, type, surface, DPE, équipements).",
    "Connaître les informations des locataires (identité, n° de sécurité sociale, date de naissance, contact) et les conditions du bail (loyer, charges, dépôt de garantie).",
    "Renseigner dans « Mes informations » le « Nom de la résidence » (affiché dans l'app) et le « Nom et prénom du propriétaire » (bailleur sur les documents officiels), ainsi que vos coordonnées d'agence.",
  ],
  tips: [
    "Respectez l'ordre Propriétaire → Bien → Locataire → Contrat : chaque étape s'appuie sur la précédente.",
    "Le RIB se saisit une seule fois, sur la fiche du propriétaire : il alimente automatiquement les quittances.",
    "Renseignez le « Nom et prénom du propriétaire » dans « Mes informations » : c'est lui qui apparaît comme bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant.",
    "Choisissez la bonne « règle d'appel de loyer » : calendaire (au prorata des jours) ou contractuelle (date à date).",
    "Résiliez un bail terminé pour libérer le bien et le rendre de nouveau disponible à la mise en location.",
    "Préparez vos annonces à l'avance : laissez l'IA rédiger le titre et la description depuis les caractéristiques du bien, ajoutez vos photos, et programmez la publication : les vues sont suivies automatiquement.",
    "Dès qu'un préavis arrive, ouvrez le dossier de sortie : rien ne s'oublie (état des lieux, retenues, restitution du dépôt), et la clôture résilie le bail proprement.",
    "Sur Propriétés, Propriétaires, Locataires et Contrats, basculez entre vue liste et vue mosaïque via les icônes en haut à droite : votre choix est mémorisé. Chaque liste s'exporte aussi en CSV (bouton « Exporter »).",
  ],
  faq: [
    { q: 'Comment publier l\'annonce d\'un bien ?', a: 'Onglet « Publication des annonces », ou bouton « Diffuser » sur la fiche du bien : ajoutez/supprimez des photos, cliquez sur « Rédiger avec l\'IA » pour générer le titre et la description à partir des caractéristiques du bien (ajustables), choisissez vos plateformes, puis publiez tout de suite ou programmez la date. Une page d\'annonce publique partageable est générée et ses vues sont comptabilisées. Cette rubrique peut être incluse ou non selon votre formule.' },
    { q: 'Comment arrivent les candidatures et comment choisir le bon locataire ?', a: 'Les visiteurs candidatent directement depuis la page publique de votre annonce ; les dossiers se centralisent dans « Candidatures ». Cochez les pièces fournies/vérifiées, puis utilisez « Comparer les profils » : les candidats sont classés par score (taux d\'effort, complétude du dossier, garant) et le mieux placé est mis en avant.' },
    { q: 'Comment gérer le départ d\'un locataire et son dépôt de garantie ?', a: 'Ouvrez un dossier dans « Sortie du locataire » (le dépôt du bail est repris automatiquement). Suivez le préavis, reliez l\'état des lieux de sortie et comparez-le à l\'entrée, saisissez les retenues éventuelles (dégradations…) : le montant à restituer se calcule tout seul. La clôture résilie le bail et libère le bien.' },
    { q: 'Un bien occupé n\'apparaît pas dans la liste lors de la création d\'un contrat, est-ce normal ?', a: 'Oui. Pour éviter les doublons, seuls les biens disponibles sont proposés. Un bien redevient sélectionnable dès que son bail est résilié.' },
    { q: 'Comment ajouter un co-locataire ?', a: 'Dans le formulaire de contrat, section « Co-titulaires », choisissez un locataire existant ou créez-en un avec le bouton « Nouveau ». C\'est possible en création comme en modification.' },
    { q: 'Pourquoi je ne génère qu\'un seul avis pour plusieurs mois ?', a: 'Si la fréquence du bail est trimestrielle, semestrielle ou annuelle, un seul avis couvre toute la période, avec le montant correspondant.' },
    { q: 'Où apparaissent mes coordonnées sur les documents ?', a: 'Les coordonnées de l\'agence (« Mes informations ») et le RIB du propriétaire (sa fiche) figurent automatiquement en en-tête des avis et quittances.' },
    { q: 'Comment générer une attestation de loyer ou un formulaire tiers payant pour la CAF ?', a: 'Onglet « Espace CAF » : sélectionnez le contrat et téléchargez l\'attestation de loyer ou le formulaire tiers payant, pré-remplis à partir du bailleur, du locataire et du bail. La déclaration des loyers à la CAF (par le gestionnaire, sur la plateforme partenaires) est ouverte de juillet à décembre ; un rappel s\'affiche alors. Cette rubrique peut être incluse ou non selon votre formule.' },
    { q: 'Pourquoi un compte n\'apparaît pas dans « Accès espace locataire » ?', a: 'À la création d\'un locataire, seuls les comptes non encore rattachés à une fiche sont proposés (un compte = un seul locataire). En modification, le compte déjà lié à ce locataire reste visible.' },
    { q: 'Où voir mes factures et comment résilier mon abonnement ?', a: 'Dans « Mon abonnement » : vos factures sont téléchargeables en PDF, et le bouton « Mettre fin à mon abonnement » envoie une demande de résiliation à notre équipe. Vous pouvez aussi déclarer vos domaines e-mail autorisés dans « Mes informations ».' },
  ],
}

const GUIDE_GP: Guide = {
  badge: 'Gestionnaire propriétaire',
  title: 'Gérer vos propres biens de A à Z',
  intro:
    "Vous êtes à la fois gestionnaire et propriétaire de vos biens. Vous disposez de tous les outils de gestion " +
    "(biens, locataires, contrats, loyers, documents) et, en plus, d'une vue financière sur vos revenus et votre liasse fiscale. " +
    "Ce guide vous montre comment démarrer et tirer parti de votre double casquette.",
  prerequisites: [
    "Renseigner dans « Mes informations » le « Nom de la résidence », le « Nom et prénom du propriétaire » (bailleur des documents), vos coordonnées et votre RIB.",
    "Réunir les caractéristiques de vos biens (adresse, type, surface, DPE, équipements).",
    "Disposer des informations des locataires (dont n° de sécurité sociale et date de naissance) et des conditions de chaque bail.",
  ],
  tips: [
    "Suivez l'ordre Bien → Locataire → Contrat : tout en découle.",
    "Votre RIB est saisi une seule fois (Mes informations) et figure sur les quittances.",
    "Consultez régulièrement « Mes revenus » et « Liasse fiscale » pour anticiper votre déclaration.",
    "Résiliez un bail terminé pour libérer le bien.",
    "Pour vos annonces, gagnez du temps : l'IA rédige le titre et la description depuis les caractéristiques du bien, et la publication peut être programmée.",
    "Sur vos listes (Propriétés, Locataires, Contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite : le choix est mémorisé. Un bouton « Exporter » génère un CSV de la liste.",
    "Le tableau de bord « Performance par bien » liste désormais tous vos biens, triés par revenu.",
  ],
  faq: [
    { q: 'Dois-je créer une fiche propriétaire pour moi-même ?', a: 'Non. En tant que gestionnaire propriétaire, vous êtes automatiquement rattaché à vos biens.' },
    { q: 'Comment publier l\'annonce d\'un bien ?', a: 'Onglet « Publication des annonces », ou bouton « Diffuser » sur la fiche du bien : ajoutez/supprimez des photos, utilisez « Rédiger avec l\'IA » pour générer le titre et la description depuis les caractéristiques du bien (modifiables), choisissez vos plateformes, puis publiez ou programmez. La page d\'annonce publique est partageable et ses vues sont suivies. Cette rubrique peut être incluse ou non selon votre formule.' },
    { q: 'Comment sont gérées les candidatures et la sortie d\'un locataire ?', a: 'Les candidatures déposées depuis vos annonces se centralisent dans « Candidatures » (pièces à vérifier, comparaison des profils, sélection). Au départ d\'un locataire, « Sortie du locataire » suit le préavis, compare les états des lieux, décompte le dépôt de garantie et clôture le dossier (bail résilié).' },
    { q: 'Où vois-je combien me rapportent mes biens ?', a: 'Dans la section « Mes finances » → « Mes revenus » et « Performance biens ».' },
    { q: 'Comment préparer ma déclaration fiscale ?', a: 'Ouvrez « Liasse fiscale », qui récapitule loyers et charges, et que vous pouvez imprimer.' },
    { q: 'Puis-je créer un locataire pendant la rédaction du bail ?', a: 'Oui, le formulaire de contrat permet de créer un locataire principal et des co-titulaires à la volée.' },
    { q: 'Pourquoi un compte n\'apparaît pas dans « Accès espace locataire » ?', a: 'À la création d\'un locataire, seuls les comptes non encore rattachés à une fiche sont proposés (un compte = un seul locataire). En modification, le compte déjà lié reste visible.' },
    { q: 'Où voir mes factures et comment résilier mon abonnement ?', a: 'Dans « Mon abonnement » : factures téléchargeables en PDF et bouton « Mettre fin à mon abonnement » (envoie une demande de résiliation). Déclarez aussi vos domaines e-mail autorisés dans « Mes informations ».' },
  ],
}

const GUIDE_PROPRIETAIRE: Guide = {
  badge: 'Propriétaire',
  title: 'Suivre vos biens et vos revenus en toute transparence',
  intro:
    "Votre espace propriétaire vous donne une vue claire et en temps réel sur vos biens confiés en gestion : " +
    "revenus perçus, locataires en place, démarches en cours et documents fiscaux. La gestion quotidienne est assurée par votre " +
    "mandataire ; vous, vous suivez et consultez.",
  prerequisites: [
    "Votre compte est créé par votre gestionnaire : utilisez l'identifiant et le mot de passe reçus.",
    "Vérifiez votre RIB dans « Mes informations » : c'est sur ce compte que sont reversés vos loyers.",
    "Vos biens et locataires sont saisis par votre gestionnaire ; vous les retrouvez directement dans votre espace.",
  ],
  tips: [
    "Gardez votre RIB à jour : c'est la condition d'un reversement sans accroc.",
    "Suivez les démarches de vos locataires dans la rubrique « Démarche » et échangez avec votre gestionnaire pour toute question.",
    "Consultez la liasse fiscale en fin d'année pour préparer sereinement votre déclaration.",
    "Sur vos listes (biens, locataires, contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite : le choix est mémorisé. Le bouton « Exporter » télécharge la liste en CSV.",
  ],
  faq: [
    { q: 'Puis-je créer un contrat ou ajouter un locataire ?', a: 'Non : ces actions sont réalisées par votre gestionnaire mandataire. Votre espace est dédié au suivi et à la consultation.' },
    { q: 'Comment signaler un problème sur un bien ?', a: 'La démarche est créée par votre locataire dans son espace ; vous en suivez l\'avancement (relance, clôture) dans la rubrique « Démarche » (lecture seule). Pour échanger, contactez votre gestionnaire.' },
    { q: 'Je ne vois pas un loyer reçu, que faire ?', a: 'Le règlement est peut-être en cours d\'enregistrement par votre gestionnaire. Contactez-le via Messages si le doute persiste.' },
  ],
}

const GUIDE_LOCATAIRE: Guide = {
  badge: 'Locataire',
  title: 'Votre logement et vos loyers, simplement',
  intro:
    "Votre espace locataire réunit tout ce qui concerne votre location : votre bail, vos avis d'échéance, " +
    "le paiement de votre loyer, vos quittances et vos échanges avec votre gestionnaire. Voici comment l'utiliser au quotidien.",
  prerequisites: [
    "Votre compte est créé par votre gestionnaire : connectez-vous avec l'identifiant et le mot de passe reçus.",
    "Un bail actif doit être enregistré à votre nom (c'est le cas dès votre entrée dans le logement).",
    "Pensez à vérifier votre adresse e-mail et votre téléphone dans « Mes informations ».",
  ],
  tips: [
    "Réglez votre loyer avant le jour d'échéance indiqué sur l'avis pour éviter les relances.",
    "Téléchargez et conservez vos quittances : elles servent de justificatif de domicile.",
    "Pour toute demande (incident, question…), créez une démarche dans « Mes démarches » et suivez son évolution ; vous pouvez relancer, ou valider/refuser la clôture proposée par votre gestionnaire.",
    "Si vous bénéficiez d'une aide au logement, elle est déjà déduite du montant à payer sur votre avis.",
  ],
  faq: [
    { q: 'Comment obtenir une quittance de loyer ?', a: 'Dès que votre loyer est enregistré comme payé, la quittance apparaît dans « Mes paiements » et « Mes documents », téléchargeable en PDF.' },
    { q: 'Je n\'arrive pas à me connecter, que faire ?', a: 'Vérifiez que la pastille « Locataire » est bien sélectionnée. En cas d\'oubli de mot de passe, votre gestionnaire peut le réinitialiser.' },
    { q: 'Mon aide au logement n\'apparaît pas ?', a: 'Si elle est gérée en tiers-payant, elle est automatiquement déduite du montant de votre avis. Sinon, contactez votre gestionnaire.' },
    { q: 'Comment télécharger mon bail ?', a: 'Depuis le tableau de bord (« Mon espace »), bouton « Télécharger le bail », ou dans « Mes documents ».' },
  ],
}

function guideForRole(role?: string): Guide {
  if (role === 'gestionnaire_proprio') return GUIDE_GP
  if (role === 'proprietaire') return GUIDE_PROPRIETAIRE
  if (role === 'locataire') return GUIDE_LOCATAIRE
  return GUIDE_MANDATAIRE // admin + gestionnaire
}

export default function GuideUtilisateur() {
  const { user } = useAuthStore()
  const g = guideForRole(user?.role)

  // Filtre par formule : on charge les fonctionnalités du plan (gestionnaires)
  // pour n'afficher que les rubriques réellement accessibles.
  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio' || user?.role === 'admin'
  const { features, loadFeatures } = useFeaturesStore()
  useEffect(() => { if (isManager) loadFeatures() }, [isManager, loadFeatures])

  // Pas à pas généré dynamiquement depuis le menu du rôle (+ filtre formule).
  const groups = useMemo(() => buildSteps(user?.role, features), [user?.role, features])
  const totalSteps = groups.reduce((n, gr) => n + gr.items.length, 0)

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      {/* En-tête */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-500 rounded-2xl p-6 sm:p-8 text-white mb-6">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen size={18} />
          <span className="text-xs font-semibold uppercase tracking-wider bg-white/20 px-2.5 py-1 rounded-full">
            Guide d'utilisation · {g.badge}
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold mb-2">{g.title}</h1>
        <p className="text-blue-50 text-sm sm:text-base leading-relaxed">{g.intro}</p>
      </div>

      {/* Pré-requis */}
      <section className="bg-white rounded-xl border border-gray-200 p-5 sm:p-6 mb-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
          <ListChecks size={18} className="text-blue-600" /> Pré-requis
        </h2>
        <ul className="space-y-2.5">
          {g.prerequisites.map((p, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-gray-700">
              <CheckCircle2 size={16} className="text-green-500 mt-0.5 shrink-0" />
              <span>{p}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Pas à pas (généré dynamiquement depuis le menu + formule) */}
      <section className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Pas à pas : vos rubriques</h2>
          <span className="text-xs text-gray-400">{totalSteps} étape{totalSteps > 1 ? 's' : ''}</span>
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

      {/* Bonnes pratiques */}
      <section className="bg-amber-50 border border-amber-200 rounded-xl p-5 sm:p-6 mb-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-amber-900 mb-4">
          <Lightbulb size={18} className="text-amber-600" /> Bonnes pratiques
        </h2>
        <ul className="space-y-2.5">
          {g.tips.map((t, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-amber-900">
              <span className="text-amber-500 mt-0.5">•</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* FAQ */}
      <section className="bg-white rounded-xl border border-gray-200 p-5 sm:p-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900 mb-4">
          <HelpCircle size={18} className="text-blue-600" /> Questions fréquentes
        </h2>
        <div className="space-y-4">
          {g.faq.map((f, i) => (
            <div key={i}>
              <p className="text-sm font-semibold text-gray-900">{f.q}</p>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed">{f.a}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
