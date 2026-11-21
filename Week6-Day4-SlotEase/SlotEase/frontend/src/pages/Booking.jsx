import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle, ArrowLeft, ArrowRight, CalendarDays, Check, CheckCircle2, Clock, MapPin, MessageCircle, Moon,
  Phone, RefreshCw, Scissors, Sun, Sunrise, User,
} from 'lucide-react'
import { api } from '../api'
import { Aurora, Empty, Logo, PageLoader, Spinner, useToast } from '../components/ui'
import { addDays, cx, dayParts, prettyDate, rupees, time12, wallTime, weekdayIdx } from '../utils'

const STEPS = ['Service', 'Date & time', 'Your details']

export default function Booking() {
  const { slug } = useParams()
  const toast = useToast()
  const [biz, setBiz] = useState(null)
  const [services, setServices] = useState([])
  const [notFound, setNotFound] = useState(false)
  const [step, setStep] = useState(0)
  const [service, setService] = useState(null)
  const [date, setDate] = useState(null)
  const [slots, setSlots] = useState(null)
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [slot, setSlot] = useState(null)
  const [form, setForm] = useState({ name: '', phone: '', email: '', notes: '' })
  const [busy, setBusy] = useState(false)
  const [conflict, setConflict] = useState('')
  const [done, setDone] = useState(null)
  const topRef = useRef(null)

  useEffect(() => {
    Promise.all([api(`/public/${slug}`, { auth: false }), api(`/public/${slug}/services`, { auth: false })])
      .then(([b, s]) => { setBiz(b); setServices(s); setDate(b.today); document.title = `Book · ${b.name}` })
      .catch(() => setNotFound(true))
  }, [slug])

  const loadSlots = useCallback(async (quiet = false) => {
    if (!service || !date) return
    if (!quiet) setSlotsLoading(true)
    try {
      const r = await api(`/public/${slug}/slots?service_id=${service.id}&date=${date}`, { auth: false })
      setSlots(r)
      setSlot((cur) => (cur && !r.slots.find((x) => x.start_time === cur.start_time && x.available) ? null : cur))
    } catch (e) { toast(e.message, 'error') } finally { setSlotsLoading(false) }
  }, [service, date, slug, toast])

  useEffect(() => { if (step === 1) loadSlots() }, [step, loadSlots])
  // Live refresh so customers rarely pick a slot someone else just took.
  useEffect(() => {
    if (step !== 1) return
    const t = setInterval(() => loadSlots(true), 20000)
    return () => clearInterval(t)
  }, [step, loadSlots])

  const days = useMemo(() => (biz ? Array.from({ length: 21 }, (_, i) => addDays(biz.today, i)) : []), [biz])
  const go = (n) => { setStep(n); topRef.current?.scrollIntoView({ behavior: 'smooth' }) }

  const groups = useMemo(() => {
    const g = { Morning: [], Afternoon: [], Evening: [] }
    for (const s of slots?.slots || []) {
      const h = Number(wallTime(s.start_time).slice(0, 2))
      g[h < 12 ? 'Morning' : h < 17 ? 'Afternoon' : 'Evening'].push(s)
    }
    return g
  }, [slots])

  const book = async (e) => {
    e.preventDefault()
    setBusy(true); setConflict('')
    try {
      const r = await api(`/public/${slug}/bookings`, {
        method: 'POST', auth: false,
        body: { service_id: service.id, start_time: slot.start_time, name: form.name, phone: form.phone, email: form.email || null, notes: form.notes },
      })
      setDone(r)
      topRef.current?.scrollIntoView({ behavior: 'smooth' })
    } catch (err) {
      if (err.status === 409) {
        setConflict(err.message)
        setSlot(null)
        go(1)
        loadSlots()
      } else toast(err.message, 'error')
    } finally { setBusy(false) }
  }

  if (notFound) {
    return (
      <div className="relative flex min-h-screen items-center justify-center p-4"><Aurora />
        <div className="glass relative z-10 max-w-md p-8"><Empty icon={AlertTriangle} title="Business not found" action={<Link to="/" className="btn-primary">Go to SlotEase</Link>}>
          There’s no booking page at <b className="text-white">/{slug}</b>. Check the link and try again.</Empty></div>
      </div>
    )
  }
  if (!biz) return <div className="relative min-h-screen"><Aurora variant="booking" /><div className="relative z-10 pt-20"><PageLoader label="Opening booking page…" /></div></div>

  return (
    <div className="relative min-h-screen pb-32">
      <Aurora variant="booking" />
      <div ref={topRef} className="relative z-10 mx-auto max-w-2xl px-4 pt-5 sm:px-6">
        {/* Business header */}
        <div className="glass overflow-hidden">
          <div className="h-20 bg-gradient-to-r from-glow-500/50 via-brand-600/50 to-fuchsia-600/50" />
          <div className="-mt-10 px-5 pb-5">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border-4 border-ink-900 bg-gradient-to-br from-brand-500 to-glow-500 font-display text-2xl font-extrabold text-white shadow-brand">
              {biz.name[0]}
            </div>
            <h1 className="mt-3 text-2xl font-extrabold text-white sm:text-3xl">{biz.name}</h1>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-300">
              <span className="capitalize inline-flex items-center gap-1.5"><Scissors className="h-4 w-4 text-glow-400" />{biz.category}</span>
              {biz.address && <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4 text-glow-400" />{biz.address}</span>}
              {biz.phone && <a href={`tel:${biz.phone}`} className="inline-flex items-center gap-1.5 hover:text-white"><Phone className="h-4 w-4 text-glow-400" />{biz.phone}</a>}
            </div>
          </div>
        </div>

        {done ? <Confirmation done={done} biz={biz} service={service} onAgain={() => { setDone(null); setSlot(null); setStep(0); setService(null) }} /> : (
          <>
            {/* Stepper */}
            <ol className="mt-5 grid grid-cols-3 gap-2">
              {STEPS.map((s, i) => (
                <li key={s}>
                  <button type="button" disabled={i > step} onClick={() => i < step && go(i)}
                    className={cx('w-full rounded-xl border px-2 py-2.5 text-left transition',
                      i === step ? 'border-glow-400/60 bg-glow-500/15' : i < step ? 'border-white/15 bg-white/5 hover:bg-white/10' : 'border-white/10 bg-white/[0.02]')}>
                    <span className={cx('flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
                      i < step ? 'bg-glow-500 text-ink-950' : i === step ? 'bg-white text-ink-950' : 'bg-white/10 text-slate-400')}>
                      {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
                    </span>
                    <span className={cx('mt-1.5 block text-xs font-semibold sm:text-sm', i <= step ? 'text-white' : 'text-slate-500')}>{s}</span>
                  </button>
                </li>
              ))}
            </ol>

            {/* Step 1: service */}
            {step === 0 && (
              <section className="mt-5 space-y-3 animate-fade-up">
                <h2 className="text-lg font-bold text-white">Choose a service</h2>
                {services.length === 0 && <div className="glass p-6"><Empty title="No services yet">This business hasn’t published any services.</Empty></div>}
                {services.map((s) => (
                  <button key={s.id} onClick={() => { setService(s); setSlot(null); go(1) }}
                    className={cx('glass group flex w-full items-center gap-4 p-4 text-left transition hover:-translate-y-0.5 hover:border-glow-400/50',
                      service?.id === s.id && 'border-glow-400/70 ring-2 ring-glow-400/30')}>
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-glow-500/30 to-brand-500/30 ring-1 ring-white/10">
                      <Scissors className="h-5 w-5 text-teal-200" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-white">{s.name}</p>
                      {s.description && <p className="mt-0.5 line-clamp-2 text-sm text-slate-300">{s.description}</p>}
                      <p className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-slate-400"><Clock className="h-3.5 w-3.5" />{s.duration_min} min</p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-lg font-bold text-white">{rupees(s.price)}</p>
                      <ArrowRight className="ml-auto mt-1 h-4 w-4 text-slate-500 transition group-hover:translate-x-1 group-hover:text-glow-400" />
                    </div>
                  </button>
                ))}
              </section>
            )}

            {/* Step 2: date + slot */}
            {step === 1 && service && (
              <section className="mt-5 animate-fade-up">
                {conflict && (
                  <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-400/50 bg-amber-500/15 p-4 text-amber-100 animate-pop">
                    <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                    <div><p className="font-semibold">Slot just taken</p><p className="text-sm">{conflict}</p></div>
                  </div>
                )}
                <h2 className="flex items-center gap-2 text-lg font-bold text-white"><CalendarDays className="h-5 w-5 text-glow-400" />Pick a date</h2>
                <div className="-mx-4 mt-3 flex snap-x gap-2 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
                  {days.map((d) => {
                    const p = dayParts(d)
                    const closed = !biz.open_weekdays.includes(weekdayIdx(d))
                    const active = d === date
                    return (
                      <button key={d} disabled={closed} onClick={() => { setDate(d); setSlot(null); setConflict('') }}
                        className={cx('flex w-16 shrink-0 snap-start flex-col items-center rounded-2xl border py-3 transition',
                          active ? 'border-transparent bg-gradient-to-b from-glow-400 to-teal-600 text-ink-950 shadow-lg shadow-teal-500/30'
                            : closed ? 'border-white/5 bg-white/[0.02] text-slate-600'
                              : 'border-white/15 bg-ink-800/70 text-slate-100 hover:border-glow-400/60')}>
                        <span className="text-[11px] font-bold uppercase">{d === biz.today ? 'Today' : p.dow}</span>
                        <span className="font-display text-xl font-bold">{p.day}</span>
                        <span className="text-[11px] font-medium">{closed ? 'Closed' : p.mon}</span>
                      </button>
                    )
                  })}
                </div>

                <div className="mt-5 flex items-center justify-between">
                  <h2 className="flex items-center gap-2 text-lg font-bold text-white"><Clock className="h-5 w-5 text-glow-400" />Free slots</h2>
                  <button onClick={() => loadSlots()} className="btn-ghost btn-sm"><RefreshCw className={cx('h-3.5 w-3.5', slotsLoading && 'animate-spin')} />Refresh</button>
                </div>
                <p className="mt-1 text-sm text-slate-300">{prettyDate(date, { long: true })} · {service.name} ({service.duration_min} min)</p>

                <div className="glass mt-3 p-4">
                  {slotsLoading && !slots ? <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
                    : !slots || slots.slots.length === 0 ? (
                      <Empty icon={Moon} title={slots?.closed ? 'Closed on this day' : 'No slots left'}>
                        {slots?.closed ? 'Please pick another date.' : 'All times for this day are taken or have passed. Try another date.'}
                      </Empty>
                    ) : slots.free_count === 0 ? (
                      <Empty icon={Moon} title="Fully booked">Every slot on this day is taken. Try another date.</Empty>
                    ) : (
                      <div className="space-y-5">
                        {Object.entries(groups).filter(([, l]) => l.length).map(([label, list]) => {
                          const Icon = label === 'Morning' ? Sunrise : label === 'Afternoon' ? Sun : Moon
                          return (
                            <div key={label}>
                              <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-300"><Icon className="h-3.5 w-3.5" />{label}</p>
                              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                                {list.map((s) => {
                                  const active = slot?.start_time === s.start_time
                                  return (
                                    <button key={s.start_time} disabled={!s.available} onClick={() => { setSlot(s); setConflict('') }}
                                      className={cx('rounded-xl border py-2.5 text-sm font-semibold transition',
                                        active ? 'border-transparent bg-white text-ink-950 shadow-lg ring-2 ring-glow-400'
                                          : s.available ? 'border-white/15 bg-ink-800/80 text-white hover:border-glow-400 hover:bg-glow-500/10'
                                            : 'cursor-not-allowed border-white/5 bg-transparent text-slate-600 line-through')}>
                                      {time12(s.label)}
                                    </button>
                                  )
                                })}
                              </div>
                            </div>
                          )
                        })}
                        <p className="flex items-center gap-2 text-xs text-slate-400"><span className="inline-block h-3 w-3 rounded border border-white/15 bg-ink-800" />Free
                          <span className="ml-3 text-slate-600 line-through">10:00</span>Taken</p>
                      </div>
                    )}
                </div>
              </section>
            )}

            {/* Step 3: details */}
            {step === 2 && service && slot && (
              <form id="details" onSubmit={book} className="mt-5 animate-fade-up">
                <h2 className="flex items-center gap-2 text-lg font-bold text-white"><User className="h-5 w-5 text-glow-400" />Your details</h2>
                <div className="glass mt-3 space-y-4 p-5">
                  <label className="block"><span className="label">Full name</span>
                    <input className="input" required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Priya Raman" autoComplete="name" /></label>
                  <label className="block"><span className="label">Mobile number</span>
                    <input className="input" required type="tel" inputMode="tel" pattern="\+?[0-9 \-]{7,20}" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="98765 43210" autoComplete="tel" /></label>
                  <label className="block"><span className="label">E-mail <span className="normal-case text-slate-500">(optional, for confirmation)</span></span>
                    <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@email.com" autoComplete="email" /></label>
                  <label className="block"><span className="label">Note <span className="normal-case text-slate-500">(optional)</span></span>
                    <textarea className="input min-h-[70px]" maxLength={500} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Anything we should know?" /></label>
                </div>
                <Summary service={service} date={date} slot={slot} className="mt-4" />
              </form>
            )}
          </>
        )}
      </div>

      {/* Sticky action bar */}
      {!done && step > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-white/10 bg-ink-950/85 backdrop-blur-xl">
          <div className="mx-auto flex max-w-2xl items-center gap-3 px-4 py-3 sm:px-6" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
            <button onClick={() => go(step - 1)} className="btn-ghost px-3" aria-label="Back"><ArrowLeft className="h-4 w-4" /></button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{service?.name} · {rupees(service?.price)}</p>
              <p className="truncate text-xs text-slate-300">{slot ? `${prettyDate(date)}, ${time12(slot.label)}` : 'Select a time'}</p>
            </div>
            {step === 1 && <button className="btn-teal px-5" disabled={!slot} onClick={() => go(2)}>Continue <ArrowRight className="h-4 w-4" /></button>}
            {step === 2 && <button form="details" className="btn-primary px-5" disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : <>Confirm booking <Check className="h-4 w-4" /></>}</button>}
          </div>
        </div>
      )}

      <div className="relative z-10 mt-10 flex justify-center opacity-80"><span className="mr-2 self-center text-xs text-slate-400">Powered by</span><Logo small /></div>
    </div>
  )
}

