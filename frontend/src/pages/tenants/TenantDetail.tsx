import { useState, useEffect } from 'react'
import { getErrorMessage } from '@/utils/errors'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Edit, Trash2, ShieldCheck, FileText, Download, CheckCircle2, Circle } from 'lucide-react'
import { tenantsApi } from '@/api/tenants'
import { apiClient } from '@/api/client'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { downloadBlob } from '@/utils/download'
import { TenantForm } from './TenantForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Tenant } from '@/types/tenant'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { formatNir, formatPhoneDisplay } from '@/utils/format'

interface TenantDoc {
  id: string
  entity_id: string
  file_name: string
  label: string | null
  created_at: string
}

const CIVILITY_LABELS: Record<string, string> = { M: 'M.', Mme: 'Mme', Autre: 'Autre' }

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const fetchTenant = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const { data } = await tenantsApi.get(id)
      setTenant(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchTenant() }, [id])

  // Documents transmis au locataire (courriers générés + uploads). La suppression
  // ici les retire aussi de l'espace « Mes documents » du locataire.
  const [docs, setDocs] = useState<TenantDoc[]>([])
  const loadDocs = async () => {
    if (!id) return
    try {
      const { data } = await apiClient.get('/documents', { params: { entity_type: 'tenant', limit: 200 } })
      setDocs((data as TenantDoc[]).filter(d => d.entity_id === id))
    } catch { /* silencieux */ }
  }
  useEffect(() => { loadDocs() }, [id])

  const downloadDoc = async (d: TenantDoc) => {
    try {
      const res = await apiClient.get(`/documents/${d.id}/download`, { responseType: 'blob' })
      downloadBlob(res.data, d.file_name)
    } catch (e: any) {
      alert(getErrorMessage(e, 'Téléchargement impossible'))
    }
  }
  const deleteDoc = async (docId: string) => {
    if (!confirm('Supprimer ce document ? Il sera aussi retiré de l\'espace « Mes documents » du locataire.')) return
    try {
      await apiClient.delete(`/documents/${docId}`)
      loadDocs()
    } catch (e: any) {
      alert(getErrorMessage(e, 'Suppression impossible'))
    }
  }

  // Plans d'apurement (échéanciers suivis)
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  const loadPlans = async () => {
    if (!id) return
    try { const { data } = await apurementApi.listForTenant(id); setPlans(data) } catch { /* silencieux */ }
  }
  useEffect(() => { loadPlans() }, [id])
  const fmtEur = (n: number) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'
  const markPaid = async (planId: string, seq: number, paid: boolean) => {
    try { await apurementApi.markInstallment(planId, seq, paid); loadPlans() }
    catch (e: any) { alert(getErrorMessage(e, 'Mise à jour impossible')) }
  }
  const deletePlan = async (planId: string) => {
    if (!confirm('Supprimer ce plan d\'apurement ?')) return
    try { await apurementApi.remove(planId); loadPlans() }
    catch (e: any) { alert(getErrorMessage(e, 'Suppression impossible')) }
  }
  const downloadPlanPdf = async (p: ApurementPlan) => {
    try { await apurementApi.downloadPdf(p.id, `plan_apurement_${(tenant?.full_name || 'locataire').replace(/\s+/g, '_')}.pdf`) }
    catch (e: any) { alert(getErrorMessage(e, 'Téléchargement impossible')) }
  }
  const todayIso = new Date().toISOString().slice(0, 10)

  const handleDelete = async () => {
    if (!id) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await tenantsApi.delete(id)
      navigate('/tenants')
    } catch (e: any) {
      setDeleteError(
        getErrorMessage(e, "La suppression a échoué. Ce locataire est peut-être rattaché à un contrat.")
      )
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!tenant) return <div className="p-6 text-sm text-red-600">Locataire introuvable</div>

  // Tous les champs sont affichés ; les valeurs vides sont signalées « Non renseigné »
  // (jamais un tiret — convention projet).
  const Field = ({ label, value, full }: { label: string; value: string | null | undefined; full?: boolean }) => (
    <div className={`min-w-0 ${full ? 'col-span-2' : ''}`}>
      <p className="text-xs text-gray-500">{label}</p>
      {value
        ? <p className="text-sm text-gray-900 break-words">{value}</p>
        : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
    </div>
  )

  const birthDate = tenant.birth_date
    ? format(new Date(tenant.birth_date), 'd MMMM yyyy', { locale: fr })
    : null
  const income = tenant.monthly_income != null
    ? `${Number(tenant.monthly_income).toLocaleString('fr-FR')} €`
    : null

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/tenants')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{tenant.full_name}</h1>
            {tenant.user_id && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte locataire lié">
                <ShieldCheck size={11} /> Compte en ligne
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">Fiche locataire</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowEdit(true)}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <Edit size={15} /> Modifier
          </button>
          <button
            onClick={() => setShowDelete(true)}
            className="flex items-center gap-2 px-3 py-2 border border-red-300 text-sm text-red-600 rounded-lg hover:bg-red-50"
          >
            <Trash2 size={15} /> Supprimer
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Identité */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Identité</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Civilité" value={tenant.civility ? CIVILITY_LABELS[tenant.civility] : null} />
            <Field label="Prénom" value={tenant.first_name} />
            <Field label="Nom" value={tenant.last_name} />
            <Field label="Date de naissance" value={birthDate} />
            <Field label="Lieu de naissance" value={tenant.birth_place} />
            <Field label="Numéro de sécurité sociale" value={tenant.national_id ? formatNir(tenant.national_id) : tenant.national_id} />
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Contact</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Email" value={tenant.email} full />
            <Field label="Téléphone" value={formatPhoneDisplay(tenant.phone)} />
          </div>
        </div>

        {/* Situation professionnelle */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Situation professionnelle</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Employeur" value={tenant.employer} />
            <Field label="Tél. employeur" value={formatPhoneDisplay(tenant.employer_phone)} />
            <Field label="Revenu mensuel" value={income} />
            <Field label="Source de revenus" value={tenant.income_source} />
          </div>
        </div>

        {/* Notes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Notes</h2>
          {tenant.notes
            ? <p className="text-sm text-gray-700 whitespace-pre-wrap">{tenant.notes}</p>
            : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
        </div>

        {/* Documents transmis au locataire */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-900 mb-1">Documents transmis au locataire</h2>
          <p className="text-xs text-gray-400 mb-3">
            Les courriers générés (relance, plan d'apurement…) apparaissent dans son espace « Mes documents ». Les supprimer ici les retire aussi de son espace.
          </p>
          {docs.length === 0 ? (
            <p className="text-sm text-gray-300 italic">Aucun document transmis</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {docs.map(d => (
                <li key={d.id} className="flex items-center gap-3 py-2">
                  <FileText size={16} className="text-gray-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 truncate">{d.label || d.file_name}</p>
                    <p className="text-xs text-gray-400">{format(new Date(d.created_at), 'd MMM yyyy', { locale: fr })}</p>
                  </div>
                  <button onClick={() => downloadDoc(d)} title="Télécharger"
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600">
                    <Download size={15} />
                  </button>
                  <button onClick={() => deleteDoc(d.id)} title="Supprimer (retire aussi de l'espace du locataire)"
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600">
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Plans d'apurement (échéanciers suivis) */}
        {plans.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Plans d'apurement</h2>
            <div className="space-y-4">
              {plans.map(p => (
                <div key={p.id} className="border border-gray-100 rounded-lg p-4">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      <span className="text-sm font-medium text-gray-900 truncate">{p.label || "Plan d'apurement"}</span>
                      {p.status === 'completed'
                        ? <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 shrink-0">Terminé</span>
                        : p.overdue
                          ? <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 shrink-0">En retard</span>
                          : <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 shrink-0">En cours</span>}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button onClick={() => downloadPlanPdf(p)} title="Télécharger le PDF"
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600"><Download size={15} /></button>
                      <button onClick={() => deletePlan(p.id)} title="Supprimer le plan"
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600"><Trash2 size={15} /></button>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="bg-gray-50 rounded-lg px-3 py-2"><p className="text-xs text-gray-500">Reste à apurer</p><p className="text-base font-semibold text-gray-900 whitespace-nowrap">{fmtEur(p.remaining)}</p></div>
                    <div className="bg-gray-50 rounded-lg px-3 py-2"><p className="text-xs text-gray-500">Réglé</p><p className="text-base font-semibold text-gray-900 whitespace-nowrap">{fmtEur(p.paid_total)}</p></div>
                    <div className="bg-gray-50 rounded-lg px-3 py-2"><p className="text-xs text-gray-500">Avancement</p><p className="text-base font-semibold text-gray-900">{p.paid_count} / {p.count}</p></div>
                  </div>
                  <ul className="divide-y divide-gray-50">
                    {p.installments.map(inst => {
                      const late = !inst.paid && inst.due_date < todayIso
                      return (
                        <li key={inst.seq} className="flex items-center gap-3 py-2">
                          {inst.paid
                            ? <CheckCircle2 size={18} className="text-green-600 shrink-0" />
                            : <Circle size={18} className={`shrink-0 ${late ? 'text-red-500' : 'text-gray-300'}`} />}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-900">Échéance {inst.seq} · {format(new Date(inst.due_date), 'd MMM yyyy', { locale: fr })}</p>
                            {inst.paid && inst.paid_date
                              ? <p className="text-xs text-gray-400">Réglée le {format(new Date(inst.paid_date), 'd MMM yyyy', { locale: fr })}</p>
                              : late ? <p className="text-xs text-red-500">En retard</p> : null}
                          </div>
                          <span className="text-sm font-medium text-gray-900 whitespace-nowrap">{fmtEur(inst.amount)}</span>
                          <button onClick={() => markPaid(p.id, inst.seq, !inst.paid)}
                            className={`text-xs px-2 py-1 rounded whitespace-nowrap ${inst.paid ? 'text-gray-500 hover:bg-gray-100' : 'bg-green-50 text-green-700 hover:bg-green-100'}`}>
                            {inst.paid ? 'Annuler' : 'Marquer payée'}
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {showEdit && (
        <TenantForm
          tenant={tenant}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchTenant() }}
        />
      )}
      <ConfirmDialog
        isOpen={showDelete}
        onClose={() => { setShowDelete(false); setDeleteError(null) }}
        onConfirm={handleDelete}
        title="Supprimer le locataire"
        message={deleteError
          ? `⚠️ ${deleteError}`
          : "Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce locataire ?"}
        confirmLabel={deleteError ? 'Réessayer' : 'Supprimer'}
        isLoading={isDeleting}
      />
    </div>
  )
}
