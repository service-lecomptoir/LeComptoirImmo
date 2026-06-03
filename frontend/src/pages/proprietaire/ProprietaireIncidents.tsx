import IncidentList from '@/pages/incidents/IncidentList'
import { ticketsApi } from '@/api/tickets'

export default function ProprietaireIncidents() {
  return (
    <IncidentList
      readOnly
      fetchFn={(params) => ticketsApi.proprietaire(params)}
      title="Démarches de mes locataires"
      subtitle="Suivi en lecture seule des démarches soumises par vos locataires"
    />
  )
}
