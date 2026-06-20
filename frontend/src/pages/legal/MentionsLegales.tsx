import { Link } from 'react-router-dom'

/** Mentions légales (page publique). Données éditeur fournies par l'exploitant.
 *  ⚠️ L'adresse du siège reste à compléter (obligation légale). */
export default function MentionsLegales() {
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
        <Link to="/" className="text-sm text-[#0D2F5C] hover:underline">← Retour à l'accueil</Link>
        <h1 className="text-2xl font-bold text-[#0D2F5C] mt-4 mb-6">Mentions légales</h1>

        <section className="space-y-2 text-sm text-slate-700 leading-relaxed">
          <h2 className="font-semibold text-slate-900 mt-4">Éditeur du site</h2>
          <p>
            Le présent site « Le Comptoir Immo » est édité par <strong>Le Comptoir</strong>,
            entreprise individuelle (régime de l'auto-entrepreneur), exploitée par
            <strong> Aronson ALPHANORD</strong>.
          </p>
          <ul className="list-disc pl-5">
            <li>SIREN : <strong>823 382 213</strong></li>
            <li>TVA : non applicable, article 293 B du Code général des impôts (franchise en base)</li>
            <li>Siège : <strong>[ADRESSE — À COMPLÉTER]</strong></li>
            <li>Contact : <a className="text-[#0D2F5C] hover:underline" href="mailto:service.lecomptoir@outlook.com">service.lecomptoir@outlook.com</a></li>
            <li>Directeur de la publication : <strong>Aronson ALPHANORD</strong></li>
          </ul>

          <h2 className="font-semibold text-slate-900 mt-5">Hébergement</h2>
          <p>
            Le site est hébergé par <strong>OVH SAS</strong>, 2 rue Kellermann, 59100 Roubaix,
            France — <a className="text-[#0D2F5C] hover:underline" href="https://www.ovhcloud.com" target="_blank" rel="noreferrer">ovhcloud.com</a>.
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Propriété intellectuelle</h2>
          <p>
            L'ensemble des contenus du site (textes, interface, logo, code) est protégé par le
            droit de la propriété intellectuelle. Toute reproduction sans autorisation est interdite.
          </p>

          <h2 className="font-semibold text-slate-900 mt-5">Données personnelles</h2>
          <p>
            Le traitement des données personnelles est décrit dans notre{' '}
            <Link to="/confidentialite" className="text-[#0D2F5C] hover:underline">Politique de confidentialité</Link>.
            Pour toute question : <a className="text-[#0D2F5C] hover:underline" href="mailto:service.lecomptoir@outlook.com">service.lecomptoir@outlook.com</a>.
          </p>
        </section>
      </div>
    </div>
  )
}
