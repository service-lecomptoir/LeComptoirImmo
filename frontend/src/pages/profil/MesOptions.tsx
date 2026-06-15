import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import SignatureSection from './sections/SignatureSection'
import EmailDomainsSection from './sections/EmailDomainsSection'
import AgentsSection from './sections/AgentsSection'
import PaymentOnlineSection from './PaymentOnlineSection'

/** « Mes options » (gestionnaire / gestionnaire-propriétaire) : signature,
 *  domaines e-mail autorisés, paiement du loyer par carte, agents IA. */
export default function MesOptions() {
  const { user } = useAuthStore()
  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio'
  if (!isManager) return <Navigate to="/profil" replace />

  return (
    <div className="max-w-2xl p-4 sm:p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mes options</h1>
        <p className="text-gray-500 text-sm mt-1">
          Signature, domaines d'envoi, paiement du loyer par carte et agents IA.
        </p>
      </div>
      <SignatureSection />
      <EmailDomainsSection />
      <PaymentOnlineSection />
      <AgentsSection />
    </div>
  )
}
