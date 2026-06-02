import { useEffect, useRef, useState, useCallback } from 'react'
import {
  ArrowLeft, Save, RefreshCw, ChevronUp, ChevronDown, GripVertical,
  Eye, EyeOff, Plus, Trash2, Palette, Check,
} from 'lucide-react'
import { apiClient } from '@/api/client'

// ── Types ──────────────────────────────────────────────────────────────────
interface Block { id: string; type: string; enabled: boolean; props: any }
interface Theme { [k: string]: string }

interface Template {
  id: string
  name: string
  template_type: string
  blocks?: Block[] | null
  theme?: Theme | null
  logo_url?: string | null
}

interface Props {
  template: Template
  onBack: () => void
  onSaved: () => void
}

// Libellés FR + descriptions par type de bloc.
const BLOCK_META: Record<string, { label: string; hint: string }> = {
  header: { label: 'En-tête (logo + titre)', hint: 'Logo à gauche, titre et sous-titres à droite.' },
  sidebar: { label: "Colonne d'informations", hint: 'Sections titrées (gauche) : infos, références, agence…' },
  recipient: { label: 'Destinataire', hint: 'Date et adresse du destinataire (à droite).' },
  reference: { label: 'Bloc référence', hint: 'Résidence, adresse, référence immeuble, locataire.' },
  greeting: { label: "Formule d'appel", hint: 'Salutation et phrase d’introduction.' },
  amount_bar: { label: 'Bandeau « Montant à payer »', hint: 'Titre + bandeau coloré avec le montant.' },
  details_table: { label: 'Tableau détaillé des montants', hint: 'Lignes appelées / réglées + total.' },
  table: { label: 'Tableau', hint: 'Colonnes + lignes (section / donnée / total / résultat).' },
  highlight: { label: 'Encadré', hint: 'Bloc mis en avant (titre + texte), ex. « La formule ».' },
  legal_footer: { label: 'Pied de page légal', hint: 'Mentions légales en bas de document.' },
  free_text: { label: 'Texte libre', hint: 'Paragraphe libre que vous rédigez.' },
}

// Variables insérables.
const VARS: { k: string; l: string }[] = [
  { k: '{{tenant_name}}', l: 'Nom locataire' },
  { k: '{{tenant_civil_name}}', l: 'Civilité + nom' },
  { k: '{{tenant_email}}', l: 'Email locataire' },
  { k: '{{tenant_phone}}', l: 'Tél locataire' },
  { k: '{{tenant_login}}', l: 'Identifiant locataire' },
  { k: '{{property_name}}', l: 'Bien' },
  { k: '{{property_address}}', l: 'Adresse bien' },
  { k: '{{property_reference}}', l: 'Réf. du bien' },
  { k: '{{company_name}}', l: 'Gestionnaire' },
  { k: '{{company_address}}', l: 'Adresse gestionnaire' },
  { k: '{{period_range}}', l: 'Période' },
  { k: '{{due_date}}', l: 'Échéance' },
  { k: '{{total_due}}', l: 'Total dû' },
  { k: '{{rent_amount}}', l: 'Loyer' },
  { k: '{{charges_amount}}', l: 'Charges' },
  { k: '{{apl_amount}}', l: 'APL (aide au logement)' },
  { k: '{{today_date}}', l: 'Date du jour' },
  // Régularisation de charges
  { k: '{{regul_real}}', l: 'Régul : dépenses' },
  { k: '{{regul_provisions}}', l: 'Régul : provisions' },
  { k: '{{regul_quote_part}}', l: 'Régul : quote-part' },
  { k: '{{regul_result_amount}}', l: 'Régul : solde' },
  // Révision de loyer
  { k: '{{rev_old_rent}}', l: 'Révision : loyer actuel' },
  { k: '{{rev_new_rent}}', l: 'Révision : nouveau loyer' },
  { k: '{{rev_old_index}}', l: 'Révision : ancien indice' },
  { k: '{{rev_new_index}}', l: 'Révision : nouvel indice' },
  { k: '{{rev_coeff}}', l: 'Révision : coefficient' },
  { k: '{{rev_effective_date}}', l: 'Révision : date d’effet' },
  // Taxes foncières
  { k: '{{tax_total}}', l: 'Taxe : montant total' },
  { k: '{{tax_days}}', l: 'Taxe : nb de jours' },
  { k: '{{tax_quote_part}}', l: 'Taxe : quote-part' },
]

