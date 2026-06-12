import { useState, useEffect, useRef } from 'react'
import { getErrorMessage } from '@/utils/errors'
import { Save, Landmark, KeyRound, Eye, EyeOff, AtSign, Plus, X, AlertTriangle, Image as ImageIcon, Trash2, UploadCloud, Bot, Send, Copy, Check, RefreshCw, Unlink } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
import { PhoneInput } from '@/components/common/PhoneInput'
import AddressAutocomplete from '@/components/common/AddressAutocomplete'
import CommuneAutocomplete from '@/components/common/CommuneAutocomplete'
import { TypedSignature } from '@/components/common/TypedSignature'
import { apiClient } from '@/api/client'
import { ownersApi } from '@/api/owners'
import { usersApi, type EmailDomain } from '@/api/users'
import { agentsApi, type TelegramStatus } from '@/api/agents'
import { useFeaturesStore } from '@/store/featuresStore'
import { isFeatureAllowed } from '@/lib/features'
import { toast } from '@/store/toast'

function splitName(s?: string | null): { first: string; last: string } {
  const parts = (s ?? '').trim().split(/\s+/).filter(Boolean)
  const first = parts.shift() ?? ''
  return { first, last: parts.join(' ') }
}
const joinName = (first: string, last: string) => `${first.trim()} ${last.trim()}`.trim()

