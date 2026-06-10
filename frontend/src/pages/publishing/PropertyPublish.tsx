import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Upload, Image as ImageIcon, Send, Clock, EyeOff, Save, ExternalLink, Eye, TrendingUp, Trash2 } from 'lucide-react'
import { publishingApi, uploadPropertyPhoto, type Listing, type PublishPlatform } from '@/api/publishing'
import { toast } from '@/store/toast'

const media = (p: string) => (/^https?:\/\//.test(p) ? p : `${import.meta.env.VITE_API_URL || ''}${p}`)

const STATUS: Record<string, { label: string; cls: string }> = {
  draft:       { label: 'Brouillon',  cls: 'bg-gray-100 text-gray-600' },
  scheduled:   { label: 'Programmée', cls: 'bg-amber-100 text-amber-700' },
  published:   { label: 'Publiée',    cls: 'bg-emerald-100 text-emerald-700' },
  unpublished: { label: 'Dépubliée',  cls: 'bg-gray-200 text-gray-600' },
}

export default function PropertyPublish() {
  const { id } = useParams<{ id: string }>()
  const [listing, setListing] = useState<Listing | null>(null)
  const [platforms, setPlatforms] = useState<PublishPlatform[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [when, setWhen] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  // Champs édités
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [photoIds, setPhotoIds] = useState<string[]>([])
  const [platformIds, setPlatformIds] = useState<string[]>([])

  const hydrate = (l: Listing) => {
    setListing(l)
    setTitle(l.title ?? '')
    setDescription(l.description ?? '')
    setPrice(l.price != null ? String(l.price) : '')
    setPhotoIds(l.photo_ids ?? [])
    setPlatformIds(l.platform_ids ?? [])
  }

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [l, p] = await Promise.all([publishingApi.getListing(id), publishingApi.listPlatforms()])
      hydrate(l.data)
      setPlatforms(p.data.filter(x => x.is_active))
    } catch { /* intercepteur affiche l'erreur */ }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [id])

  const payload = () => ({
    title: title.trim() || null,
    description: description.trim() || null,
    price: price.trim() ? Number(price) : null,
    photo_ids: photoIds,
    platform_ids: platformIds,
  })

  const save = async () => {
    if (!id) return
    setSaving(true)
    try {
      const r = await publishingApi.saveListing(id, payload())
      hydrate(r.data)
      toast.success('Annonce enregistrée.')
    } catch { /* */ } finally { setSaving(false) }
  }

  const act = async (fn: () => Promise<{ data: Listing }>, msg: string) => {
    if (!id) return
    setBusy(true)
    try {
      await publishingApi.saveListing(id, payload())  // enregistre le contenu courant d'abord
      const r = await fn()
      hydrate(r.data)
      toast.success(msg)
    } catch { /* */ } finally { setBusy(false) }
  }

  const onPublish = () => act(() => publishingApi.publish(id!), 'Annonce publiée.')
  const onUnpublish = () => act(() => publishingApi.unpublish(id!), 'Annonce dépubliée.')
  const onSchedule = () => {
    if (!when) { toast.error('Choisissez une date de publication.'); return }
    const iso = new Date(when).toISOString()
    act(() => publishingApi.schedule(id!, iso), 'Publication programmée.')
  }

  const togglePhoto = (pid: string) =>
    setPhotoIds(prev => prev.includes(pid) ? prev.filter(x => x !== pid) : [...prev, pid])

  const deletePhoto = async (pid: string) => {
    if (!id) return
    if (!window.confirm('Supprimer définitivement cette photo ? Elle sera retirée du bien et de l\'annonce.')) return
    setBusy(true)
    try {
      await publishingApi.deletePhoto(id, pid)
      setListing(prev => prev ? { ...prev, available_photos: prev.available_photos.filter(p => p.id !== pid) } : prev)
      setPhotoIds(prev => prev.filter(x => x !== pid))
      toast.success('Photo supprimée.')
    } catch { /* intercepteur affiche l'erreur */ } finally { setBusy(false) }
  }
  const togglePlatform = (pid: string) =>
    setPlatformIds(prev => prev.includes(pid) ? prev.filter(x => x !== pid) : [...prev, pid])

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length || !id) return
    setBusy(true)
    try {
      for (const f of Array.from(files)) await uploadPropertyPhoto(id, f)
      const r = await publishingApi.getListing(id)
      // conserve les sélections + le contenu en cours d'édition
      setListing(prev => prev ? { ...prev, available_photos: r.data.available_photos } : r.data)
      toast.success('Photo(s) ajoutée(s).')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de l'envoi")
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (loading) return <div className="p-6 text-gray-400">Chargement…</div>
  if (!listing) return <div className="p-6 text-gray-400">Annonce indisponible.</div>

  const st = STATUS[listing.status] ?? STATUS.draft
  const publicUrl = listing.public_path ? `${window.location.origin}${listing.public_path}` : null
  const photos = listing.available_photos

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      <Link to={`/properties/${id}`} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-3">
        <ArrowLeft size={15} /> Retour au bien
      </Link>

      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <h1 className="text-2xl font-bold text-gray-900">Publication de l'annonce</h1>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${st.cls}`}>{st.label}</span>
      </div>

      {/* Performances (suivi des vues) */}
      {(listing.status === 'published' || listing.views_count > 0) && (
        <div className="mb-5 grid grid-cols-3 gap-3">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><Eye size={12} /> Vues</p>
            <p className="text-xl font-bold text-gray-900 mt-0.5">{listing.views_count}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><Clock size={12} /> En ligne depuis</p>
            <p className="text-xl font-bold text-gray-900 mt-0.5">
              {listing.published_at
                ? `${Math.max(1, Math.ceil((Date.now() - new Date(listing.published_at).getTime()) / 86400000))} j`
                : '—'}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400 flex items-center gap-1"><TrendingUp size={12} /> Vues / jour</p>
            <p className="text-xl font-bold text-gray-900 mt-0.5">
              {listing.published_at
                ? (listing.views_count / Math.max(1, Math.ceil((Date.now() - new Date(listing.published_at).getTime()) / 86400000))).toFixed(1)
                : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Lien public quand publiée */}
      {listing.status === 'published' && publicUrl && (
        <div className="mb-5 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-sm text-emerald-800 break-all">
            Page publique : <a href={publicUrl} target="_blank" rel="noopener" className="font-medium underline inline-flex items-center gap-1">{publicUrl}<ExternalLink size={12} /></a>
          </div>
          <button onClick={() => { navigator.clipboard?.writeText(publicUrl); toast.success('Lien copié.') }}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white border border-emerald-300 text-emerald-700">Copier</button>
        </div>
      )}
      {listing.status === 'scheduled' && listing.scheduled_at && (
        <div className="mb-5 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          Publication programmée le {new Date(listing.scheduled_at).toLocaleString('fr-FR')}.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Titre de l'annonce</label>
          <input value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Bel appartement T3 lumineux…" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={5}
              placeholder="Décrivez le bien, le quartier, les atouts…" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Loyer (€ / mois)</label>
            <input value={price} onChange={e => setPrice(e.target.value)} type="number" min="0"
              placeholder="950" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        {/* Photos */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Photos ({photoIds.length} sélectionnée{photoIds.length > 1 ? 's' : ''})</label>
            <button onClick={() => fileRef.current?.click()} disabled={busy}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-50">
              <Upload size={13} /> Ajouter
            </button>
            <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={onUpload} />
          </div>
          {photos.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-400">
              <ImageIcon size={24} className="mx-auto mb-1 text-gray-300" />
              Aucune photo. Ajoutez-en pour enrichir l'annonce.
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {photos.map(ph => {
                const idx = photoIds.indexOf(ph.id)
                const sel = idx >= 0
                return (
                  <div key={ph.id}
                    className={`relative rounded-lg overflow-hidden aspect-square border-2 ${sel ? 'border-blue-600' : 'border-transparent'}`}>
                    <button type="button" onClick={() => togglePhoto(ph.id)} title={sel ? 'Retirer de l\'annonce' : 'Ajouter à l\'annonce'}
                      className="absolute inset-0 w-full h-full">
                      <img src={media(ph.url)} alt={ph.label ?? ''} className="w-full h-full object-cover" />
                    </button>
                    {sel && (
                      <span className="absolute top-1 left-1 w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center pointer-events-none">{idx + 1}</span>
                    )}
                    <button type="button" onClick={() => deletePhoto(ph.id)} disabled={busy}
                      title="Supprimer définitivement la photo"
                      className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/55 hover:bg-red-600 text-white flex items-center justify-center disabled:opacity-50">
                      <Trash2 size={12} />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Plateformes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Plateformes de diffusion</label>
          {platforms.length === 0 ? (
            <p className="text-sm text-gray-400">
              Aucune plateforme active. <Link to="/diffusion" className="text-blue-600 underline">Définissez vos plateformes</Link>.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {platforms.map(pf => {
                const sel = platformIds.includes(pf.id)
                return (
                  <button key={pf.id} type="button" onClick={() => togglePlatform(pf.id)}
                    className={`text-sm px-3 py-1.5 rounded-lg border ${sel ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>
                    {pf.name}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <button onClick={save} disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-60" style={{ background: '#0D2F5C' }}>
            <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </div>

      {/* Actions de publication */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mt-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">Publication</h2>
        <div className="flex flex-wrap items-end gap-3">
          <button onClick={onPublish} disabled={busy}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-60" style={{ background: '#0E9F8E' }}>
            <Send size={15} /> Publier maintenant
          </button>
          <div className="flex items-end gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Programmer</label>
              <input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            </div>
            <button onClick={onSchedule} disabled={busy}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold bg-amber-100 hover:bg-amber-200 text-amber-800 disabled:opacity-60">
              <Clock size={15} /> Programmer
            </button>
          </div>
          {(listing.status === 'published' || listing.status === 'scheduled') && (
            <button onClick={onUnpublish} disabled={busy}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-60">
              <EyeOff size={15} /> Dépublier
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-3">
          La publication crée une page d'annonce publique partageable. Le contenu en cours est enregistré automatiquement avant chaque action.
        </p>
      </div>
    </div>
  )
}