const THEME_FIELDS: { key: string; label: string }[] = [
  { key: 'navy', label: 'Couleur principale (titres)' },
  { key: 'orange', label: 'Accent (référence)' },
  { key: 'teal', label: 'Bandeau montant' },
  { key: 'gray', label: 'Texte secondaire' },
  { key: 'section_bg', label: 'Fond de section (tableau)' },
  { key: 'row_bg', label: 'Lignes alternées (tableau)' },
]

const DEFAULT_THEME: Theme = {
  navy: '#003D7C', orange: '#EB690B', gray: '#949191', teal: '#4BA282',
  section_bg: '#CCEBF1', row_bg: '#F1F9FA', col_header: '#3F3F46',
  header_cell_bg: '#FAFAFA', footer_color: '#403E3E',
  font_family: 'Helvetica, Arial, sans-serif',
}

// ── Champ texte avec insertion de variable au curseur ────────────────────────
function VarInput({ value, onChange, registerActive, placeholder, textarea }: {
  value: string
  onChange: (v: string) => void
  registerActive: (fn: ((txt: string) => void) | null) => void
  placeholder?: string
  textarea?: boolean
}) {
  const ref = useRef<HTMLInputElement & HTMLTextAreaElement>(null)
  const insert = (txt: string) => {
    const el = ref.current
    const s = el?.selectionStart ?? value.length
    const e = el?.selectionEnd ?? s
    const next = value.slice(0, s) + txt + value.slice(e)
    onChange(next)
    setTimeout(() => { el?.focus(); el?.setSelectionRange(s + txt.length, s + txt.length) }, 0)
  }
  const common = {
    ref: ref as any,
    value: value ?? '',
    placeholder,
    onChange: (e: any) => onChange(e.target.value),
    onFocus: () => registerActive(insert),
    className: 'w-full px-2 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-200',
  }
  return textarea
    ? <textarea {...common} rows={2} />
    : <input {...common} />
}