export default function MonProfil() {
  const { user, fetchMe } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  // Prénom/Nom (recombinés dans full_name pour les non-gestionnaires, owner_full_name pour les gestionnaires)
  const [firstName, setFirstName] = useState(splitName(user?.full_name).first)
  const [lastName, setLastName] = useState(splitName(user?.full_name).last)
  const [ownerFirstName, setOwnerFirstName] = useState(splitName(user?.owner_full_name).first)
  const [ownerLastName, setOwnerLastName] = useState(splitName(user?.owner_full_name).last)
  const [ownerCompany, setOwnerCompany] = useState(user?.owner_company ?? '')
  const [ownerNationalId, setOwnerNationalId] = useState(user?.owner_national_id ?? '')
  // Type d'identité bailleur : 'personne' (Prénom/Nom) ou 'societe' (Société/SCI + SIRET).
  const [ownerKind, setOwnerKind] = useState<'personne' | 'societe'>(user?.owner_kind === 'societe' ? 'societe' : 'personne')
  const [email, setEmail] = useState(user?.email ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [address, setAddress] = useState(user?.address ?? '')
  const [zipCode, setZipCode] = useState(user?.zip_code ?? '')
  const [city, setCity] = useState(user?.city ?? '')
  const [country, setCountry] = useState(user?.country ?? '')
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
  // Domaines e-mail autorisés : pour les comptes qui envoient des communications.
  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio'
  const isGP = user?.role === 'gestionnaire_proprio'
  const [domains, setDomains] = useState<EmailDomain[]>([])
  const [newDomain, setNewDomain] = useState('')
  const [domainErr, setDomainErr] = useState<string | null>(null)
  const [domainBusy, setDomainBusy] = useState(false)

  // Logo du gestionnaire (en-tête des documents).
  const logoInputRef = useRef<HTMLInputElement>(null)
  const [logoBusy, setLogoBusy] = useState(false)

  // Signature numérique (data-URL PNG) apposée en bas des courriers générés.
  // undefined = inchangée ; null = à supprimer ; string = nouvelle signature.
  const [signature, setSignature] = useState<string | null | undefined>(undefined)

  // ── Agents IA (Telegram) — option de plan « agents_ia » ──
  const { features } = useFeaturesStore()
  const showAgents = isManager && isFeatureAllowed(features, 'agents_ia')
  const [tgStatus, setTgStatus] = useState<TelegramStatus | null>(null)
  const [tgCode, setTgCode] = useState<string | null>(null)
  const [tgDeepLink, setTgDeepLink] = useState<string | null>(null)
  const [tgBusy, setTgBusy] = useState(false)
  const [tgCopied, setTgCopied] = useState(false)

  useEffect(() => {
    if (!showAgents) return
    agentsApi.telegramStatus().then(r => setTgStatus(r.data)).catch(() => {})
  }, [showAgents])

  const generateTgCode = async () => {
    setTgBusy(true)
    try {
      const { data } = await agentsApi.generateLinkCode()
      setTgCode(data.code)
      setTgDeepLink(data.deep_link)
      setTgStatus({
        linked: data.linked,
        bot_username: data.bot_username,
        enabled: data.enabled,
      })
    } catch (e: any) {
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

  const handleLogoFile = async (file: File) => {
    if (!file.type.startsWith('image/')) { toast.error('Choisissez une image (PNG, JPG, SVG, WebP).'); return }
    setLogoBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      await apiClient.post('/auth/me/logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      await fetchMe()
      toast.success('Logo mis à jour')
    } catch (e: any) {
      toast.error(getErrorMessage(e, "Échec du téléversement du logo"))
    } finally {
      setLogoBusy(false)
      if (logoInputRef.current) logoInputRef.current.value = ''
    }
  }

  const removeLogo = async () => {
    setLogoBusy(true)
    try {
      await apiClient.delete('/auth/me/logo')
      await fetchMe()
      toast.success('Logo supprimé')
    } catch {
      toast.error('Suppression du logo impossible')
    } finally {
      setLogoBusy(false)
    }
  }

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
        setZipCode(o.zip_code ?? '')
        setCity(o.city ?? '')
        setCountry(o.country ?? '')
        setIban(o.iban ?? '')
        setBic(o.bic ?? '')
        setBankHolder(o.bank_holder ?? '')
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [showRib])

  useEffect(() => {
    if (!isManager) return
    usersApi.listEmailDomains().then(r => setDomains(r.data)).catch(() => {})
  }, [isManager])

  const addDomain = async () => {
    if (!newDomain.trim()) return
    setDomainBusy(true); setDomainErr(null)
    try {
      const { data } = await usersApi.addEmailDomain(newDomain.trim())
      setDomains(prev => prev.some(d => d.id === data.id) ? prev : [...prev, data])
      setNewDomain('')
      toast.success('Domaine ajouté')
    } catch (e: any) {
      setDomainErr(getErrorMessage(e, "Impossible d'ajouter ce domaine"))
    } finally {
      setDomainBusy(false)
    }
  }

  const removeDomain = async (id: string) => {
    try {
      await usersApi.removeEmailDomain(id)
      setDomains(prev => prev.filter(d => d.id !== id))
      toast.success('Domaine supprimé')
    } catch {
      toast.error('Suppression impossible')
    }
  }

  const save = async () => {
    setSaving(true); setMsg(null); setErr(null)
    try {
      // Compte : nom + email (identifiant) + téléphone + adresse.
      // L'adresse et le téléphone sont aussi écrits sur le compte (pas seulement
      // sur la fiche propriétaire) pour que les documents générés et le bloc
      // « Émetteur » de l'éditeur de templates restent à jour, quel que soit le
      // rôle. Le locataire est exclu de l'adresse (son adresse = le bien loué).
      // Gestionnaire : full_name = nom de COMPTE (champ unique) ; le nom du propriétaire
      // est saisi en Prénom/Nom → recombiné dans owner_full_name.
      // Autres rôles : le nom de la personne est saisi en Prénom/Nom → recombiné dans full_name.
      await apiClient.patch('/users/me', {
        full_name: isManager ? fullName : joinName(firstName, lastName),
        email: email.trim() || undefined,
        phone: phone || null,
        ...(isLocataire ? {} : {
          address: address || null,
          zip_code: zipCode || null,
          city: city || null,
          country: country || null,
        }),
        ...(isManager ? {
          // Mandataire = société par nature ; GP = selon le type choisi (personne/société).
          // Le nom des documents dérive côté serveur du type (owner_kind).
          owner_kind: isGP ? ownerKind : 'societe',
          owner_full_name: (isGP && ownerKind === 'personne')
            ? (joinName(ownerFirstName, ownerLastName) || null) : null,
          owner_company: ownerCompany.trim() || null,
          owner_national_id: ownerNationalId.trim() || null,
          // Signature : envoyée seulement si modifiée (string = nouvelle, null = supprimée).
          ...(signature !== undefined ? { signature } : {}),
        } : {}),
      })
      // Propriétaire / GP : coordonnées de règlement + RIB → fiche propriétaire.
      if (showRib && ownerId) {
        await ownersApi.updateMe({
          phone: phone || null,
          address: address || null,
          zip_code: zipCode || null,
          city: city || null,
          country: country || null,
          iban: iban ? iban.replace(/\s+/g, '').toUpperCase() : null,
          bic: bic ? bic.replace(/\s+/g, '').toUpperCase() : null,
          bank_holder: bankHolder || null,
        } as any)
      }
      await fetchMe()
      setMsg('Profil mis à jour.')
    } catch (e: any) {
      setErr(getErrorMessage(e, "Erreur lors de l'enregistrement"))
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
      setPwdErr(getErrorMessage(e, 'Mot de passe actuel incorrect.'))
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
          Vos informations et coordonnées : utilisées dans la barre latérale et sur vos documents.
        </p>
      </div>

      {/* ── Informations & coordonnées ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        {msg && <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">{msg}</div>}
        {err && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{err}</div>}
        {isManager ? (
          <div>
            <label className={lbl}>Nom de compte</label>
            <input className={inp} value={fullName} onChange={e => setFullName(e.target.value)} />
            <p className="text-xs text-gray-400 mt-1">Affiché dans l'application et sur la plupart des documents.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className={lbl}>Prénom</label>
              <input className={inp} value={firstName} onChange={e => setFirstName(e.target.value)} />
            </div>
            <div>
              <label className={lbl}>Nom</label>
              <input className={inp} value={lastName} onChange={e => setLastName(e.target.value)} />
            </div>
          </div>
        )}
        {/* Identité bailleur. Mandataire = société/SIREN (ce n'est pas un propriétaire).
            GP = choix personne (Prénom/Nom) OU société/SCI + SIREN. Le nom utilisé sur
            les documents (bail, attestations) dérive de ce choix. */}
        {isManager && (
          <div>
            <label className={lbl}>{isGP ? 'Propriétaire (bailleur)' : 'Société (mandataire)'}</label>
            {/* Le GP choisit son type d'identité ; le mandataire est une société par nature. */}
            {isGP && (
              <div className="grid grid-cols-2 gap-2 mb-3">
                <button type="button" onClick={() => setOwnerKind('personne')}
                  className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${ownerKind === 'personne' ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  Personne (Prénom / Nom)
                </button>
                <button type="button" onClick={() => setOwnerKind('societe')}
                  className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${ownerKind === 'societe' ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  Société / SCI
                </button>
              </div>
            )}
            {isGP && ownerKind === 'personne' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={lbl}>Prénom</label>
                  <input className={inp} value={ownerFirstName} onChange={e => setOwnerFirstName(e.target.value)} />
                </div>
                <div>
                  <label className={lbl}>Nom</label>
                  <input className={inp} value={ownerLastName} onChange={e => setOwnerLastName(e.target.value)} />
                </div>
              </div>
            )}
            {(!isGP || ownerKind === 'societe') && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={lbl}>Raison sociale</label>
                  <input className={inp} value={ownerCompany} onChange={e => setOwnerCompany(e.target.value)} placeholder="Raison sociale" />
                </div>
                <div>
                  <label className={lbl}>SIREN / SIRET</label>
                  <input className={inp} value={ownerNationalId} onChange={e => setOwnerNationalId(e.target.value)} placeholder="123 456 789" />
                </div>
              </div>
            )}
            <p className="text-xs text-gray-400 mt-1">Utilisé comme bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant.</p>
          </div>
        )}
        <div>
          <label className={lbl}>Email (identifiant de connexion)</label>
          <input className={inp} type="email" value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <div>
          <label className={lbl}>Téléphone</label>
          <PhoneInput value={phone} onChange={setPhone} inputClassName={inp} />
        </div>
        {!isLocataire && (
          <div className="space-y-3">
            <div>
              <label className={lbl}>Adresse</label>
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onSelect={({ street, postcode, city: c }) => {
                  setAddress(street)
                  if (postcode) setZipCode(postcode)
                  if (c) setCity(c)
                }}
                className={inp}
                placeholder="12 rue de la République"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className={lbl}>Code postal</label>
                <CommuneAutocomplete
                  value={zipCode}
                  onChange={setZipCode}
                  onSelect={({ zip, city: c }) => { setZipCode(zip); setCity(c) }}
                  display="postcode"
                  className={inp}
                  placeholder="ex. 75001"
                />
              </div>
              <div>
                <label className={lbl}>Ville</label>
                <CommuneAutocomplete
                  value={city}
                  onChange={setCity}
                  onSelect={({ zip, city: c }) => { setZipCode(zip); setCity(c) }}
                  display="city"
                  className={inp}
                  placeholder="ex. Paris"
                />
              </div>
              <div>
                <label className={lbl}>Pays</label>
                <input className={inp} value={country} onChange={e => setCountry(e.target.value)} placeholder="France" />
              </div>
            </div>
          </div>
        )}

        {/* ── Logo (affiché en en-tête des documents) ── */}
        {isManager && (
          <div>
            <label className={lbl}>Logo</label>
            <div className="flex items-center gap-4">
              <div className="w-40 h-20 shrink-0 rounded-lg border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center overflow-hidden">
                {user?.logo_url ? (
                  <img src={`${API_BASE}${user.logo_url}`} alt="logo" className="max-w-full max-h-full object-contain" />
                ) : (
                  <ImageIcon size={22} className="text-gray-300" />
                )}
              </div>
              <div className="flex flex-col gap-2">
                <input ref={logoInputRef} type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp"
                  className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) handleLogoFile(f) }} />
                <button type="button" onClick={() => logoInputRef.current?.click()} disabled={logoBusy}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">
                  <UploadCloud size={15} /> {logoBusy ? 'Envoi…' : (user?.logo_url ? 'Remplacer le logo' : 'Téléverser un logo')}
                </button>
                {user?.logo_url && (
                  <button type="button" onClick={removeLogo} disabled={logoBusy}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50">
                    <Trash2 size={15} /> Supprimer
                  </button>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Apparaît en haut à gauche de vos documents (avis d'échéance…). Format conseillé : PNG/JPG, ~170×64 px.
              S'il n'y a pas de logo, l'emplacement reste vide.
            </p>
          </div>
        )}

        {/* ── Signature numérique (apposée au bas des courriers générés) ── */}
        {isManager && (
          <div>
            <label className={lbl}>Signature</label>
            <TypedSignature
              value={signature !== undefined ? signature : (user?.signature ?? null)}
              onChange={setSignature}
              defaultText={(isManager ? (ownerKind === 'personne' ? joinName(ownerFirstName, ownerLastName) : ownerCompany) : '') || fullName || ''}
            />
            <p className="text-xs text-gray-400 mt-1">
              Tapez votre nom et choisissez un style d'écriture. Apposée en bas de vos courriers
              (lettre de relance, plan d'apurement…). Pensez à cliquer sur « Enregistrer » ci-dessous pour la sauvegarder.
            </p>
          </div>
        )}

        {/* ── Coordonnées bancaires (RIB) : propriétaire / GP ── */}
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

      {/* ── Domaines e-mail autorisés (gestionnaires) ── */}
      {isManager && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 mt-5">
          <div className="flex items-center gap-2">
            <AtSign size={16} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Domaines e-mail autorisés</h2>
          </div>
          <p className="text-xs text-gray-500 -mt-2">
            Ajoutez votre nom de domaine pour envoyer les communications depuis ce domaine.
          </p>
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800">
              Attention, il n'est pas possible d'activer l'envoi depuis un nom de domaine d'un fournisseur
              public (p. ex. : @gmail.com, @hotmail.com, @yahoo.com, etc.).
            </p>
          </div>

          {domains.length > 0 && (
            <ul className="space-y-2">
              {domains.map(d => (
                <li key={d.id} className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2">
                  <span className="text-sm font-medium text-gray-800">{d.domain}</span>
                  <button onClick={() => removeDomain(d.id)} title="Supprimer"
                    className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors">
                    <X size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {domainErr && <p className="text-xs text-red-600">{domainErr}</p>}

          <div className="flex gap-2">
            <input
              className={inp}
              value={newDomain}
              onChange={e => setNewDomain(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addDomain() } }}
              placeholder="mon-agence.fr"
            />
            <button onClick={addDomain} disabled={domainBusy || !newDomain.trim()}
              className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
              <Plus size={15} /> Ajouter un domaine
            </button>
          </div>
        </div>
      )}

      {/* ── Agents IA (Telegram) ── */}
      {showAgents && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 mt-5">
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Agents IA</h2>
          </div>
          <p className="text-xs text-gray-500 -mt-2">
            Votre équipe d'agents répond à vos questions, vous envoie un point du jour, et peut
            <b> exécuter des actions</b> (générer un avis ou une quittance, enregistrer un paiement,
            ouvrir une démarche) : avec confirmation : directement sur Telegram (gratuit).
          </p>

          {/* Présentation des 3 agents */}
          <ul className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { emoji: '📊', name: 'Agent Comptable', desc: 'Impayés, encaissements, quittances.' },
              { emoji: '🛡️', name: 'Agent Sécurité', desc: 'Démarches, incidents, conflits de voisinage.' },
              { emoji: '🗂️', name: 'Agent Administratif', desc: 'Biens, locataires, contrats, entretiens.' },
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
                    {tgDeepLink ? (
                      <>1. Ouvrez le bot puis envoyez la commande ci-dessous.</>
                    ) : (
                      <>1. Ouvrez votre bot Telegram et envoyez-lui la commande ci-dessous.</>
                    )}
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
      )}

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
