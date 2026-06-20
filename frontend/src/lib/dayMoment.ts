import { Moon, Sunrise, CloudSun, Sunset } from 'lucide-react'
import { BRAND } from '@/lib/brand'
import type { LucideIcon } from 'lucide-react'

export interface DayMoment {
  Icon: LucideIcon
  color: string   // couleur de l'icône
  bg: string      // fond de la pastille
  label: string   // salutation selon le moment
}

/** Fuseau horaire de l'utilisateur, déduit de la localisation de son appareil
 *  (réglages système/navigateur), ex. « Europe/Paris ». Sans demande de
 *  permission : c'est la géolocalisation « douce » standard côté web. */
export function userTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Paris'
  } catch {
    return 'Europe/Paris'
  }
}

/** Heure (0-23) à l'endroit où se trouve l'utilisateur (son fuseau). */
function localHour(d: Date): number {
  const s = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit', hour12: false, timeZone: userTimeZone(),
  }).format(d)
  return parseInt(s, 10) % 24
}

/** Renvoie l'icône + les couleurs + la salutation selon le moment de la journée
 *  (aube / après-midi soleil-nuage / crépuscule / nuit), calculé sur le fuseau
 *  horaire de l'utilisateur (sa géolocalisation). Source unique. */
export function getDayMoment(d: Date = new Date()): DayMoment {
  const h = localHour(d)
  if (h < 7) return { Icon: Moon, color: '#6366F1', bg: '#EEF2FF', label: 'Bonne nuit' }
  if (h < 12) return { Icon: Sunrise, color: '#F59E0B', bg: '#FFF7ED', label: 'Bonne matinée' }
  if (h < 18) return { Icon: CloudSun, color: BRAND.orange, bg: '#FFF7ED', label: 'Bel après-midi' }
  if (h < 22) return { Icon: Sunset, color: '#EA580C', bg: '#FFF1F0', label: 'Bonne soirée' }
  return { Icon: Moon, color: '#6366F1', bg: '#EEF2FF', label: 'Bonne nuit' }
}

/** Date longue en français (« lundi 15 juin 2026 »), au fuseau de l'utilisateur. */
export const formatLongDate = (d: Date = new Date()): string =>
  d.toLocaleDateString('fr-FR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    timeZone: userTimeZone(),
  })
