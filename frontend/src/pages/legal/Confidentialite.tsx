import { Link } from 'react-router-dom'

/** Politique de confidentialité (page publique). Rédigée d'après le traitement
 *  réel : données de gestion locative, durées de conservation, droits RGPD. */
export default function Confidentialite() {
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
        <Link to="/" className="text-sm text-[#0D2F5C] hover:underline">← Retour à l'accueil</Link>
        <h1 className="text-2xl font-bold text-[#0D2F5C] mt-4 mb-2">Politique de confidentialité</h1>
        <p className="text-xs text-slate-400 mb-6">Protection des données personnelles (RGPD)</p>

        <section className="space-y-2 text-sm text-slate-700 leading-relaxed">
          <h2 className="font-semibold text-slate-900 mt-4">Responsable du traitement</h2>
          <p>
            <strong>Le Comptoir</strong> (Aronson ALPHANORD), SIREN 823 382 213.
            Contact pour toute question relative aux données :{' '}
            <a className="text-[#0D2F5C] hover:underline" href="mailto:service.lecomptoir@outlook.com">service.lecomptoir@outlook.com</a>.
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Données collectées</h2>
          <ul className="list-disc pl-5">
            <li>Identité et coordonnées (locataires, propriétaires, candidats) : nom, e-mail, téléphone, adresse, date et lieu de naissance.</li>
            <li>Données de solvabilité (candidatures) : situation professionnelle, revenus, pièces justificatives.</li>
            <li>Données de location et financières : baux, loyers, paiements, quittances.</li>
          </ul>

          <h2 className="font-semibold text-slate-900 mt-5">Finalités et bases légales</h2>
          <ul className="list-disc pl-5">
            <li>Gestion locative et exécution des contrats de bail (exécution du contrat).</li>
            <li>Facturation, quittances et comptabilité (obligation légale).</li>
            <li>Traitement des candidatures de location (mesures précontractuelles).</li>
          </ul>

          <h2 className="font-semibold text-slate-900 mt-5">Durées de conservation</h2>
          <ul className="list-disc pl-5">
            <li>Locataires : jusqu'à 3 ans après la fin du bail, puis anonymisation.</li>
            <li>Candidatures refusées : 12 mois, puis anonymisation.</li>
            <li>Documents comptables : conservés selon les obligations légales (jusqu'à 10 ans).</li>
          </ul>

          <h2 className="font-semibold text-slate-900 mt-5">Destinataires</h2>
          <p>
            Les données sont accessibles à votre gestionnaire et à nos sous-traitants techniques :
            l'hébergeur (OVH, France), le prestataire de paiement (Stripe) et le service d'envoi
            d'e-mails (Brevo). Aucune donnée n'est vendue ni cédée à des tiers à des fins commerciales.
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Cookies</h2>
          <p>
            Le site n'utilise que des cookies/jetons strictement nécessaires à votre connexion et à
            la sécurité. Aucun cookie de mesure d'audience ou de publicité n'est déposé : aucun
            consentement n'est donc requis.
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Vos droits</h2>
          <p>
            Vous disposez des droits d'accès, de rectification, d'effacement, de portabilité,
            de limitation et d'opposition. Pour les exercer :{' '}
            <a className="text-[#0D2F5C] hover:underline" href="mailto:service.lecomptoir@outlook.com">service.lecomptoir@outlook.com</a>.
            La plateforme permet l'export et l'effacement de vos données sur demande. Vous pouvez
            aussi introduire une réclamation auprès de la CNIL (<a className="text-[#0D2F5C] hover:underline" href="https://www.cnil.fr" target="_blank" rel="noreferrer">cnil.fr</a>).
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Sécurité</h2>
          <p>
            Les secrets sont chiffrés, les accès sont restreints par rôle et les bases de données
            sont sauvegardées quotidiennement avec test de restauration.
          </p>
        </section>
      </div>
    </div>
  )
}
