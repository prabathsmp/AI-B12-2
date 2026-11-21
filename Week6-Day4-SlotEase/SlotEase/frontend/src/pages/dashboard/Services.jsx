import { useEffect, useState } from 'react'
import { Archive, Clock, Pencil, Plus, Sparkles, Tags, Trash2 } from 'lucide-react'
import { aiHeaders, api, getAiSettings } from '../../api'
import { Empty, Field, Modal, PageLoader, Spinner, Toggle, useToast } from '../../components/ui'
import { cx, rupees } from '../../utils'
import { PageHeader } from './Layout'

const BLANK = { name: '', duration_min: 30, price: 300, description: '', is_active: true }
const DURATIONS = [15, 30, 45, 60, 90, 120]

export default function Services() {
  const toast = useToast()
  const [rows, setRows] = useState(null)
  const [edit, setEdit] = useState(null)
  const [busy, setBusy] = useState(false)
  const [aiBusy, setAiBusy] = useState(false)
  const [confirmDel, setConfirmDel] = useState(null)
  const hasAi = !!getAiSettings().key

  const load = () => api('/services').then(setRows).catch((e) => toast(e.message, 'error'))
  useEffect(() => { load() }, [])

  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const body = { ...edit, duration_min: Number(edit.duration_min), price: Number(edit.price) }
      if (edit.id) await api(`/services/${edit.id}`, { method: 'PUT', body })
      else await api('/services', { method: 'POST', body })
      toast(edit.id ? 'Service updated' : 'Service added')
      setEdit(null); load()
    } catch (err) { toast(err.message, 'error') } finally { setBusy(false) }
  }

  const remove = async (s) => {
    try {
      const r = await api(`/services/${s.id}`, { method: 'DELETE' })
      toast(r.message, r.archived ? 'info' : 'success'); setConfirmDel(null); load()
    } catch (err) { toast(err.message, 'error') }
  }

  const toggle = async (s) => {
    try { await api(`/services/${s.id}`, { method: 'PUT', body: { ...s, is_active: !s.is_active } }); load() } catch (err) { toast(err.message, 'error') }
  }

  const aiDescribe = async () => {
    if (!edit.name) return toast('Enter a service name first', 'error')
    setAiBusy(true)
    try {
      const r = await api(`/ai/service-description?model=${encodeURIComponent(getAiSettings().model || 'gpt-4o-mini')}`, {
        method: 'POST', headers: aiHeaders(), body: { ...edit, duration_min: Number(edit.duration_min), price: Number(edit.price) },
      })
      setEdit((x) => ({ ...x, description: r.description }))
    } catch (err) { toast(err.message, 'error') } finally { setAiBusy(false) }
  }

  if (!rows) return <PageLoader />
  return (
    <>
      <PageHeader title="Services" subtitle="What customers can book, how long it takes and what it costs."
        actions={<button className="btn-primary" onClick={() => setEdit({ ...BLANK })}><Plus className="h-4 w-4" />New service</button>} />

      {rows.length === 0 ? (
        <div className="glass p-6"><Empty icon={Tags} title="No services yet" action={<button className="btn-primary" onClick={() => setEdit({ ...BLANK })}><Plus className="h-4 w-4" />Add your first service</button>}>
          Add services like “Haircut · 30 min · ₹300” so customers can start booking.</Empty></div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((s) => (
            <div key={s.id} className={cx('glass flex flex-col p-5 transition hover:border-brand-400/40', !s.is_active && 'opacity-60')}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-lg font-bold text-white">{s.name}</h3>
                  <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-slate-300"><Clock className="h-4 w-4 text-brand-300" />{s.duration_min} min</p>
                </div>
                <p className="font-display text-2xl font-bold text-white">{rupees(s.price)}</p>
              </div>
              <p className="mt-3 line-clamp-2 flex-1 text-sm text-slate-300">{s.description || <span className="italic text-slate-500">No description</span>}</p>
              <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
                <span className="flex items-center gap-2 text-sm text-slate-300"><Toggle checked={s.is_active} onChange={() => toggle(s)} label="Active" />{s.is_active ? 'Bookable' : 'Hidden'}</span>
                <div className="flex gap-1">
                  <button className="btn-ghost btn-sm" onClick={() => setEdit({ ...s })}><Pencil className="h-3.5 w-3.5" />Edit</button>
                  <button className="btn-ghost btn-sm hover:!border-rose-400/50 hover:!text-rose-200" onClick={() => setConfirmDel(s)} aria-label="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? 'Edit service' : 'New service'}
        footer={<><button className="btn-ghost" onClick={() => setEdit(null)}>Cancel</button><button form="svc" className="btn-primary" disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : 'Save service'}</button></>}>
        {edit && (
          <form id="svc" onSubmit={save} className="space-y-4">
            <Field label="Name"><input className="input" required value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} placeholder="Haircut + Beard" /></Field>
            <Field label="Duration">
              <div className="flex flex-wrap gap-2">
                {DURATIONS.map((d) => (
                  <button type="button" key={d} onClick={() => setEdit({ ...edit, duration_min: d })}
                    className={cx('rounded-lg border px-3 py-1.5 text-sm font-semibold', Number(edit.duration_min) === d ? 'border-transparent bg-white text-ink-950' : 'border-white/15 bg-ink-800 text-slate-200 hover:border-brand-400')}>{d} min</button>
                ))}
                <input type="number" min={5} max={600} step={5} className="input w-28" value={edit.duration_min} onChange={(e) => setEdit({ ...edit, duration_min: e.target.value })} aria-label="Custom minutes" />
              </div>
            </Field>
            <Field label="Price (₹)"><input type="number" min={0} step={10} className="input" required value={edit.price} onChange={(e) => setEdit({ ...edit, price: e.target.value })} /></Field>
            <Field label={<span className="flex items-center justify-between"><span>Description</span>
              <button type="button" onClick={aiDescribe} disabled={aiBusy || !hasAi} title={hasAi ? 'Write with AI' : 'Add an OpenAI key in Settings to enable'}
                className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold normal-case tracking-normal text-fuchsia-200 hover:bg-fuchsia-500/15 disabled:opacity-40">
                {aiBusy ? <Spinner className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}Write with AI</button></span>}>
              <textarea className="input min-h-[80px]" maxLength={1000} value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} placeholder="Shown on your booking page" />
            </Field>
            <div className="flex items-center gap-3 text-sm text-slate-200"><Toggle checked={edit.is_active} onChange={(v) => setEdit({ ...edit, is_active: v })} label="Bookable" />Customers can book this service</div>
          </form>
        )}
      </Modal>

      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Delete service?"
        footer={<><button className="btn-ghost" onClick={() => setConfirmDel(null)}>Keep it</button><button className="btn bg-rose-500 text-white hover:bg-rose-400" onClick={() => remove(confirmDel)}><Trash2 className="h-4 w-4" />Delete</button></>}>
        <p className="text-slate-200">Delete <b className="text-white">{confirmDel?.name}</b>? If it already has bookings it will be <span className="inline-flex items-center gap-1 text-amber-200"><Archive className="h-3.5 w-3.5" />archived</span> instead so your history stays intact.</p>
      </Modal>
    </>
  )
}
