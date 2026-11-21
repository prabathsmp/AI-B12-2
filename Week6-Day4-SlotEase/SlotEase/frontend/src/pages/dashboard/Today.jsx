import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Ban, CalendarCheck, CheckCircle2, ChevronLeft, ChevronRight, Clock, IndianRupee, MessageCircle, Phone, Plus, RotateCcw, UserX,
} from 'lucide-react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Empty, PageLoader, STATUS, StatCard, StatusChip, useToast } from '../../components/ui'
import WalkInModal from '../../components/WalkInModal'
import { addDays, cx, initials, pad, prettyDate, rupees, time12, wallTime, ymd } from '../../utils'
import { PageHeader } from './Layout'

const FILTERS = [['all', 'All'], ['booked', 'Booked'], ['completed', 'Completed'], ['no_show', 'No-show'], ['cancelled', 'Cancelled']]

export function useBusinessToday() {
  const { business } = useAuth()
  const [today, setToday] = useState(null)
  useEffect(() => {
    api(`/public/${business.slug}`, { auth: false }).then((b) => setToday(b.today)).catch(() => setToday(ymd(new Date())))
  }, [business.slug])
  return today
}

export default function Today() {
  const { business } = useAuth()
  const toast = useToast()
  const today = useBusinessToday()
  const [date, setDate] = useState(null)
  const [rows, setRows] = useState(null)
  const [month, setMonth] = useState(null)
  const [filter, setFilter] = useState('all')
  const [walkIn, setWalkIn] = useState(false)
  const [busyId, setBusyId] = useState(null)

  useEffect(() => { if (today && !date) setDate(today) }, [today, date])

  const load = useCallback(async () => {
    if (!date) return
    try { setRows(await api(`/appointments?date=${date}`)) } catch (e) { toast(e.message, 'error') }
  }, [date, toast])
  useEffect(() => { load() }, [load])
  useEffect(() => { if (date) api(`/stats?month=${date.slice(0, 7)}`).then(setMonth).catch(() => {}) }, [date, rows])

  const setStatus = async (a, status) => {
    setBusyId(a.id)
    try {
      const upd = await api(`/appointments/${a.id}`, { method: 'PATCH', body: { status } })
      setRows((r) => r.map((x) => (x.id === a.id ? { ...x, ...upd } : x)))
      toast(`${a.customer.name}: ${STATUS[status].label}`)
    } catch (e) { toast(e.message, 'error') } finally { setBusyId(null) }
  }

  const summary = useMemo(() => {
    const r = rows || []
    const live = r.filter((a) => a.status !== 'cancelled')
    return {
      total: live.length,
      noShows: r.filter((a) => a.status === 'no_show').length,
      completed: r.filter((a) => a.status === 'completed').length,
      revenue: r.filter((a) => a.status === 'completed' || a.status === 'booked').reduce((s, a) => s + a.service.price, 0),
    }
  }, [rows])

  const nextUp = useMemo(() => {
    if (!rows || date !== today) return null
    const d = new Date()
    const now = `${pad(d.getHours())}:${pad(d.getMinutes())}`
    return rows.find((a) => a.status === 'booked' && wallTime(a.end_time) > now)
  }, [rows, date, today])

  if (!date) return <PageLoader />
  const visible = (rows || []).filter((a) => filter === 'all' || a.status === filter)

  return (
    <>
      <PageHeader
        title={date === today ? `Today, ${prettyDate(date)}` : prettyDate(date, { long: true })}
        subtitle={`${business.name} · run your day from here`}
        actions={<>
          <div className="flex items-center rounded-xl border border-white/15 bg-white/5 p-1">
            <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setDate(addDays(date, -1))} aria-label="Previous day"><ChevronLeft className="h-4 w-4" /></button>
            <button className={cx('rounded-lg px-3 py-1 text-sm font-semibold', date === today ? 'bg-white/15 text-white' : 'text-slate-300 hover:text-white')} onClick={() => setDate(today)}>Today</button>
            <input type="date" className="bg-transparent px-2 text-sm text-slate-200 outline-none" value={date} onChange={(e) => e.target.value && setDate(e.target.value)} />
            <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setDate(addDays(date, 1))} aria-label="Next day"><ChevronRight className="h-4 w-4" /></button>
          </div>
          <button className="btn-primary" onClick={() => setWalkIn(true)}><Plus className="h-4 w-4" />Add booking</button>
        </>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={CalendarCheck} label="Bookings" value={summary.total} hint="excluding cancelled" />
        <StatCard icon={CheckCircle2} tone="teal" label="Completed" value={summary.completed} />
        <StatCard icon={UserX} tone="rose" label="No-shows" value={summary.noShows} />
        <StatCard icon={IndianRupee} tone="amber" label="Est. revenue" value={rupees(summary.revenue)} hint="completed + booked" />
      </div>

      {month && (
        <div className="glass-soft mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 px-4 py-3 text-sm text-slate-200">
          <span className="font-semibold text-white">This month:</span>
          <span><b className="text-white">{month.total_bookings}</b> bookings</span>
          <span>No-show rate <b className="text-white">{month.no_show_rate}%</b></span>
          {month.busiest_day && <span>Busiest day: <b className="text-white">{month.busiest_day}</b></span>}
        </div>
      )}

      {nextUp && (
        <div className="mt-5 flex flex-wrap items-center gap-4 rounded-2xl border border-glow-400/40 bg-gradient-to-r from-glow-500/20 to-brand-500/10 p-4 animate-fade-up">
          <div className="rounded-xl bg-glow-500 p-2.5 text-ink-950"><Clock className="h-5 w-5" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-wider text-teal-200">Up next</p>
            <p className="truncate font-semibold text-white">{time12(wallTime(nextUp.start_time))} · {nextUp.customer.name} — {nextUp.service.name}</p>
          </div>
          <a href={nextUp.whatsapp_link} target="_blank" rel="noreferrer" className="btn btn-sm bg-[#25D366] text-ink-950"><MessageCircle className="h-3.5 w-3.5" />Remind</a>
        </div>
      )}

      <div className="glass mt-5 overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-4 py-3">
          {FILTERS.map(([v, l]) => {
            const n = v === 'all' ? (rows || []).length : (rows || []).filter((a) => a.status === v).length
            return (
              <button key={v} onClick={() => setFilter(v)} className={cx('rounded-lg px-3 py-1.5 text-sm font-semibold transition', filter === v ? 'bg-white text-ink-950' : 'text-slate-300 hover:bg-white/10 hover:text-white')}>
                {l} <span className={cx('ml-1 text-xs', filter === v ? 'text-ink-700' : 'text-slate-500')}>{n}</span>
              </button>
            )
          })}
        </div>

        {!rows ? <PageLoader /> : visible.length === 0 ? (
          <div className="p-6"><Empty icon={CalendarCheck} title="No appointments" action={<button className="btn-primary" onClick={() => setWalkIn(true)}><Plus className="h-4 w-4" />Add booking</button>}>
            {filter === 'all' ? 'Nothing booked for this day yet. Share your booking link!' : 'No appointments with this status.'}</Empty></div>
        ) : (
          <ul className="divide-y divide-white/[0.07]">
            {visible.map((a) => (
              <li key={a.id} className={cx('flex flex-col gap-3 px-4 py-4 transition hover:bg-white/[0.03] sm:flex-row sm:items-center', a.status === 'cancelled' && 'opacity-60')}>
                <div className="flex min-w-0 flex-1 items-center gap-4">
                  <div className="w-20 shrink-0">
                    <p className="font-display text-lg font-bold text-white">{time12(wallTime(a.start_time))}</p>
                    <p className="text-xs text-slate-400">to {time12(wallTime(a.end_time))}</p>
                  </div>
                  <div className={cx('h-10 w-1 shrink-0 rounded-full', STATUS[a.status].dot)} />
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500/40 to-glow-500/30 text-sm font-bold text-white ring-1 ring-white/15">{initials(a.customer.name)}</div>
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">{a.customer.name}</p>
                    <p className="truncate text-sm text-slate-300">{a.service.name} · {rupees(a.service.price)}</p>
                    <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
                      <span className="font-mono">{a.booking_id}</span>
                      {a.source === 'walk_in' && <span className="rounded bg-amber-500/15 px-1.5 text-amber-200">walk-in</span>}
                      {a.notes && <span className="truncate italic">“{a.notes}”</span>}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                  <StatusChip status={a.status} />
                  {a.status === 'booked' ? (
                    <>
                      <button disabled={busyId === a.id} onClick={() => setStatus(a, 'completed')} className="btn btn-sm bg-emerald-500 text-ink-950 hover:bg-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" />Complete</button>
                      <button disabled={busyId === a.id} onClick={() => setStatus(a, 'no_show')} className="btn btn-sm border border-rose-400/50 bg-rose-500/15 text-rose-100 hover:bg-rose-500/30"><UserX className="h-3.5 w-3.5" />No-show</button>
                      <button disabled={busyId === a.id} onClick={() => setStatus(a, 'cancelled')} className="btn-ghost btn-sm" title="Cancel"><Ban className="h-3.5 w-3.5" /></button>
                    </>
                  ) : (
                    <button disabled={busyId === a.id} onClick={() => setStatus(a, 'booked')} className="btn-ghost btn-sm" title="Undo"><RotateCcw className="h-3.5 w-3.5" />Undo</button>
                  )}
                  <a href={`tel:${a.customer.phone}`} className="btn-ghost btn-sm" title={a.customer.phone}><Phone className="h-3.5 w-3.5" /></a>
                  <a href={a.whatsapp_link} target="_blank" rel="noreferrer" className="btn btn-sm border border-[#25D366]/40 bg-[#25D366]/10 text-[#7ef0a8] hover:bg-[#25D366]/20" title="WhatsApp"><MessageCircle className="h-3.5 w-3.5" /></a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <WalkInModal open={walkIn} onClose={() => setWalkIn(false)} date={date} onCreated={load} />
    </>
  )
}
