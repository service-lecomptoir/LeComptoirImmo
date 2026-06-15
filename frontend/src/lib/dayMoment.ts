import { Moon, Sunrise, CloudSun, Sunset } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface DayMoment {
  Icon: LucideIcon
  color: string   // couleur de l'icône
  bg: string      // fond de la pastille
  label: string   // salutation selon le moment
}

/** Renvoie l'icône + les couleurs + la salutation selon l'heure de la journée
 *  (aube / après-midi soleil-nuage / crépuscule / nuit). Source unique. */
export function getDayMoment(d: Date = new Date()): DayMoment {
  const h = d.getHours()
  if (h < 7) return { Icon: Moon, color: '#6366F1', bg: '#EEF2FF', label: 'Bonne nuit' }
  if (h < 12) return { Icon: Sunrise, color: '#F59E0B', bg: '#FFF7ED', label: 'Bonne matinée' }
  if (h < 18) return { Icon: CloudSun, color: '#F07800', bg: '#FFF7ED', label: 'Bel après-midi' }
  if (h < 22) return { Icon: Sunset, color: '#EA580C', bg: '#FFF1F0', label: 'Bonne soirée' }
  return { Icon: Moon, color: '#6366F1', bg: '#EEF2FF', label: 'Bonne nuit' }
}

/** Date longue en français : « lundi 15 juin 2026 ». */
export const formatLongDate = (d: Date = new Date()): string =>
  d.toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
