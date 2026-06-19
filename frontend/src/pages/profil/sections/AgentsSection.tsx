import { useEffect, useState } from 'react'
import { Bot, Check, Unlink, AlertTriangle, Send, Copy, RefreshCw } from 'lucide-react'
import { agentsApi, type TelegramStatus } from '@/api/agents'
import { useFeaturesStore } from '@/store/featuresStore'
import { isFeatureAllowed } from '@/lib/features'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

/** Agents IA (Telegram) — option de plan « agents_ia ». Section autonome :
 *  ne rend rien si la fonctionnalité n'est pas autorisée. */
export default function AgentsSection() {
  const { features } = useFeaturesStore()
  const allowed = isFeatureAllowed(features, 'agents_ia')
  const [tgStatus, setTgStatus] = useState<TelegramStatus | null>(null)
  const [tgCode, setTgCode] = useState<string | null>(null)
  const [tgDeepLink, setTgDeepLink] = useState<string | null>(null)
  const [tgBusy, setTgBusy] = useState(false)
  const [tgCopied, setTgCopied] = useState(false)

  useEffect(() => {
    if (!allowed) return
    agentsApi.telegramStatus().then(r => setTgStatus(r.data)).catch(() => {})
  }, [allowed])

  const generateTgCode = async () => {
    setTgBusy(true)
    try {
      const { data } = await agentsApi.generateLinkCode()
      setTgCode(data.code)
      setTgDeepLink(data.deep_link)
      setTgStatus({ linked: data.linked, bot_username: data.bot_username, enabled: data.enabled })
    } catch (e) {
      toast.error(getErrorMessage(e, 'Génération du code impossible'))
    } finally {
      setTgBusy(false)
    }
  }

  const copyTgCommand = async () => {
    if (!tgCode) return
    try {
      await navigator.clipboard.writeText(`/start ${tgCode}`)
      setTgCopied(true)
      setTimeout(() => setTgCopied(false), 2000)
    } catch {
      toast.error('Copie impossible')
    }
  }

  const unlinkTg = async () => {
    setTgBusy(true)
    try {
      await agentsApi.unlink()
      setTgCode(null); setTgDeepLink(null)
      setTgStatus(s => s ? { ...s, linked: false } : s)
      toast.success('Telegram délié')
    } catch {
      toast.error('Suppression impossible')
    } finally {
      setTgBusy(false)
    }
  }

  if (!allowed) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Bot size={16} className="text-blue-600" />
        <h2 className="text-sm font-semibold text-gray-900">Agents IA</h2>
      </div>
      <p className="text-xs text-gray-500 -mt-2">
        Votre équipe d'agents répond à vos questions, vous envoie un point du jour, et peut
        <b> exécuter des actions</b> (générer un avis ou une quittance, enregistrer un paiement,
        ouvrir une démarche) : avec confirmation, directement sur Telegram (gratuit).
      </p>

      <ul className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { emoji: '📊', name: 'Agent Comptable', desc: 'Impayés et ancienneté, encaissements, taux de recouvrement, échéances à venir, quittances.' },
          { emoji: '🛡️', name: 'Agent Sécurité', desc: 'Démarches et incidents, signalements de la résidence (bruit, sécurité, ascenseur…), voisinage.' },
          { emoji: '🗂️', name: 'Agent Administratif', desc: 'Biens occupés/vacants, contrats, baux à échéance, candidatures et visites, entretiens.' },
        ].map(a => (
          <li key={a.name} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div className="text-lg">{a.emoji}</div>
            <div className="text-sm font-semibold text-gray-800 mt-1">{a.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">{a.desc}</div>
          </li>
        ))}
      </ul>

      {tgStatus?.linked ? (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <div className="flex items-start gap-2 text-sm text-emerald-800 min-w-0">
            <Check size={15} className="text-emerald-600 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <p>
                Telegram est connecté{tgStatus.bot_username ? <> à <span className="font-semibold">@{tgStatus.bot_username}</span></> : null}.
              </p>
              <p className="mt-1 text-emerald-700">
                Écrivez <span className="font-semibold">« aide »</span> au bot pour commencer. Vous recevez aussi
                chaque matin un <span className="font-semibold">point du jour</span>.
              </p>
            </div>
          </div>
          <button onClick={unlinkTg} disabled={tgBusy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 whitespace-nowrap shrink-0">
            <Unlink size={14} /> Délier
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {!tgStatus?.enabled && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-800">
                Le canal Telegram n'est pas encore activé sur la plateforme. Vous pouvez préparer votre code de liaison ;
                la connexion deviendra effective dès l'activation.
              </p>
            </div>
          )}
          {!tgCode ? (
            <button onClick={generateTgCode} disabled={tgBusy}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
              <Send size={15} /> {tgBusy ? 'Génération…' : 'Connecter Telegram'}
            </button>
          ) : (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
              <p className="text-sm text-gray-700">
                {tgDeepLink ? <>1. Ouvrez le bot puis envoyez la commande ci-dessous.</>
                            : <>1. Ouvrez votre bot Telegram et envoyez-lui la commande ci-dessous.</>}
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm font-mono text-gray-800 select-all">
                  /start {tgCode}
                </code>
                <button onClick={copyTgCommand} title="Copier"
                  className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-white whitespace-nowrap">
                  {tgCopied ? <Check size={15} className="text-emerald-600" /> : <Copy size={15} />}
                  {tgCopied ? 'Copié' : 'Copier'}
                </button>
              </div>
              {tgDeepLink && (
                <a href={tgDeepLink} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
                  <Send size={15} /> Ouvrir Telegram et lier automatiquement
                </a>
              )}
              <button onClick={generateTgCode} disabled={tgBusy}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700">
                <RefreshCw size={12} /> Générer un nouveau code
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
