import { useAuthStore } from '@/store/authStore'
import { BookOpen, CheckCircle2, Lightbulb, HelpCircle, ListChecks } from 'lucide-react'
import type { ElementType } from 'react'
import { navForRole, descriptionForRoute } from '@/lib/navigation'

// ─── Types du contenu de guide ────────────────────────────────────────────────
interface Step { title: string; desc: string }
interface Feature { icon: ElementType; title: string; desc: string }
interface Faq { q: string; a: string }

// ─── Rubriques générées depuis le MENU du rôle (source de vérité : lib/navigation.ts) ─
// Le menu latéral et le guide partagent la même définition : tout ajout, renommage
// ou retrait d'une fonctionnalité dans la navigation met le guide à jour
// automatiquement (libellé + icône du menu, description via descriptionForRoute).
function rubriquesForRole(role?: string): Feature[] {
  return navForRole(role)
    .filter(item => !item.isSeparator && item.to)
    .map(item => ({
      icon: item.icon ?? ListChecks,
      title: item.label,
      desc: descriptionForRoute(item.to),
    }))
}

interface Guide {
  badge: string
  title: string
  intro: string
  prerequisites: string[]
  steps: Step[]
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
    "Connaître les informations des locataires (identité, n° de sécurité sociale, date de naissance, contact) et les conditions du bail (loyer, charges, dépôt de garantie).",
    "Renseigner dans « Mes informations » le « Nom de la résidence » (affiché dans l'app) et le « Nom et prénom du propriétaire » (bailleur sur les documents officiels), ainsi que vos coordonnées d'agence.",
  ],
  steps: [
    { title: '1. Créez les fiches Propriétaires', desc: "Onglet Propriétaires → « Nouveau ». Saisissez l'identité, le contact et surtout le RIB : c'est lui qui figure sur les quittances. Une fiche peut exister sans compte de connexion." },
    { title: '2. Enregistrez les Propriétés', desc: "Onglet Propriétés → « Nouveau ». Décrivez le bien (le code postal et la ville bénéficient d'une autocomplétion) et rattachez-le à une fiche propriétaire. Un bien occupé ne sera plus proposé lors de la création d'un contrat." },
    { title: '3. Créez les fiches Locataires', desc: "Onglet Locataires → « Nouveau ». Le n° de sécurité sociale et la date de naissance sont obligatoires. Vous pouvez aussi créer un locataire à la volée depuis le formulaire de contrat." },
    { title: '4. Rédigez le Contrat de bail', desc: "Onglet Contrats → « Nouveau ». Reliez un bien et un locataire principal, ajoutez d'éventuels co-titulaires, puis renseignez loyer, charges, dépôt, jour et fréquence de paiement, règle d'appel de loyer, aide au logement et garant. Le bail PDF (« Bail non meublé ») se télécharge depuis la fiche du contrat." },
    { title: '5. Pilotez les loyers', desc: "Les avis d'échéances et les paiements se génèrent automatiquement selon la fréquence choisie. Enregistrez les règlements reçus, puis générez/envoyez les quittances." },
    { title: '6. Éditez les Documents CAF', desc: "Onglet « Documents CAF » : générez l'attestation de loyer et le formulaire tiers payant pré-remplis pour chaque contrat (le bailleur n'a plus qu'à vérifier et signer)." },
    { title: '7. Diffusez vos biens', desc: "Onglet « Diffusion des annonces » : définissez une fois vos plateformes de partage, puis composez l'annonce de chaque bien (photos issues de ses documents, description, loyer) et publiez-la immédiatement ou programmez sa publication. Une page d'annonce publique partageable est générée." },
    { title: '8. Donnez les accès', desc: "Dans « Gestion des utilisateurs », créez les comptes de connexion pour vos propriétaires et locataires en les rattachant à leur fiche, afin qu'ils accèdent à leur propre espace." },
  ],
  tips: [
    "Respectez l'ordre Propriétaire → Bien → Locataire → Contrat : chaque étape s'appuie sur la précédente.",
    "Le RIB se saisit une seule fois, sur la fiche du propriétaire : il alimente automatiquement les quittances.",
    "Renseignez le « Nom et prénom du propriétaire » dans « Mes informations » : c'est lui qui apparaît comme bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant.",
    "Choisissez la bonne « règle d'appel de loyer » : calendaire (au prorata des jours) ou contractuelle (date à date).",
    "Résiliez un bail terminé pour libérer le bien et le rendre de nouveau disponible à la mise en location.",
    "Préparez vos annonces à l'avance : le contenu et les photos sont enregistrés par bien et réutilisables, et la publication peut être programmée à la date de votre choix.",
    "Sur Propriétés, Propriétaires, Locataires et Contrats, basculez entre vue liste et vue mosaïque via les icônes en haut à droite — votre choix est mémorisé. Chaque liste s'exporte aussi en CSV (bouton « Exporter »).",
  ],
  faq: [
    { q: 'Comment diffuser l\'annonce d\'un bien ?', a: 'Onglet « Diffusion des annonces », ou bouton « Diffuser » sur la fiche du bien : sélectionnez les photos (issues des documents du bien) et vos plateformes, rédigez le texte, puis publiez tout de suite ou programmez la date. Une page d\'annonce publique partageable est générée. Cette rubrique peut être incluse ou non selon votre formule.' },
    { q: 'Un bien occupé n\'apparaît pas dans la liste lors de la création d\'un contrat, est-ce normal ?', a: 'Oui. Pour éviter les doublons, seuls les biens disponibles sont proposés. Un bien redevient sélectionnable dès que son bail est résilié.' },
    { q: 'Comment ajouter un co-locataire ?', a: 'Dans le formulaire de contrat, section « Co-titulaires », choisissez un locataire existant ou créez-en un avec le bouton « Nouveau ». C\'est possible en création comme en modification.' },
    { q: 'Pourquoi je ne génère qu\'un seul avis pour plusieurs mois ?', a: 'Si la fréquence du bail est trimestrielle, semestrielle ou annuelle, un seul avis couvre toute la période, avec le montant correspondant.' },
    { q: 'Où apparaissent mes coordonnées sur les documents ?', a: 'Les coordonnées de l\'agence (« Mes informations ») et le RIB du propriétaire (sa fiche) figurent automatiquement en en-tête des avis et quittances.' },
    { q: 'Comment générer une attestation de loyer ou un formulaire tiers payant pour la CAF ?', a: 'Onglet « Documents CAF » : sélectionnez le contrat et téléchargez l\'attestation de loyer ou le formulaire tiers payant, pré-remplis à partir du bailleur, du locataire et du bail. Cette rubrique peut être incluse ou non selon votre formule.' },
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
  steps: [
    { title: '1. Complétez votre profil', desc: "Dans « Mes informations », renseignez le « Nom de la résidence », le « Nom et prénom du propriétaire » (qui apparaît comme bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant), vos coordonnées et votre RIB." },
    { title: '2. Enregistrez vos Propriétés', desc: "Onglet Propriétés → « Nouveau ». Vous êtes automatiquement le propriétaire rattaché — pas besoin de créer une fiche propriétaire séparée." },
    { title: '3. Créez les fiches Locataires', desc: "Onglet Locataires → « Nouveau », ou directement depuis le formulaire de contrat." },
    { title: '4. Rédigez le Contrat de bail', desc: "Onglet Contrats → « Nouveau » : bien, locataire principal, co-titulaires, loyer, charges, dépôt, jour et fréquence de paiement, règle d'appel, aide au logement, garant." },
    { title: '5. Suivez les loyers', desc: "Avis d'échéances et paiements se génèrent selon la fréquence. Enregistrez les règlements et éditez les quittances." },
    { title: '6. Éditez vos Documents CAF', desc: "Onglet « Documents CAF » : attestation de loyer et formulaire tiers payant pré-remplis, prêts à signer." },
    { title: '7. Diffusez vos biens', desc: "Onglet « Diffusion des annonces » : définissez vos plateformes de partage, composez l'annonce de chaque bien (photos issues de ses documents, description, loyer), puis publiez immédiatement ou programmez la publication. Une page d'annonce publique partageable est générée." },
    { title: '8. Pilotez vos finances', desc: "Section « Mes finances » : suivez « Mes revenus », la « Performance bien » et préparez votre « Liasse fiscale »." },
  ],
  tips: [
    "Suivez l'ordre Bien → Locataire → Contrat : tout en découle.",
    "Votre RIB est saisi une seule fois (Mes informations) et figure sur les quittances.",
    "Consultez régulièrement « Mes revenus » et « Liasse fiscale » pour anticiper votre déclaration.",
    "Résiliez un bail terminé pour libérer le bien.",
    "Préparez et programmez la diffusion de vos annonces : photos et contenu sont enregistrés par bien et réutilisables.",
    "Sur vos listes (Propriétés, Locataires, Contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite — le choix est mémorisé. Un bouton « Exporter » génère un CSV de la liste.",
    "Le tableau de bord « Performance par bien » liste désormais tous vos biens, triés par revenu.",
  ],
  faq: [
    { q: 'Dois-je créer une fiche propriétaire pour moi-même ?', a: 'Non. En tant que gestionnaire propriétaire, vous êtes automatiquement rattaché à vos biens.' },
    { q: 'Comment diffuser l\'annonce d\'un bien ?', a: 'Onglet « Diffusion des annonces », ou bouton « Diffuser » sur la fiche du bien : choisissez les photos et vos plateformes, rédigez le texte, puis publiez ou programmez la publication. Une page d\'annonce publique partageable est générée. Cette rubrique peut être incluse ou non selon votre formule.' },
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
  steps: [
    { title: '1. Connectez-vous à votre espace', desc: "Sur la page d'accueil, choisissez la pastille « Propriétaire » puis saisissez vos identifiants." },
    { title: '2. Vérifiez vos informations', desc: "Dans « Mes informations », contrôlez vos coordonnées et votre RIB pour le bon reversement des loyers." },
    { title: '3. Consultez votre tableau de bord', desc: "Vue d'ensemble : revenus, taux d'occupation et points d'attention sur vos biens." },
    { title: '4. Suivez vos revenus', desc: "« Mes revenus » détaille les loyers encaissés, période par période et bien par bien." },
    { title: '5. Préparez votre fiscalité', desc: "« Liasse fiscale » récapitule loyers et charges ; téléchargez-la pour votre déclaration." },
  ],
  tips: [
    "Gardez votre RIB à jour : c'est la condition d'un reversement sans accroc.",
    "Suivez les démarches de vos locataires dans la rubrique « Démarche » et échangez avec votre gestionnaire pour toute question.",
    "Consultez la liasse fiscale en fin d'année pour préparer sereinement votre déclaration.",
    "Sur vos listes (biens, locataires, contrats), basculez entre vue liste et mosaïque via les icônes en haut à droite — le choix est mémorisé. Le bouton « Exporter » télécharge la liste en CSV.",
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
  steps: [
    { title: '1. Connectez-vous', desc: "Sur la page d'accueil, gardez la pastille « Locataire » et saisissez vos identifiants." },
    { title: '2. Découvrez votre espace', desc: "Le tableau de bord affiche votre bail, votre prochain avis d'échéance et votre dernier paiement." },
    { title: '3. Consultez vos avis d\'échéance', desc: "« Avis d'échéances » liste vos appels de loyer ; vous pouvez les télécharger en PDF." },
    { title: '4. Payez votre loyer', desc: "« Payer mon loyer » vous indique le montant dû et les coordonnées de paiement (virement, etc.)." },
    { title: '5. Récupérez vos quittances', desc: "Une fois le loyer réglé, votre quittance est disponible dans « Mes paiements » et « Mes documents »." },
    { title: '6. Faites vos démarches', desc: "Dans « Mes démarches », créez une demande en choisissant son type (problème dans le logement, problème de voisinage, autre) : le bon service est alerté automatiquement. Échangez ensuite avec votre gestionnaire, relancez si besoin, et validez ou refusez la clôture qu'il propose." },
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
  // Rubriques générées automatiquement depuis le menu du rôle (lib/navigation.ts).
  const rubriques = rubriquesForRole(user?.role)

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
          {rubriques.map((f, i) => {
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
