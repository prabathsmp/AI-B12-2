import { useEffect, useState } from 'react'
import { Copy, Save } from 'lucide-react'
import { api } from '../../api'
import { PageLoader, Spinner, Toggle, useToast } from '../../components/ui'
import { cx, time12 } from '../../utils'
import { PageHeader } from './Layout'

export default function Hours() {
  const toast = useToast()
  const [days, setDays] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api('/working-hours').then(setDays).catch((e) => toast(e.message, 'error')) }, [toast])
  const upd = (i, patch) => setDays((d) => d.map((x, j) => (j === i ? { ...x, ...patch } : x)))

  const copyMonday = () => {
    const m = days[0]
    setDays((d) => d.map((x, i) => (i > 0 && i < 6 ? { ...x, is_open: m.is_open, open_time: m.open_time, close_time: m.close_time } : x)))
    toast("Copied Monday's hours to Tue–Sat", 'info')
  }

  const save = async () => {
    const bad = days.find((d) => d.is_open && d.close_time <= d.open_time)
    if (bad) return toast(`${bad.name}: closing time must be after opening time`, 'error')
    setBusy(true)
    try {
      setDays(await api('/working-hours', { method: 'PUT', body: { days: days.map(({ weekday, is_open, open_time, close_time }) => ({ weekday, is_open, open_time, close_time })) } }))
      toast('Working hours saved')
    } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }

  if (!days) return <PageLoader />
  const openCount = days.filter((d) => d.is_open).length
  const weekly = days.filter((d) => d.is_open).reduce((s, d) => {
    const [oh, om] = d.open_time.split(':').map(Number); const [ch, cm] = d.close_time.split(':').map(Number)
    return s + Math.max(0, ch * 60 + cm - oh * 60 - om)
  }, 0)

  return (
    <>
      <PageHeader title="Working hours" subtitle="Slots are only offered inside these hours. Existing bookings are not affected."
        actions={<><button className="btn-ghost" onClick={copyMonday}><Copy className="h-4 w-4" />Copy Mon → Sat</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : <><Save className="h-4 w-4" />Save hours</>}</button></>} />

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="glass divide-y divide-white/[0.07]">
          {days.map((d, i) => (
            <div key={d.weekday} className={cx('flex flex-wrap items-center gap-4 px-5 py-4', !d.is_open && 'bg-white/[0.015]')}>
              <div className="flex w-40 items-center gap-3">
                <Toggle checked={d.is_open} onChange={(v) => upd(i, { is_open: v })} label={`${d.name} open`} />
                <span className={cx('font-semibold', d.is_open ? 'text-white' : 'text-slate-500')}>{d.name}</span>
              </div>
              {d.is_open ? (
                <div className="flex flex-1 flex-wrap items-center gap-3">
                  <input type="time" step={900} className="input w-36" value={d.open_time} onChange={(e) => upd(i, { open_time: e.target.value })} aria-label={`${d.name} opens`} />
                  <span className="text-sm text-slate-400">to</span>
                  <input type="time" step={900} className="input w-36" value={d.close_time} onChange={(e) => upd(i, { close_time: e.target.value })} aria-label={`${d.name} closes`} />
                  <span className="ml-auto hidden text-sm text-slate-400 sm:block">{time12(d.open_time)} – {time12(d.close_time)}</span>
                </div>
              ) : <span className="chip bg-slate-500/15 text-slate-300 ring-slate-400/30">Closed</span>}
            </div>
          ))}
        </div>
        <div className="glass h-fit p-5">
          <p className="label">Week at a glance</p>
          <p className="mt-2 font-display text-4xl font-bold text-white">{Math.round(weekly / 60)}<span className="text-lg text-slate-400"> hrs</span></p>
          <p className="text-sm text-slate-300">open across {openCount} day{openCount === 1 ? '' : 's'}</p>
          <div className="mt-5 flex h-24 items-end gap-1.5">
            {days.map((d) => {
              const [oh, om] = d.open_time.split(':').map(Number); const [ch, cm] = d.close_time.split(':').map(Number)
              const mins = d.is_open ? Math.max(0, ch * 60 + cm - oh * 60 - om) : 0
              return (
                <div key={d.weekday} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t-md bg-gradient-to-t from-brand-600 to-glow-400" style={{ height: `${Math.max(4, (mins / 720) * 80)}px`, opacity: d.is_open ? 1 : 0.2 }} />
                  <span className="text-[10px] font-bold text-slate-400">{d.name.slice(0, 2)}</span>
                </div>
              )
            })}
          </div>
          <p className="mt-4 text-xs text-slate-400">Slots start every 15 minutes. A 45-min service at 10:00 blocks 10:00–10:45.</p>
        </div>
      </div>
    </>
  )
}