function Summary({ service, date, slot, className }) {
  return (
    <div className={cx('glass-soft grid grid-cols-3 divide-x divide-white/10 p-1 text-center', className)}>
      <div className="p-3"><p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Service</p><p className="mt-1 truncate text-sm font-semibold text-white">{service.name}</p></div>
      <div className="p-3"><p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">When</p><p className="mt-1 text-sm font-semibold text-white">{prettyDate(date)}<br />{time12(slot.label)}</p></div>
      <div className="p-3"><p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Price</p><p className="mt-1 text-sm font-semibold text-white">{rupees(service.price)}</p></div>
    </div>
  )
}

function Confirmation({ done, biz, service, onAgain }) {
  const start = done.start_time
  const date = start.slice(0, 10)
  const gcal = useMemo(() => {
    const fmt = (iso) => new Date(iso).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
    const p = new URLSearchParams({ action: 'TEMPLATE', text: `${done.service} at ${biz.name}`, dates: `${fmt(done.start_time)}/${fmt(done.end_time)}`, details: `Booking ID ${done.booking_id}`, location: biz.address || '' })
    return `https://calendar.google.com/calendar/render?${p}`
  }, [done, biz])
  return (
    <section className="glass mt-5 p-6 text-center animate-fade-up sm:p-8">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-glow-400 to-emerald-500 shadow-lg shadow-emerald-500/40 animate-pop">
        <CheckCircle2 className="h-10 w-10 text-ink-950" />
      </div>
      <h2 className="mt-5 text-2xl font-extrabold text-white">You’re booked!</h2>
      <p className="mt-2 text-slate-200">{done.message}</p>
      <div className="mx-auto mt-5 inline-flex flex-col rounded-2xl border border-dashed border-glow-400/50 bg-glow-500/10 px-6 py-3">
        <span className="text-[11px] font-bold uppercase tracking-widest text-teal-200">Booking ID</span>
        <span className="font-mono text-xl font-bold text-white">{done.booking_id}</span>
      </div>
      <div className="mx-auto mt-5 max-w-sm text-left">
        <Summary service={service || { name: done.service, price: 0 }} date={date} slot={{ label: wallTime(start) }} />
      </div>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
        {done.whatsapp_link && <a href={done.whatsapp_link} target="_blank" rel="noreferrer" className="btn bg-[#25D366] text-ink-950 hover:brightness-110"><MessageCircle className="h-4 w-4" />Send on WhatsApp</a>}
        <a href={gcal} target="_blank" rel="noreferrer" className="btn-ghost"><CalendarDays className="h-4 w-4" />Add to Google Calendar</a>
        <button onClick={onAgain} className="btn-ghost">Book another</button>
      </div>
      <p className="mt-4 text-xs text-slate-400">{done.notification === 'email' ? 'A confirmation e-mail is on its way.' : 'Please screenshot this page or save your booking ID.'}</p>
    </section>
  )
}
