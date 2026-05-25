import { useEffect, useState, useCallback, type ReactElement } from 'react'
import { Bell, CheckCheck, RefreshCw, AlertCircle, Info, Clock, BellOff } from 'lucide-react'
import { notificationsApi } from '@/api/notifications'
import { useAuthStore } from '@/store/authStore'
import type { Notification, NotificationPriority } from '@/types/notification'
import { NOTIFICATION_TYPE_LABELS, NOTIFICATION_PRIORITY_VARIANTS } from '@/types/notification'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

const PRIORITY_ICON: Record<NotificationPriority, ReactElement> = {
  urgent: <AlertCircle size={16} className="text-red-500" />,
  high: <AlertCircle size={16} className="text-red-400" />,
  normal: <Info size={16} className="text-blue-500" />,
  low: <Clock size={16} className="text-gray-400" />,
}

const PRIORITY_BADGE: Record<string, string> = {
  red: 'bg-red-100 text-red-700',
  yellow: 'bg-yellow-100 text-yellow-700',
  blue: 'bg-blue-100 text-blue-700',
  gray: 'bg-gray-100 text-gray-600',
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function NotificationList() {
  const { user } = useAuthStore()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [totalAll, setTotalAll] = useState(0)
  const [loading, setLoading] = useState(true)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [markingAll, setMarkingAll] = useState(false)
  const [generatingAlerts, setGeneratingAlerts] = useState(false)
  const [alertMsg, setAlertMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await notificationsApi.list({ unread_only: unreadOnly, limit: 100 })
      setNotifications(data.items)
      setUnreadCount(data.unread_count)
      if (!unreadOnly) setTotalAll(data.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [unreadOnly])

  useEffect(() => { load() }, [load])

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      )
      setUnreadCount((c) => Math.max(0, c - 1))
      window.dispatchEvent(new Event('notification-read'))
    } catch { /* ignore */ }
  }

  const handleMarkAllRead = async () => {
    setMarkingAll(true)
    try {
      await notificationsApi.markAllRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() })))
      setUnreadCount(0)
      window.dispatchEvent(new Event('notification-read'))
    } catch { /* ignore */ }
    setMarkingAll(false)
  }

  const handleGenerateAlerts = async () => {
    setGeneratingAlerts(true)
    setAlertMsg(null)
    try {
      const { data } = await notificationsApi.generateAlerts()
      setAlertMsg(
        `Alertes générées : ${data.late_payment_alerts} retard(s), ${data.expiring_lease_alerts} expiration(s)`
      )
      await load()
    } catch {
      setAlertMsg('Erreur lors de la génération des alertes.')
    }
    setGeneratingAlerts(false)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-gray-700" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
            <p className="text-sm text-gray-500">
              {unreadCount > 0 ? `${unreadCount} non lue${unreadCount > 1 ? 's' : ''}` : 'Tout est lu'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Admin: generate alerts button */}
          {user?.role === 'admin' && (
            <button
              onClick={handleGenerateAlerts}
              disabled={generatingAlerts}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-orange-50 text-orange-700 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={generatingAlerts ? 'animate-spin' : ''} />
              Générer alertes
            </button>
          )}
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={markingAll}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
            >
              <CheckCheck size={14} />
              Tout marquer comme lu
            </button>
          )}
        </div>
      </div>

      {/* Alert message */}
      {alertMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          {alertMsg}
        </div>
      )}

      {/* ── Filter ── */}
      <div className="mb-4 flex items-center gap-2">
        <button
          onClick={() => setUnreadOnly(false)}
          className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
            !unreadOnly ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Toutes ({totalAll})
        </button>
        <button
          onClick={() => setUnreadOnly(true)}
          className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
            unreadOnly ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Non lues ({unreadCount})
        </button>
      </div>

      {/* ── List ── */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <BellOff size={48} className="mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">Aucune notification</p>
          <p className="text-sm mt-1">
            {unreadOnly ? 'Toutes vos notifications sont lues.' : "Vous n'avez aucune notification."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((notif) => {
            const variant = NOTIFICATION_PRIORITY_VARIANTS[notif.priority]
            return (
              <div
                key={notif.id}
                className={`flex items-start gap-4 p-4 rounded-xl border transition-colors ${
                  notif.is_read
                    ? 'bg-white border-gray-200'
                    : 'bg-blue-50 border-blue-200'
                }`}
              >
                {/* Priority icon */}
                <div className="mt-0.5 flex-shrink-0">
                  {PRIORITY_ICON[notif.priority]}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-sm text-gray-900">{notif.title}</span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${PRIORITY_BADGE[variant]}`}
                    >
                      {NOTIFICATION_TYPE_LABELS[notif.notification_type]}
                    </span>
                    {!notif.is_read && (
                      <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">{notif.message}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatDate(notif.created_at)}</p>
                </div>

                {/* Mark read button */}
                {!notif.is_read && (
                  <button
                    onClick={() => handleMarkRead(notif.id)}
                    className="flex-shrink-0 text-xs text-blue-600 hover:text-blue-800 hover:underline whitespace-nowrap"
                  >
                    Marquer lu
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
