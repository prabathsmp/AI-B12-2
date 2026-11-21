import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, MessageCircle, Plus } from 'lucide-react'
import { api } from '../../api'
import { Modal, PageLoader, STATUS, StatusChip, useToast } from '../../components/ui'
import WalkInModal from '../../components/WalkInModal'
import { addDays, cx, dayParts, minutesOf, mondayOf, prettyDate, rupees, time12, wallDate, wallTime } from '../../utils'
import { PageHeader } from './Layout'
import { useBusinessToday } from './Today'

const HOUR_PX = 64

export default function Calendar() {
  const toast = useToast()
  const today = useBusinessToday()
  const [weekStart, setWeekStart] = useState(null)
  const [rows, setRows] = useState(null)
  const [hours, setHours] = useState(null)
  const [selected, setSelected] = useState(null)
  const [walkIn, setWalkIn] = useState(null)

  useEffect(() => { if (today && !weekStart) setWeekStart(mondayOf(today)) }, [today, weekStart])
  useEffect(() => { api('/working-hours').then(setHours).catch(() => {}) }, [])

  const load = useCallback(async () => {
    if (!weekStart) return
    setRows(null)
    try { setRows(await api(`/appointments?from=${weekStart}&to=${addDays(weekStart, 6)}`)) } catch (e) { toast(e.message, 'error') }
  }, [weekStart, toast])
  useEffect(() => { load() }, [load])

  const days = useMemo(() => (weekStart ? Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)) : []), [weekStart])

  const [startH, endH] = useMemo(() => {
    const open = (hours || []).filter((h) => h.is_open)
    let s = open.length ? Math.min(...open.map((h) => Number(h.open_time.slice(0, 2)))) : 9
    let e = open.length ? Math.max(...open.map((h) => Math.ceil(Number(h.close_time.slice(0, 2)) + Number(h.close_time.slice(3)) / 60))) : 18
    for (const a of rows || []) { s = Math.min(s, Math.floor(minutesOf(a.start_time) / 60)); e = Math.max(e, Math.ceil(minutesOf(a.end_time) / 60)) }
    return [s, Math.max(e, s + 1)]
  }, [hours, rows])

  const byDay = useMemo(() => {
    const m = {}
    for (const a of rows || []) (m[wallDate(a.start_time)] ||= []).push(a)
    return m
  }, [rows])

  const setStatus = async (status) => {
    try {
      const upd = await api(`/appointments/${selected.id}`, { method: 'PATCH', body: { status } })
      setRows((r) => r.map((x) => (x.id === upd.id ? { ...x, ...upd } : x)))
      setSelected(null); toast(`Marked ${STATUS[status].label}`)
    } catch (e) { toast(e.message, 'error') }
  }

  if (!weekStart || !hours) return <PageLoader />
  const total = (rows || []).filter((a) => a.status !== 'cancelled').length

  return (
    <>
      <PageHeader title="Weekly calendar" subtitle={`${prettyDate(days[0])} – ${prettyDate(days[6])} · ${total} bookings`}
        actions={<>
          <div className="flex items-center rounded-xl border border-white/15 bg-white/5 p-1">
            <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Previous week"><ChevronLeft className="h-4 w-4" /></button>
            <button className="rounded-lg px-3 py-1 text-sm font-semibold text-slate-200 hover:text-white" onClick={() => setWeekStart(mondayOf(today))}>This week</button>
            <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Next week"><ChevronRight className="h-4 w-4" /></button>
          </div>
          <button className="btn-primary" onClick={() => setWalkIn(today)}><Plus className="h-4 w-4" />Add booking</button>
        </>} />

      <div className="mb-3 flex flex-wrap gap-3 text-xs text-slate-300">
        {Object.entries(STATUS).map(([k, v]) => <span key={k} className="inline-flex items-center gap-1.5"><span className={cx('h-2.5 w-2.5 rounded-sm', v.dot)} />{v.label}</span>)}
      </div>

      <div className="glass overflow-x-auto">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-[56px_repeat(7,1fr)] border-b border-white/10">
            <div />
            {days.map((d) => {
              const p = dayParts(d)
              const closed = !hours.find((h) => h.weekday === (p.jsDay + 6) % 7)?.is_open
              const count = (byDay[d] || []).filter((a) => a.status !== 'cancelled').length
              return (
                <button key={d} onClick={() => setWalkIn(d)} className={cx('group border-l border-white/10 px-2 py-3 text-left transition hover:bg-white/5', d === today && 'bg-brand-500/10')}>
                  <p className={cx('text-xs font-bold uppercase', d === today ? 'text-brand-200' : 'text-slate-400')}>{p.dow}</p>
                  <p className="flex items-baseline gap-2"><span className={cx('font-display text-xl font-bold', d === today ? 'text-white' : 'text-slate-100')}>{p.day}</span>
                    <span className="text-xs text-slate-400">{closed ? 'Closed' : `${count} booked`}</span>
                    <Plus className="ml-auto h-3.5 w-3.5 text-slate-500 opacity-0 transition group-hover:opacity-100" /></p>
                </button>
              )
            })}
          </div>

          {!rows ? <PageLoader /> : (
            <div className="relative grid grid-cols-[56px_repeat(7,1fr)]" style={{ height: (endH - startH) * HOUR_PX }}>
              <div className="relative">
                {Array.from({ length: endH - startH }, (_, i) => (
                  <span key={i} className="absolute right-2 -translate-y-2 text-[11px] font-medium text-slate-400" style={{ top: i * HOUR_PX }}>{i === 0 ? '' : time12(`${startH + i}:00`).replace(':00', '')}</span>
                ))}
              </div>
              {days.map((d) => {
                const wh = hours.find((h) => h.weekday === (dayParts(d).jsDay + 6) % 7)
                const toPx = (min) => ((min - startH * 60) / 60) * HOUR_PX
                return (
                  <div key={d} className={cx('relative border-l border-white/10', d === today && 'bg-brand-500/[0.05]')}>
                    {Array.from({ length: endH - startH }, (_, i) => <div key={i} className="absolute inset-x-0 border-t border-white/[0.06]" style={{ top: i * HOUR_PX }} />)}
                    {/* closed shading */}
                    {!wh?.is_open ? <div className="absolute inset-0 bg-[repeating-linear-gradient(135deg,rgba(255,255,255,.03)_0_8px,transparent_8px_16px)]" /> : (<>
                      <div className="absolute inset-x-0 top-0 bg-black/25" style={{ height: Math.max(0, toPx(Number(wh.open_time.slice(0, 2)) * 60 + Number(wh.open_time.slice(3)))) }} />
                      <div className="absolute inset-x-0 bottom-0 bg-black/25" style={{ top: toPx(Number(wh.close_time.slice(0, 2)) * 60 + Number(wh.close_time.slice(3))) }} />
                    </>)}
                    {(byDay[d] || []).map((a) => {
                      const top = toPx(minutesOf(a.start_time))
                      const h = Math.max(22, toPx(minutesOf(a.end_time)) - top - 2)
                      return (
                        <button key={a.id} onClick={() => setSelected(a)} style={{ top: top + 1, height: h }}
                          className={cx('absolute inset-x-1 overflow-hidden rounded-lg border-l-[3px] px-2 py-1 text-left text-[11px] leading-tight text-white shadow-md backdrop-blur transition hover:z-10 hover:brightness-125', STATUS[a.status].bar, a.status === 'cancelled' && 'opacity-50 line-through')}>
                          <p className="truncate font-bold">{wallTime(a.start_time)} {a.customer.name}</p>
                          {h > 34 && <p className="truncate text-slate-200">{a.service.name}</p>}
                        </button>
                      )
                    })}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.customer.name}
        footer={selected && <>
          {selected.status !== 'completed' && <button className="btn bg-emerald-500 text-ink-950 hover:bg-emerald-400" onClick={() => setStatus('completed')}>Complete</button>}
          {selected.status !== 'no_show' && <button className="btn border border-rose-400/50 bg-rose-500/15 text-rose-100" onClick={() => setStatus('no_show')}>No-show</button>}
          {selected.status !== 'cancelled' && <button className="btn-ghost" onClick={() => setStatus('cancelled')}>Cancel booking</button>}
          {selected.status !== 'booked' && <button className="btn-ghost" onClick={() => setStatus('booked')}>Reset to booked</button>}
        </>}>
        {selected && (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div><dt className="label">Status</dt><dd><StatusChip status={selected.status} /></dd></div>
            <div><dt className="label">Booking ID</dt><dd className="font-mono text-white">{selected.booking_id}</dd></div>
            <div><dt className="label">Service</dt><dd className="text-white">{selected.service.name} · {rupees(selected.service.price)}</dd></div>
            <div><dt className="label">When</dt><dd className="text-white">{prettyDate(wallDate(selected.start_time))}, {time12(wallTime(selected.start_time))}–{time12(wallTime(selected.end_time))}</dd></div>
            <div><dt className="label">Phone</dt><dd><a className="text-teal-200 hover:underline" href={`tel:${selected.customer.phone}`}>{selected.customer.phone}</a></dd></div>
            <div><dt className="label">WhatsApp</dt><dd><a className="inline-flex items-center gap-1 text-[#7ef0a8] hover:underline" href={selected.whatsapp_link} target="_blank" rel="noreferrer"><MessageCircle className="h-4 w-4" />Message</a></dd></div>
            {selected.notes && <div className="col-span-2"><dt className="label">Note</dt><dd className="text-slate-200">{selected.notes}</dd></div>}
          </dl>
        )}
      </Modal>
      <WalkInModal open={!!walkIn} onClose={() => setWalkIn(null)} date={walkIn || today} onCreated={load} />
    </>
  )
}
