import { useAuthStore } from '@/store/authStore'
import {
  BookOpen, CheckCircle2, Lightbulb, HelpCircle, ListChecks,
  Building2, Users, KeyRound, FileText, CreditCard, Calendar,
  FileCheck, MessageSquare, Wrench, Calculator, Wallet, Receipt,
  Settings, Zap, ShoppingBag,
} from 'lucide-react'
import type { ElementType } from 'react'

// ─── Types du contenu de guide ────────────────────────────────────────────────
interface Step { title: string; desc: string }
interface Feature { icon: ElementType; title: string; desc: string }
interface Faq { q: string; a: string }
interface Guide {
  badge: string
  title: string
  intro: string
  prerequisites: string[]
  steps: Step[]
  features: Feature[]
  tips: string[]
  faq: Faq[]
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
    "Connaître les informations des locataires (identité, contact) et les conditions du bail (loyer, charges, dépôt de garantie).",
    "Renseigner vos coordonnées d'agence dans « Mes informations » : elles apparaissent en en-tête des documents.",
  ],
  steps: [
    { title: '1. Créez les fiches Propriétaires', desc: "Onglet Propriétaires → « Nouveau ». Saisissez l'identité, le contact et surtout le RIB : c'est lui qui figure sur les quittances. Une fiche peut exister sans compte de connexion." },
    { title: '2. Enregistrez les Propriétés', desc: "Onglet Propriétés → « Nouveau ». Décrivez le bien et rattachez-le à une fiche propriétaire. Un bien occupé ne sera plus proposé lors de la création d'un nouveau contrat." },
    { title: '3. Créez les fiches Locataires', desc: "Onglet Locataires → « Nouveau ». Vous pourrez aussi en créer un à la volée depuis le formulaire de contrat." },
    { title: '4. Rédigez le Contrat de bail', desc: "Onglet Contrats → « Nouveau ». Reliez un bien et un locataire principal, ajoutez d'éventuels co-titulaires, puis renseignez loyer, charges, dépôt, jour et fréquence de paiement, règle d'appel de loyer, aide au logement et garant." },
    { title: '5. Pilotez les loyers', desc: "Les avis d'échéances et les paiements se génèrent automatiquement selon la fréquence choisie. Enregistrez les règlements reçus, puis générez/envoyez les quittances." },
    { title: '6. Donnez les accès', desc: "Dans Administration, créez les comptes de connexion pour vos propriétaires et locataires en les rattachant à leur fiche, afin qu'ils accèdent à leur propre espace." },
  ],
  features: [
    { icon: Building2, title: 'Propriétés', desc: "Le parc géré, avec caractéristiques, statut d'occupation et propriétaire rattaché." },
    { icon: KeyRound, title: 'Propriétaires', desc: 'Les fiches des bailleurs (identité, RIB unique, biens rattachés).' },
    { icon: Users, title: 'Locataires', desc: 'Les fiches locataires, indépendantes de leur compte de connexion.' },
    { icon: FileText, title: 'Contrats', desc: 'Les baux : loyer, charges, dépôt, co-titulaires, règle et fréquence d\'appel.' },
    { icon: Calendar, title: "Avis d'échéances", desc: 'Les appels de loyer, générés et imprimables en PDF selon la fréquence du bail.' },
    { icon: CreditCard, title: 'Paiements', desc: 'Le suivi des règlements : encaissement, relance, génération de quittance.' },
    { icon: FileCheck, title: 'Quittances', desc: 'Les quittances de loyer officielles, à télécharger ou envoyer au locataire.' },
    { icon: MessageSquare, title: 'Incidents & messages', desc: 'La communication avec les locataires et le suivi des signalements.' },
    { icon: Wrench, title: 'Entretiens', desc: 'La planification et le suivi des interventions et prestataires.' },
    { icon: Zap, title: 'Automatisation', desc: 'Les règles automatiques (rappels, relances) pour gagner du temps.' },
    { icon: Settings, title: 'Administration', desc: 'La création et la gestion des comptes de connexion (propriétaires, locataires).' },
  ],
  tips: [
    "Respectez l'ordre Propriétaire → Bien → Locataire → Contrat : chaque étape s'appuie sur la précédente.",
    "Le RIB se saisit une seule fois, sur la fiche du propriétaire : il alimente automatiquement les quittances.",
    "Choisissez la bonne « règle d'appel de loyer » : calendaire (au prorata des jours) ou contractuelle (date à date).",
    "Résiliez un bail terminé pour libérer le bien et le rendre de nouveau disponible à la mise en location.",
    "Sur Propriétés, Propriétaires, Locataires et Contrats, basculez entre vue liste et vue mosaïque via les icônes en haut à droite — votre choix est mémorisé. Chaque liste s'exporte aussi en CSV (bouton « Exporter »).",
  ],
  faq: [
    { q: 'Un bien occupé n\'apparaît pas dans la liste lors de la création d\'un contrat, est-ce normal ?', a: 'Oui. Pour éviter les doublons, seuls les biens disponibles sont proposés. Un bien redevient sélectionnable dès que son bail est résilié.' },
    { q: 'Comment ajouter un co-locataire ?', a: 'Dans le formulaire de contrat, section « Co-titulaires », choisissez un locataire existant ou créez-en un avec le bouton « Nouveau ». C\'est possible en création comme en modification.' },
    { q: 'Pourquoi je ne génère qu\'un seul avis pour plusieurs mois ?', a: 'Si la fréquence du bail est trimestrielle, semestrielle ou annuelle, un seul avis couvre toute la période, avec le montant correspondant.' },
    { q: 'Où apparaissent mes coordonnées sur les documents ?', a: 'Les coordonnées de l\'agence (« Mes informations ») et le RIB du propriétaire (sa fiche) figurent automatiquement en en-tête des avis et quittances.' },
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
    "Renseigner vos coordonnées et votre RIB dans « Mes informations » : ils alimentent l'en-tête et les quittances.",
    "Réunir les caractéristiques de vos biens (adresse, type, surface, DPE, équipements).",
    "Disposer des informations des locataires et des conditions de chaque bail.",
  ],
  steps: [
    { title: '1. Complétez votre profil', desc: "Dans « Mes informations », vérifiez vos coordonnées et votre RIB : ils servent aux documents et au reversement des loyers." },
    { title: '2. Enregistrez vos Propriétés', desc: "Onglet Propriétés → « Nouveau ». Vous êtes automatiquement le propriétaire rattaché — pas besoin de créer une fiche propriétaire séparée." },
    { title: '3. Créez les fiches Locataires', desc: "Onglet Locataires → « Nouveau », ou directement depuis le formulaire de contrat." },
    { title: '4. Rédigez le Contrat de bail', desc: "Onglet Contrats → « Nouveau » : bien, locataire principal, co-titulaires, loyer, charges, dépôt, jour et fréquence de paiement, règle d'appel, aide au logement, garant." },
    { title: '5. Suivez les loyers', desc: "Avis d'échéances et paiements se génèrent selon la fréquence. Enregistrez les règlements et éditez les quittances." },
    { title: '6. Pilotez vos finances', desc: "Section « Mes finances » : suivez vos revenus, la performance de vos biens et préparez votre liasse fiscale." },
  ],
  features: [
    { icon: Building2, title: 'Propriétés', desc: 'Vos biens et leur statut d\'occupation.' },
    { icon: Users, title: 'Locataires', desc: 'Les fiches de vos locataires.' },
    { icon: FileText, title: 'Contrats', desc: 'Vos baux et leurs conditions financières.' },
    { icon: Calendar, title: "Avis d'échéances", desc: 'Les appels de loyer en PDF, selon la fréquence du bail.' },
    { icon: CreditCard, title: 'Paiements', desc: 'Le suivi des encaissements et des relances.' },
    { icon: FileCheck, title: 'Quittances', desc: 'Vos quittances de loyer officielles.' },
    { icon: Calculator, title: 'Mes finances', desc: 'Revenus, performance des biens et liasse fiscale.' },
    { icon: MessageSquare, title: 'Incidents', desc: 'Le suivi des signalements de vos locataires.' },
    { icon: Wrench, title: 'Entretiens', desc: 'La gestion des interventions et prestataires.' },
    { icon: Settings, title: 'Administration', desc: 'Les comptes de connexion de vos locataires.' },
  ],
  tips: [
    "Suivez l'ordre Bien → Locataire → Contrat : tout en découle.",
    "Votre RIB est saisi une seule fois (Mes informations) et figure sur les quittances.",
    "Consultez régulièrement « Mes revenus » et « Liasse fiscale » pour anticiper votre déclaration.",
    "Résiliez un bail terminé pour libérer le bien.",
    "Sur vos listes (Propriétés, Locataires, Contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite — le choix est mémorisé. Un bouton « Exporter » génère un CSV de la liste.",
    "Le tableau de bord « Performance par bien » liste désormais tous vos biens, triés par revenu.",
  ],
  faq: [
    { q: 'Dois-je créer une fiche propriétaire pour moi-même ?', a: 'Non. En tant que gestionnaire propriétaire, vous êtes automatiquement rattaché à vos biens.' },
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
    "revenus perçus, locataires en place, incidents et documents fiscaux. La gestion quotidienne est assurée par votre " +
    "mandataire ; vous, vous suivez et consultez.",
  prerequisites: [
    "Votre compte est créé par votre gestionnaire : utilisez l'identifiant et le mot de passe reçus.",
    "Vérifiez votre RIB dans « Mes informations » : c'est sur ce compte que sont reversés vos loyers.",
    "Vos biens et locataires sont saisis par votre gestionnaire ; vous les retrouvez directement dans votre espace.",
  ],
  steps: [
    { title: '1. Connectez-vous à votre espace', desc: "Sur la page d'accueil, choisissez la pastille « Propriétaire » puis saisissez vos identifiants." },
    { title: '2. Vérifiez vos informations', desc: "Dans « Mes informations », contrôlez vos coordonnées et votre RIB pour le bon reversement des loyers." },
    { title: '3. Consultez votre tableau de bord', desc: "Vue d'ensemble : revenus, taux d'occupation et points d'attention sur vos biens." },
    { title: '4. Suivez vos revenus', desc: "« Mes revenus » détaille les loyers encaissés, période par période et bien par bien." },
    { title: '5. Préparez votre fiscalité', desc: "« Liasse fiscale » récapitule loyers et charges ; téléchargez-la pour votre déclaration." },
  ],
  features: [
    { icon: Building2, title: 'Mes biens', desc: 'Le détail de chaque bien et son statut d\'occupation.' },
    { icon: CreditCard, title: 'Mes revenus', desc: 'Les loyers perçus, par période et par bien.' },
    { icon: Users, title: 'Mes locataires', desc: 'Les locataires en place dans vos biens.' },
    { icon: MessageSquare, title: 'Incidents & messages', desc: 'Le suivi des signalements et les échanges avec votre gestionnaire.' },
    { icon: Wrench, title: 'Entretiens', desc: 'Les interventions réalisées ou planifiées sur vos biens.' },
    { icon: Calculator, title: 'Liasse fiscale', desc: 'Le récapitulatif annuel pour votre déclaration de revenus fonciers.' },
  ],
  tips: [
    "Gardez votre RIB à jour : c'est la condition d'un reversement sans accroc.",
    "Utilisez les messages pour toute question : votre gestionnaire y répond.",
    "Consultez la liasse fiscale en fin d'année pour préparer sereinement votre déclaration.",
    "Sur vos listes (biens, locataires, contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite — le choix est mémorisé. Le bouton « Exporter » télécharge la liste en CSV.",
  ],
  faq: [
    { q: 'Puis-je créer un contrat ou ajouter un locataire ?', a: 'Non : ces actions sont réalisées par votre gestionnaire mandataire. Votre espace est dédié au suivi et à la consultation.' },
    { q: 'Comment signaler un problème sur un bien ?', a: 'Via la rubrique « Incidents » ou « Messages » : votre gestionnaire est notifié.' },
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
  steps: [
    { title: '1. Connectez-vous', desc: "Sur la page d'accueil, gardez la pastille « Locataire » et saisissez vos identifiants." },
    { title: '2. Découvrez votre espace', desc: "Le tableau de bord affiche votre bail, votre prochain avis d'échéance et votre dernier paiement." },
    { title: '3. Consultez vos avis d\'échéance', desc: "« Avis d'échéances » liste vos appels de loyer ; vous pouvez les télécharger en PDF." },
    { title: '4. Payez votre loyer', desc: "« Payer mon loyer » vous indique le montant dû et les coordonnées de paiement (virement, etc.)." },
    { title: '5. Récupérez vos quittances', desc: "Une fois le loyer réglé, votre quittance est disponible dans « Mes paiements » et « Mes documents »." },
  ],
  features: [
    { icon: Calendar, title: "Avis d'échéances", desc: 'Vos appels de loyer mensuels (ou selon la fréquence du bail), en PDF.' },
    { icon: Wallet, title: 'Payer mon loyer', desc: 'Le montant dû et les modalités de règlement.' },
    { icon: CreditCard, title: 'Mes paiements', desc: 'L\'historique de vos règlements et le téléchargement des quittances.' },
    { icon: MessageSquare, title: 'Mes messages', desc: 'Vos échanges avec votre gestionnaire et le signalement d\'incidents.' },
    { icon: Receipt, title: 'Mes documents', desc: 'Votre bail, vos quittances et tous les documents liés à votre location.' },
    { icon: ShoppingBag, title: 'Offres & Services', desc: 'Les services proposés (assurance, box internet, etc.).' },
  ],
  tips: [
    "Réglez votre loyer avant le jour d'échéance indiqué sur l'avis pour éviter les relances.",
    "Téléchargez et conservez vos quittances : elles servent de justificatif de domicile.",
    "Pour toute question ou problème dans le logement, utilisez « Mes messages ».",
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

      {/* Premiers pas */}
      <section className="mb-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Premiers pas</h2>
        <ol className="space-y-3">
          {g.steps.map((s, i) => (
            <li key={i} className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 flex gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold text-sm flex items-center justify-center shrink-0">
                {i + 1}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{s.title.replace(/^\d+\.\s*/, '')}</p>
                <p className="text-sm text-gray-600 mt-0.5 leading-relaxed">{s.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Fonctionnalités */}
      <section className="mb-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Vos rubriques en un coup d'œil</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {g.features.map((f, i) => {
            const Icon = f.icon
            return (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
                <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                  <Icon size={17} className="text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{f.title}</p>
                  <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            )
          })}
        </div>
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
