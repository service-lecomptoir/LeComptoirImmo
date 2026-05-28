import { useState, useEffect } from 'react'
import { Save, Landmark, KeyRound, Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/api/client'
import { ownersApi } from '@/api/owners'

export default function MonProfil() {
  const { user, fetchMe } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [address, setAddress] = useState(user?.address ?? '')
  const [iban, setIban] = useState('')
  const [bic, setBic] = useState('')
  const [bankHolder, setBankHolder] = useState('')
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  // Mot de passe
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [pwdSaving, setPwdSaving] = useState(false)
  const [pwdMsg, setPwdMsg] = useState<string | null>(null)
  const [pwdErr, setPwdErr] = useState<string | null>(null)

  // Le RIB n'est utile que pour les comptes qui encaissent le loyer (propriétaire / GP).
  // Source UNIQUE des coordonnées de règlement : la fiche propriétaire (entité Owner).
  const showRib = user?.role === 'proprietaire' || user?.role === 'gestionnaire_proprio'
  // Le locataire n'a pas d'adresse propre (son adresse = le bien loué) → champ masqué.
  const isLocataire = user?.role === 'locataire'

  // Charge la fiche propriétaire liée au compte : coordonnées de règlement + RIB.
  useEffect(() => {
    if (!showRib) return
    let cancelled = false
    ownersApi.me()
      .then(r => {
        if (cancelled || !r.data) return
        const o = r.data
        setOwnerId(o.id)
        setPhone(o.phone ?? '')
        setAddress(o.address ?? '')
        setIban(o.iban ?? '')
        setBic(o.bic ?? '')
        setBankHolder(o.bank_holder ?? '')
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [showRib])

  const save = async () => {
    setSaving(true); setMsg(null); setErr(null)
    try {
      // Compte : nom + email (identifiant). Pour un gestionnaire/admin, le téléphone
      // et l'adresse (agence) restent sur le compte.
      await apiClient.patch('/users/me', {
        full_name: fullName,
        email: email.trim() || undefined,
        ...(showRib ? {} : { phone: phone || null, ...(isLocataire ? {} : { address: address || null }) }),
      })
      // Propriétaire / GP : coordonnées de règlement + RIB → fiche propriétaire.
      if (showRib && ownerId) {
        await ownersApi.updateMe({
          phone: phone || null,
          address: address || null,
          iban: iban ? iban.replace(/\s+/g, '').toUpperCase() : null,
          bic: bic ? bic.replace(/\s+/g, '').toUpperCase() : null,
          bank_holder: bankHolder || null,
        } as any)
      }
      await fetchMe()
      setMsg('Profil mis à jour.')
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Erreur lors de l'enregistrement")
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async () => {
    if (!currentPassword || !newPassword) { setPwdErr('Remplissez les deux champs.'); return }
    if (newPassword.length < 8) { setPwdErr('Le nouveau mot de passe doit contenir au moins 8 caractères.'); return }
    setPwdSaving(true); setPwdMsg(null); setPwdErr(null)
    try {
      await apiClient.patch('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setPwdMsg('Mot de passe modifié.')
      setCurrentPassword(''); setNewPassword('')
    } catch (e: any) {
      setPwdErr(e?.response?.data?.detail || 'Mot de passe actuel incorrect.')
    } finally {
      setPwdSaving(false)
    }
  }

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-600 mb-1'

  return (
    <div className="max-w-2xl p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes informations</h1>
        <p className="text-gray-500 text-sm mt-1">
          Vos informations et coordonnées — utilisées dans la barre latérale et sur vos documents.
        </p>
      </div>

      {/* ── Informations & coordonnées ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        {msg && <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">{msg}</div>}
        {err && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{err}</div>}
        <div>
          <label className={lbl}>Nom complet</label>
          <input className={inp} value={fullName} onChange={e => setFullName(e.target.value)} />
        </div>
        <div>
          <label className={lbl}>Email (identifiant de connexion)</label>
          <input className={inp} type="email" value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <div>
          <label className={lbl}>Téléphone</label>
          <input className={inp} value={phone} onChange={e => setPhone(e.target.value)} placeholder="06 12 34 56 78" />
        </div>
        {!isLocataire && (
          <div>
            <label className={lbl}>Adresse</label>
            <textarea className={`${inp} resize-none`} rows={2} value={address}
              onChange={e => setAddress(e.target.value)} placeholder="12 rue de la République, 75001 Paris" />
          </div>
        )}

        {/* ── Coordonnées bancaires (RIB) — propriétaire / GP ── */}
        {showRib && (
          <div className="pt-4 mt-2 border-t border-gray-100 space-y-4">
            <div className="flex items-center gap-2">
              <Landmark size={16} className="text-blue-600" />
              <h2 className="text-sm font-semibold text-gray-900">Coordonnées bancaires (RIB)</h2>
            </div>
            <p className="text-xs text-gray-500 -mt-2">
              Ce RIB est communiqué à vos locataires pour le règlement du loyer par virement.
            </p>
            <div>
              <label className={lbl}>Titulaire du compte</label>
              <input className={inp} value={bankHolder} onChange={e => setBankHolder(e.target.value)}
                placeholder="Nom figurant sur le compte" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className={lbl}>IBAN</label>
                <input className={`${inp} font-mono`} value={iban} onChange={e => setIban(e.target.value)}
                  placeholder="FR76 3000 4028 3798 7654 3210 943" />
              </div>
              <div>
                <label className={lbl}>BIC</label>
                <input className={`${inp} font-mono`} value={bic} onChange={e => setBic(e.target.value)}
                  placeholder="BNPAFRPPXXX" />
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <button onClick={save} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
            <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </div>

      {/* ── Sécurité : mot de passe ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 mt-5">
        <div className="flex items-center gap-2">
          <KeyRound size={16} className="text-gray-600" />
          <h2 className="text-sm font-semibold text-gray-900">Changer le mot de passe</h2>
        </div>
        {pwdMsg && <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">{pwdMsg}</div>}
        {pwdErr && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{pwdErr}</div>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={lbl}>Mot de passe actuel</label>
            <div className="relative">
              <input className={`${inp} pr-9`} type={showPwd ? 'text' : 'password'} value={currentPassword}
                onChange={e => setCurrentPassword(e.target.value)} placeholder="••••••••" />
              <button type="button" onClick={() => setShowPwd(v => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <div>
            <label className={lbl}>Nouveau mot de passe</label>
            <input className={inp} type={showPwd ? 'text' : 'password'} value={newPassword}
              onChange={e => setNewPassword(e.target.value)} placeholder="8 caractères min." />
          </div>
        </div>
        <div className="flex justify-end">
          <button onClick={changePassword} disabled={pwdSaving || !currentPassword || !newPassword}
            className="px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 disabled:opacity-50">
            {pwdSaving ? 'Modification…' : 'Modifier le mot de passe'}
          </button>
        </div>
      </div>
    </div>
  )
}
