import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Field, Modal, Spinner, useToast } from './ui'
import { cx, time12 } from '../utils'

// Owner adds a phone / walk-in booking. Uses the same slot engine + 409 protection.
export default function WalkInModal({ open, onClose, date, onCreated }) {
  const { business } = useAuth()
  const toast = useToast()
  const [services, setServices] = useState([])
  const [serviceId, setServiceId] = useState('')
  const [day, setDay] = useState(date)
  const [slots, setSlots] = useState(null)
  const [slot, setSlot] = useState('')
  const [form, setForm] = useState({ name: '', phone: '', notes: '' })
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (open) { setDay(date); setSlot(''); setForm({ name: '', phone: '', notes: '' }) } }, [open, date])
  useEffect(() => {
    if (!open) return
    api('/services').then((s) => { const act = s.filter((x) => x.is_active); setServices(act); setServiceId((v) => v || act[0]?.id || '') })
  }, [open])
  useEffect(() => {
    if (!open || !serviceId || !day) return
    setSlots(null)
    api(`/public/${business.slug}/slots?service_id=${serviceId}&date=${day}`, { auth: false })
      .then(setSlots).catch((e) => { setSlots({ slots: [] }); toast(e.message, 'error') })
  }, [open, serviceId, day, business.slug, toast])

  const submit = async (e) => {
    e.preventDefault()
    if (!slot) return toast('Pick a time slot', 'error')
    setBusy(true)
    try {
      await api('/appointments', { method: 'POST', body: { service_id: Number(serviceId), start_time: slot, ...form } })
      toast('Booking added')
      onCreated?.(); onClose()
    } catch (err) { toast(err.message, 'error') } finally { setBusy(false) }
  }

  const free = (slots?.slots || []).filter((s) => s.available)
  return (
    <Modal open={open} onClose={onClose} title="Add booking" wide
      footer={<><button className="btn-ghost" onClick={onClose}>Cancel</button><button form="walkin" className="btn-primary" disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : 'Save booking'}</button></>}>
      <form id="walkin" onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Service"><select className="input" value={serviceId} onChange={(e) => { setServiceId(e.target.value); setSlot('') }}>
            {services.map((s) => <option key={s.id} value={s.id} className="bg-ink-900">{s.name} · {s.duration_min} min</option>)}</select></Field>
          <Field label="Date"><input type="date" className="input" value={day} onChange={(e) => { setDay(e.target.value); setSlot('') }} /></Field>
        </div>
        <div>
          <span className="label">Free slots</span>
          <div className="glass-soft max-h-44 overflow-y-auto p-3">
            {!slots ? <div className="flex justify-center py-4"><Spinner /></div> : free.length === 0 ? <p className="py-3 text-center text-sm text-slate-400">No free slots on this day.</p> : (
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {free.map((s) => (
                  <button type="button" key={s.start_time} onClick={() => setSlot(s.start_time)}
                    className={cx('rounded-lg border py-1.5 text-xs font-semibold', slot === s.start_time ? 'border-transparent bg-white text-ink-950' : 'border-white/15 bg-ink-800 text-white hover:border-brand-400')}>
                    {time12(s.label)}</button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Customer name"><input className="input" required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone"><input className="input" required pattern="\+?[0-9 \-]{7,20}" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
        </div>
        <Field label="Note"><input className="input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Walk-in / phone booking" /></Field>
      </form>
    </Modal>
  )
}
