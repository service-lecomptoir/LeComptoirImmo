import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { CalendarClock, CheckCircle2, Loader2, Users, MapPin } from 'lucide-react'
import { publicCandidatureApi, type PublicVisits } from '@/api/publicCandidature'
import { toast } from '@/store/toast'
import { LogoMark } from '@/components/common/Logo'

const NAVY = '#0D2F5C'

function fmtDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
}
function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

export default function CandidatureVisit() {
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<PublicVisits | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [bookingId, setBookingId] = useState<string | null>(null)

  const load = () => {
    if (!token) return
    publicCandidatureApi.getVisits(token)
      .then(r => setData(r.data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }
  useEffect(load, [token])

  const book = async (slotId: string) => {
    if (!token) return
    setBookingId(slotId)
    try {
      await publicCandidatureApi.bookVisit(token, slotId)
      const r = await publicCandidatureApi.getVisits(token)
      setData(r.data)
      toast.success('Créneau réservé. À très bientôt !')
    } catch (e: any) {
      const msg = e?.response?.status === 409
        ? 'Ce créneau vient d\'être complété. Choisissez-en un autre.'
        : 'Réservation impossible pour le moment.'
      toast.error(msg)
      load()
    } finally {
      setBookingId(null)
    }
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement…</div>
  if (notFound || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
        <CalendarClock size={40} className="text-gray-300 mb-3" />
        <h1 className="text-xl font-bold text-gray-900">Lien indisponible</h1>
        <p className="text-gray-500 mt-1 text-sm">Ce lien de réservation n'est plus valable. Contactez votre gestionnaire.</p>
      </div>
    )
  }

  const booked = data.booked_slot_id

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: NAVY }}><LogoMark size={17} className="text-white" /></div>
          <span className="font-semibold text-gray-900 text-sm">Le Comptoir Immo</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Réserver une visite</h1>
          <p className="text-gray-500 text-sm mt-1">
            Bonjour {data.candidate_name}, votre dossier a été retenu pour le bien référencé{' '}
            <span className="font-semibold text-gray-700">{data.property_ref || '—'}</span>. Choisissez un créneau ci-dessous.
          </p>
        </div>

        {data.property_address && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700">
            <MapPin size={16} className="mt-0.5 shrink-0 text-gray-400" />
            <span><span className="font-medium">Adresse de la visite :</span> {data.property_address}</span>
          </div>
        )}

        <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
          <Users size={16} className="mt-0.5 shrink-0" />
          <span>D'autres candidats sont également conviés : les créneaux sont attribués dans l'ordre des réservations. Choisissez le vôtre rapidement.</span>
        </div>

        {booked && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 text-emerald-800 px-3 py-2.5 text-sm">
            <CheckCircle2 size={16} /> Votre créneau est réservé. Vous pouvez le modifier en choisissant un autre créneau.
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
          {data.slots.length === 0 ? (
            <p className="px-4 py-8 text-sm text-gray-400 text-center">Aucun créneau disponible pour le moment. Revenez un peu plus tard.</p>
          ) : data.slots.map(s => {
            const isBooked = s.id === booked
            const full = s.remaining <= 0 && !isBooked
            return (
              <div key={s.id} className="flex items-center justify-between gap-3 px-4 py-3.5">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 capitalize">{fmtDate(s.starts_at)}</p>
                  <p className="text-xs text-gray-500">
                    {fmtTime(s.starts_at)} · {s.duration_min} min
                    {!isBooked && <span className="ml-2">{full ? 'Complet' : `${s.remaining} place${s.remaining > 1 ? 's' : ''} restante${s.remaining > 1 ? 's' : ''}`}</span>}
                  </p>
                </div>
                <button
                  onClick={() => book(s.id)}
                  disabled={bookingId === s.id || isBooked || full}
                  className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 ${
                    isBooked ? 'bg-emerald-100 text-emerald-700' : full ? 'bg-gray-100 text-gray-400' : 'text-white'
                  }`}
                  style={isBooked || full ? undefined : { background: NAVY }}
                >
                  {bookingId === s.id
                    ? <><Loader2 size={13} className="animate-spin" /> …</>
                    : isBooked ? <><CheckCircle2 size={13} /> Réservé</> : 'Réserver'}
                </button>
              </div>
            )
          })}
        </div>
      </main>
    </div>
  )
}
