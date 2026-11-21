import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, CalendarCheck, ChevronLeft, ChevronRight, Flame, IndianRupee, Lightbulb, Repeat, Sparkles, UserX } from 'lucide-react'
import { aiHeaders, api, getAiSettings } from '../../api'
import { PageLoader, Spinner, StatCard, useToast } from '../../components/ui'
import { cx, monthLabel, rupees, shiftMonth } from '../../utils'
import { PageHeader } from './Layout'
import { useBusinessToday } from './Today'

export default function Stats() {
  const toast = useToast()
  const today = useBusinessToday()
  const [month, setMonth] = useState(null)
  const [s, setS] = useState(null)
  const [ai, setAi] = useState({ busy: false, answer: '', question: '' })
  const ai_cfg = getAiSettings()

  useEffect(() => { if (today && !month) setMonth(today.slice(0, 7)) }, [today, month])
  useEffect(() => {
    if (!month) return
    setS(null); setAi((a) => ({ ...a, answer: '' }))
    api(`/stats?month=${month}`).then(setS).catch((e) => toast(e.message, 'error'))
  }, [month, toast])

  const askAi = async () => {
    setAi((a) => ({ ...a, busy: true }))
    try {
      const r = await api('/ai/insights', { method: 'POST', headers: aiHeaders(), body: { month, model: ai_cfg.model || 'gpt-4o-mini', question: ai.question || null } })
      setAi((a) => ({ ...a, busy: false, answer: r.answer }))
    } catch (e) { toast(e.message, 'error'); setAi((a) => ({ ...a, busy: false })) }
  }

  if (!month || !s) return <PageLoader />
  const maxDay = Math.max(1, ...s.daily.map((d) => d.bookings))
  const maxWd = Math.max(1, ...s.weekday.map((d) => d.bookings))
  const resolved = s.completed + s.no_shows + s.cancelled + s.upcoming || 1
  const seg = [[s.completed, '#34d399'], [s.upcoming, '#38bdf8'], [s.no_shows, '#fb7185'], [s.cancelled, '#64748b']]
  let acc = 0
  const conic = seg.map(([v, c]) => { const a = acc; acc += (v / resolved) * 100; return `${c} ${a}% ${acc}%` }).join(', ')

  return (
    <>
      <PageHeader title="Stats & insights" subtitle="How your business is doing — the numbers that keep the lights on."
        actions={<div className="flex items-center rounded-xl border border-white/15 bg-white/5 p-1">
          <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setMonth(shiftMonth(month, -1))} aria-label="Previous month"><ChevronLeft className="h-4 w-4" /></button>
          <span className="px-3 text-sm font-semibold text-white">{monthLabel(month)}</span>
          <button className="rounded-lg p-1.5 text-slate-200 hover:bg-white/10" onClick={() => setMonth(shiftMonth(month, 1))} aria-label="Next month"><ChevronRight className="h-4 w-4" /></button>
        </div>} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={CalendarCheck} label="Bookings" value={s.total_bookings} hint={`${s.upcoming} still upcoming`} />
        <StatCard icon={UserX} tone="rose" label="No-show rate" value={`${s.no_show_rate}%`} hint={`${s.no_shows} of ${s.completed + s.no_shows} attended slots`} />
        <StatCard icon={IndianRupee} tone="amber" label="Revenue estimate" value={rupees(s.revenue_estimate)} hint={`${rupees(s.revenue_completed)} already earned`} />
        <StatCard icon={Flame} tone="teal" label="Busiest day" value={s.busiest_day || '—'} hint={s.peak_hour != null ? `peak around ${s.peak_hour % 12 || 12} ${s.peak_hour < 12 ? 'AM' : 'PM'}` : undefined} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="glass p-5 lg:col-span-2">
          <p className="label">Bookings per day</p>
          <div className="mt-4 flex h-48 items-end gap-[3px]">
            {s.daily.map((d) => (
              <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end">
                <div className="w-full rounded-t bg-gradient-to-t from-brand-600 via-fuchsia-500 to-glow-400 transition group-hover:brightness-125"
                  style={{ height: `${(d.bookings / maxDay) * 100}%`, minHeight: d.bookings ? 4 : 1, opacity: d.bookings ? 1 : 0.15 }} />
                <span className="pointer-events-none absolute -top-7 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-white px-2 py-0.5 text-[11px] font-bold text-ink-950 group-hover:block">{d.day}: {d.bookings}</span>
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-slate-400"><span>1</span><span>{Math.ceil(s.daily.length / 2)}</span><span>{s.daily.length}</span></div>
        </div>

        <div className="glass p-5">
          <p className="label">Status mix</p>
          <div className="mt-4 flex items-center gap-5">
            <div className="relative h-32 w-32 shrink-0 rounded-full" style={{ background: `conic-gradient(${conic})` }}>
              <div className="absolute inset-4 flex flex-col items-center justify-center rounded-full bg-ink-900">
                <span className="font-display text-2xl font-bold text-white">{s.completed + s.no_shows + s.cancelled + s.upcoming}</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400">total</span>
              </div>
            </div>
            <ul className="space-y-2 text-sm">
              {[['Completed', s.completed, 'bg-emerald-400'], ['Upcoming', s.upcoming, 'bg-sky-400'], ['No-show', s.no_shows, 'bg-rose-400'], ['Cancelled', s.cancelled, 'bg-slate-500']].map(([l, v, c]) => (
                <li key={l} className="flex items-center gap-2 text-slate-200"><span className={cx('h-2.5 w-2.5 rounded-sm', c)} />{l}<b className="ml-auto pl-3 text-white">{v}</b></li>
              ))}
            </ul>
          </div>
          <div className="mt-5 flex items-center gap-3 rounded-xl bg-white/5 p-3 text-sm text-slate-200"><Repeat className="h-4 w-4 text-brand-300" />
            <span><b className="text-white">{s.repeat_customers}</b> of {s.unique_customers} customers came back</span></div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="glass p-5">
          <p className="label">By weekday</p>
          <div className="mt-4 space-y-2.5">
            {s.weekday.map((d) => (
              <div key={d.weekday} className="flex items-center gap-3 text-sm">
                <span className="w-9 font-semibold text-slate-300">{d.weekday}</span>
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-gradient-to-r from-glow-500 to-brand-500" style={{ width: `${(d.bookings / maxWd) * 100}%` }} /></div>
                <span className="w-8 text-right font-semibold text-white">{d.bookings}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass p-5 lg:col-span-2">
          <p className="label">Top services</p>
          {s.services.length === 0 ? <p className="mt-4 text-sm text-slate-400">No bookings this month.</p> : (
            <table className="mt-3 w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-400"><th className="py-2 font-semibold">Service</th><th className="py-2 text-right font-semibold">Bookings</th><th className="py-2 text-right font-semibold">Revenue</th></tr></thead>
              <tbody className="divide-y divide-white/[0.07]">
                {s.services.map((x) => (
                  <tr key={x.name}><td className="py-2.5 font-medium text-white">{x.name}</td><td className="py-2.5 text-right text-slate-200">{x.bookings}</td><td className="py-2.5 text-right font-semibold text-white">{rupees(x.revenue)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="glass p-5">
          <p className="label flex items-center gap-2"><Lightbulb className="h-4 w-4 text-amber-300" />Quick insights</p>
          <ul className="mt-3 space-y-2">
            {s.insights.length ? s.insights.map((t) => (
              <li key={t} className="flex gap-3 rounded-xl bg-white/[0.04] px-3 py-2.5 text-sm text-slate-100"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-300" />{t}</li>
            )) : <li className="text-sm text-slate-400">Insights appear once you have bookings.</li>}
          </ul>
        </div>

        <div className="glass relative overflow-hidden p-5">
          <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-fuchsia-500/25 blur-3xl" />
          <p className="label relative flex items-center gap-2"><Bot className="h-4 w-4 text-fuchsia-300" />AI business coach <span className="chip bg-fuchsia-500/15 text-fuchsia-200 ring-fuchsia-400/30 normal-case tracking-normal">optional</span></p>
          {!ai_cfg.key ? (
            <div className="relative mt-3 text-sm text-slate-300">
              Plug in your own OpenAI API key to get tailored advice from this month’s numbers. Everything else works without it.
              <Link to="/dashboard/settings" className="btn-ghost btn-sm mt-3 w-fit"><Sparkles className="h-3.5 w-3.5" />Add API key in Settings</Link>
            </div>
          ) : (
            <div className="relative mt-3 space-y-3">
              <input className="input" placeholder="Ask anything, e.g. How do I fill weekday mornings?" value={ai.question} onChange={(e) => setAi({ ...ai, question: e.target.value })} />
              <button className="btn-primary" onClick={askAi} disabled={ai.busy}>{ai.busy ? <Spinner className="h-4 w-4 text-white" /> : <Sparkles className="h-4 w-4" />}Get AI advice</button>
              {ai.answer && <div className="whitespace-pre-wrap rounded-xl border border-fuchsia-400/30 bg-fuchsia-500/10 p-4 text-sm leading-relaxed text-slate-100 animate-fade-up">{ai.answer}</div>}
              <p className="text-xs text-slate-400">Model: {ai_cfg.model || 'gpt-4o-mini'} · aggregated stats only, no customer names or phones are sent.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