// ── Éditeur d'un bloc selon son type ─────────────────────────────────────────
function BlockEditor({ block, update, registerActive }: {
  block: Block
  update: (props: any) => void
  registerActive: (fn: ((txt: string) => void) | null) => void
}) {
  const p = block.props || {}
  const set = (k: string, v: any) => update({ ...p, [k]: v })
  const L = (s: string) => <label className="block text-[11px] font-medium text-gray-500 mb-1">{s}</label>
  const V = (props: any) => <VarInput registerActive={registerActive} {...props} />

  // Liste de lignes éditables (sidebar lines, recipient lines, reference lines…)
  const LinesEditor = ({ lines, onLines }: { lines: string[]; onLines: (l: string[]) => void }) => (
    <div className="space-y-1.5">
      {(lines || []).map((ln, i) => (
        <div key={i} className="flex items-center gap-1">
          {V({ value: ln, onChange: (v: string) => { const c = [...lines]; c[i] = v; onLines(c) } })}
          <button type="button" onClick={() => onLines(lines.filter((_, j) => j !== i))}
            className="p-1 text-gray-400 hover:text-red-500" title="Supprimer la ligne"><Trash2 size={13} /></button>
        </div>
      ))}
      <button type="button" onClick={() => onLines([...(lines || []), ''])}
        className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"><Plus size={12} /> Ajouter une ligne</button>
    </div>
  )

  switch (block.type) {
    case 'header':
      return (<div className="space-y-2">
        <div>{L('Titre')}{V({ value: p.title, onChange: (v: string) => set('title', v) })}</div>
        <div>{L('Sous-titre 1 (ex. période)')}{V({ value: p.subtitle1, onChange: (v: string) => set('subtitle1', v) })}</div>
        <div>{L('Sous-titre 2')}{V({ value: p.subtitle2, onChange: (v: string) => set('subtitle2', v) })}</div>
        <p className="text-[11px] text-gray-400">Le logo provient de « Mes informations » / du logo enregistré sur le modèle.</p>
      </div>)
    case 'sidebar':
      return (<div className="space-y-3">
        {(p.sections || []).map((sec: any, si: number) => (
          <div key={si} className="border border-gray-200 rounded-lg p-2 bg-gray-50">
            <div className="flex items-center gap-1 mb-1.5">
              {V({ value: sec.title, onChange: (v: string) => { const s = [...p.sections]; s[si] = { ...sec, title: v }; set('sections', s) } })}
              <button type="button" onClick={() => set('sections', p.sections.filter((_: any, j: number) => j !== si))}
                className="p-1 text-gray-400 hover:text-red-500" title="Supprimer la section"><Trash2 size={13} /></button>
            </div>
            <LinesEditor lines={sec.lines || []} onLines={(l) => { const s = [...p.sections]; s[si] = { ...sec, lines: l }; set('sections', s) }} />
          </div>
        ))}
        <button type="button" onClick={() => set('sections', [...(p.sections || []), { title: 'NOUVELLE SECTION', lines: [''] }])}
          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"><Plus size={12} /> Ajouter une section</button>
      </div>)
    case 'recipient':
      return (<div className="space-y-2">
        <div>{L('Date')}{V({ value: p.date_text, onChange: (v: string) => set('date_text', v) })}</div>
        <div>{L('Lignes de l’adresse')}<LinesEditor lines={p.lines || []} onLines={(l) => set('lines', l)} /></div>
      </div>)
    case 'reference':
      return (<div className="space-y-2">
        <div>{L('Lignes')}<LinesEditor lines={p.lines || []} onLines={(l) => set('lines', l)} /></div>
        <div>{L('Ligne référence')}{V({ value: p.ref_line, onChange: (v: string) => set('ref_line', v) })}</div>
        <div>{L('Ligne locataire')}{V({ value: p.tenant_line, onChange: (v: string) => set('tenant_line', v) })}</div>
      </div>)
    case 'greeting':
      return (<div className="space-y-2">
        <div>{L('Salutation')}{V({ value: p.salutation, onChange: (v: string) => set('salutation', v) })}</div>
        <div>{L('Introduction')}{V({ value: p.intro, onChange: (v: string) => set('intro', v), textarea: true })}</div>
      </div>)
    case 'amount_bar':
      return (<div className="space-y-2">
        <div>{L('Titre')}{V({ value: p.title, onChange: (v: string) => set('title', v) })}</div>
        <div>{L('Libellé du bandeau')}{V({ value: p.label, onChange: (v: string) => set('label', v) })}</div>
        <div>{L('Montant')}{V({ value: p.amount, onChange: (v: string) => set('amount', v) })}</div>
      </div>)
    case 'details_table':
      return (<div className="space-y-2">
        <div>{L('Titre du tableau')}{V({ value: p.heading, onChange: (v: string) => set('heading', v) })}</div>
        <div>{L('En-tête de section')}{V({ value: p.section_label, onChange: (v: string) => set('section_label', v) })}</div>
        <div className="grid grid-cols-2 gap-2">
          <div>{L('Colonne appelés')}{V({ value: p.col_appel, onChange: (v: string) => set('col_appel', v) })}</div>
          <div>{L('Colonne réglés')}{V({ value: p.col_regle, onChange: (v: string) => set('col_regle', v) })}</div>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input type="checkbox" checked={p.show_regle !== false} onChange={e => set('show_regle', e.target.checked)} />
          Afficher la colonne « réglés »
        </label>
        <div>{L('Ligne total')}{V({ value: p.total_label, onChange: (v: string) => set('total_label', v) })}</div>
        <div>{L('Ligne « Montant à payer »')}{V({ value: p.pay_label, onChange: (v: string) => set('pay_label', v) })}</div>
        <div className="border-t border-gray-100 pt-2">
          <p className="text-[11px] font-medium text-gray-500 mb-1">Lignes personnalisées (en plus du loyer/charges automatiques)</p>
          {(p.custom_rows || []).map((cr: any, i: number) => (
            <div key={i} className="flex items-center gap-1 mb-1">
              {V({ value: cr.label, onChange: (v: string) => { const c = [...p.custom_rows]; c[i] = { ...cr, label: v }; set('custom_rows', c) }, placeholder: 'Libellé' })}
              {V({ value: cr.appele, onChange: (v: string) => { const c = [...p.custom_rows]; c[i] = { ...cr, appele: v }; set('custom_rows', c) }, placeholder: 'Appelé' })}
              <button type="button" onClick={() => set('custom_rows', p.custom_rows.filter((_: any, j: number) => j !== i))}
                className="p-1 text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
            </div>
          ))}
          <button type="button" onClick={() => set('custom_rows', [...(p.custom_rows || []), { label: '', appele: '', regle: '' }])}
            className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"><Plus size={12} /> Ajouter une ligne</button>
        </div>
      </div>)
    case 'highlight':
      return (<div className="space-y-2">
        <div>{L('Titre')}{V({ value: p.title, onChange: (v: string) => set('title', v) })}</div>
        <div>{L('Texte')}{V({ value: p.text, onChange: (v: string) => set('text', v), textarea: true })}</div>
      </div>)
    case 'table': {
      const cols: any[] = p.columns || []
      const rows: any[] = p.rows || []
      const setCols = (c: any[]) => set('columns', c)
      const setRows = (r: any[]) => set('rows', r)
      return (<div className="space-y-3">
        <div>{L('Titre du tableau')}{V({ value: p.heading, onChange: (v: string) => set('heading', v) })}</div>
        <div>
          {L('Colonnes')}
          <div className="space-y-1.5">
            {cols.map((c, ci) => (
              <div key={ci} className="flex items-center gap-1">
                {V({ value: c.label, onChange: (v: string) => { const n = [...cols]; n[ci] = { ...c, label: v }; setCols(n) }, placeholder: `Colonne ${ci + 1}` })}
                <button type="button" onClick={() => { setCols(cols.filter((_, j) => j !== ci)); setRows(rows.map(r => ({ ...r, cells: (r.cells || []).filter((_: any, j: number) => j !== ci) }))) }}
                  className="p-1 text-gray-400 hover:text-red-500" title="Supprimer la colonne"><Trash2 size={13} /></button>
              </div>
            ))}
            <button type="button" onClick={() => setCols([...cols, { label: '', align: 'right' }])}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"><Plus size={12} /> Ajouter une colonne</button>
          </div>
        </div>
        <div>
          {L('Lignes')}
          <div className="space-y-2">
            {rows.map((r, ri) => (
              <div key={ri} className="border border-gray-200 rounded-lg p-2 bg-gray-50 space-y-1.5">
                <div className="flex items-center gap-1">
                  <select value={r.kind || 'data'} onChange={e => { const n = [...rows]; n[ri] = { ...r, kind: e.target.value }; setRows(n) }}
                    className="text-xs border border-gray-200 rounded px-1 py-1 bg-white">
                    <option value="section">Section</option>
                    <option value="data">Donnée</option>
                    <option value="total">Total</option>
                    <option value="result">Résultat</option>
                  </select>
                  {V({ value: r.label, onChange: (v: string) => { const n = [...rows]; n[ri] = { ...r, label: v }; setRows(n) }, placeholder: 'Libellé' })}
                  <button type="button" onClick={() => setRows(rows.filter((_, j) => j !== ri))}
                    className="p-1 text-gray-400 hover:text-red-500" title="Supprimer la ligne"><Trash2 size={13} /></button>
                </div>
                {r.kind !== 'section' && cols.length > 0 && (
                  <div className="grid grid-cols-2 gap-1">
                    {cols.map((c, ci) => (
                      <div key={ci}>{V({ value: (r.cells || [])[ci] || '', onChange: (v: string) => { const n = [...rows]; const cells = [...(r.cells || [])]; cells[ci] = v; n[ri] = { ...r, cells }; setRows(n) }, placeholder: c.label || `Col ${ci + 1}` })}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <button type="button" onClick={() => setRows([...rows, { kind: 'data', label: '', cells: [] }])}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"><Plus size={12} /> Ajouter une ligne</button>
          </div>
        </div>
      </div>)
    }
    case 'legal_footer':
    case 'free_text':
      return <div>{L(block.type === 'free_text' ? 'Texte' : 'Mentions légales')}{V({ value: p.text, onChange: (v: string) => set('text', v), textarea: true })}</div>
    default:
      return <p className="text-xs text-gray-400">Bloc non éditable.</p>
  }
}

// ── Composant principal ──────────────────────────────────────────────────────
export default function AvisBlockEditor({ template, onBack, onSaved }: Props) {
  const [blocks, setBlocks] = useState<Block[]>(() =>
    Array.isArray(template.blocks) ? JSON.parse(JSON.stringify(template.blocks)) : [])
  const [theme, setTheme] = useState<Theme>(() => ({ ...DEFAULT_THEME, ...(template.theme || {}) }))
  const [name, setName] = useState(template.name)
  const [openId, setOpenId] = useState<string | null>(null)
  const [showTheme, setShowTheme] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const dragIndex = useRef<number | null>(null)
  const activeInsert = useRef<((txt: string) => void) | null>(null)

  // Aperçu PDF
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const previewUrlRef = useRef<string | null>(null)

  const updateBlock = (id: string, props: any) =>
    setBlocks(bs => bs.map(b => b.id === id ? { ...b, props } : b))
  const toggleBlock = (id: string) =>
    setBlocks(bs => bs.map(b => b.id === id ? { ...b, enabled: !b.enabled } : b))

  const move = (from: number, to: number) => {
    if (to < 0 || to >= blocks.length) return
    setBlocks(bs => { const c = [...bs]; const [m] = c.splice(from, 1); c.splice(to, 0, m); return c })
  }

  // Aperçu débauché.
  useEffect(() => {
    let cancelled = false
    const h = setTimeout(async () => {
      setPreviewLoading(true)
      try {
        const r = await apiClient.post('/templates/preview', {
          template_type: template.template_type,
          blocks, theme, template_id: template.id,
        }, { responseType: 'blob' })
        if (cancelled) return
        const url = URL.createObjectURL(r.data as Blob)
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
        previewUrlRef.current = url
        setPreviewUrl(url)
      } catch { /* ignore */ } finally {
        if (!cancelled) setPreviewLoading(false)
      }
    }, 600)
    return () => { cancelled = true; clearTimeout(h) }
  }, [blocks, theme, template.id])

  useEffect(() => () => { if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current) }, [])

  const registerActive = useCallback((fn: ((txt: string) => void) | null) => { activeInsert.current = fn }, [])

  const save = async () => {
    setSaving(true)
    try {
      await apiClient.patch(`/templates/${template.id}`, { name, blocks, theme })
      setSavedOk(true); setTimeout(() => setSavedOk(false), 2000)
      onSaved()
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Erreur lors de l'enregistrement")
    } finally { setSaving(false) }
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Barre supérieure */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2.5 bg-white border-b">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={onBack} className="p-1.5 rounded hover:bg-gray-100 text-gray-500"><ArrowLeft size={18} /></button>
          <input value={name} onChange={e => setName(e.target.value)}
            className="font-semibold text-gray-900 px-2 py-1 rounded hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200 min-w-0" />
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium shrink-0">Éditeur par blocs</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowTheme(s => !s)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border ${showTheme ? 'bg-blue-50 border-blue-200 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            <Palette size={15} /> Couleurs
          </button>
          <button onClick={save} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50">
            {savedOk ? <Check size={15} /> : <Save size={15} />} {saving ? 'Enregistrement…' : savedOk ? 'Enregistré' : 'Enregistrer'}
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex">
        {/* Colonne gauche : blocs */}
        <div className="w-[440px] shrink-0 border-r bg-white flex flex-col">
          {/* Chips de variables */}
          <div className="shrink-0 px-3 py-2 border-b bg-gray-50">
            <p className="text-[11px] text-gray-400 mb-1.5">Cliquez dans un champ, puis insérez une variable :</p>
            <div className="flex flex-wrap gap-1">
              {VARS.map(v => (
                <button key={v.k} type="button" title={v.k}
                  onClick={() => activeInsert.current?.(v.k)}
                  className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-white border border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-700">
                  {v.l}
                </button>
              ))}
            </div>
          </div>

          {/* Panneau thème */}
          {showTheme && (
            <div className="shrink-0 px-3 py-2.5 border-b bg-blue-50/40 space-y-2">
              {THEME_FIELDS.map(f => (
                <div key={f.key} className="flex items-center justify-between gap-2">
                  <span className="text-xs text-gray-600">{f.label}</span>
                  <input type="color" value={theme[f.key] || '#000000'}
                    onChange={e => setTheme(t => ({ ...t, [f.key]: e.target.value }))}
                    className="w-8 h-6 rounded border border-gray-200 cursor-pointer" />
                </div>
              ))}
              <button type="button" onClick={() => setTheme({ ...DEFAULT_THEME })}
                className="text-[11px] text-gray-500 hover:text-gray-700 underline">Réinitialiser les couleurs</button>
            </div>
          )}

          {/* Liste des blocs */}
          <div className="flex-1 min-h-0 overflow-auto p-3 space-y-2">
            {blocks.map((b, i) => {
              const meta = BLOCK_META[b.type] || { label: b.type, hint: '' }
              const open = openId === b.id
              return (
                <div key={b.id}
                  draggable
                  onDragStart={() => { dragIndex.current = i }}
                  onDragOver={e => e.preventDefault()}
                  onDrop={() => { if (dragIndex.current !== null) move(dragIndex.current, i); dragIndex.current = null }}
                  className={`rounded-lg border ${b.enabled ? 'border-gray-200 bg-white' : 'border-dashed border-gray-200 bg-gray-50 opacity-70'}`}>
                  <div className="flex items-center gap-1.5 px-2 py-2">
                    <GripVertical size={15} className="text-gray-300 cursor-grab shrink-0" />
                    <button onClick={() => setOpenId(open ? null : b.id)} className="flex-1 min-w-0 text-left">
                      <div className="text-sm font-medium text-gray-800 truncate">{meta.label}</div>
                      {!open && <div className="text-[11px] text-gray-400 truncate">{meta.hint}</div>}
                    </button>
                    <div className="flex items-center gap-0.5 shrink-0">
                      <button onClick={() => move(i, i - 1)} disabled={i === 0}
                        className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30" title="Monter"><ChevronUp size={15} /></button>
                      <button onClick={() => move(i, i + 1)} disabled={i === blocks.length - 1}
                        className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30" title="Descendre"><ChevronDown size={15} /></button>
                      <button onClick={() => toggleBlock(b.id)}
                        className={`p-1 ${b.enabled ? 'text-blue-500 hover:text-blue-700' : 'text-gray-300 hover:text-gray-500'}`}
                        title={b.enabled ? 'Masquer ce bloc' : 'Afficher ce bloc'}>
                        {b.enabled ? <Eye size={15} /> : <EyeOff size={15} />}
                      </button>
                    </div>
                  </div>
                  {open && (
                    <div className="px-3 pb-3 pt-1 border-t border-gray-100">
                      <BlockEditor block={b} update={(props) => updateBlock(b.id, props)} registerActive={registerActive} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Colonne droite : aperçu PDF */}
        <div className="flex-1 min-h-0 flex flex-col bg-gray-100">
          <div className="flex items-center justify-between px-4 py-2 shrink-0">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Aperçu document</p>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              {previewLoading ? <><RefreshCw size={11} className="animate-spin" /> génération…</> : 'PDF final'}
            </span>
          </div>
          <div className="flex-1 min-h-0 px-4 pb-4">
            <div className="w-full h-full rounded-lg border border-gray-200 bg-white overflow-hidden relative">
              {previewUrl ? (
                <iframe title="Aperçu PDF" src={`${previewUrl}#toolbar=0&navpanes=0`} className="w-full h-full" />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-400">
                  <RefreshCw size={14} className="animate-spin mr-2" /> Préparation de l'aperçu…
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
