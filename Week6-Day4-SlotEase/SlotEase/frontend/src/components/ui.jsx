import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cx } from '../utils'

/* ---------- Background ---------- */
export function Aurora({ variant = 'default' }) {
  const tealTop = variant === 'booking'
  return (
    <div className="aurora" aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,#1a1446_0%,#060914_55%)]" />
      <div className="blob animate-float" style={{ width: 520, height: 520, top: -160, left: -120, background: tealTop ? '#0d9488' : '#7c3aed' }} />
      <div className="blob animate-float-slow" style={{ width: 460, height: 460, top: 80, right: -140, background: tealTop ? '#7c3aed' : '#c026d3', opacity: 0.35 }} />
      <div className="blob animate-float" style={{ width: 600, height: 600, bottom: -300, left: '30%', background: '#0e7490', opacity: 0.28 }} />
      <div className="grid" />
      <div className="noise" />
    </div>
  )
}

/* ---------- Logo ---------- */
export function Logo({ to = '/', small = false }) {
  return (
    <Link to={to} className="group inline-flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className={cx('transition group-hover:rotate-[-6deg]', small ? 'h-8 w-8' : 'h-9 w-9')} />
      <span className={cx('font-display font-extrabold tracking-tight text-white', small ? 'text-lg' : 'text-xl')}>
        Slot<span className="gradient-text">Ease</span>
      </span>
    </Link>
  )
}

/* ---------- Spinner / Empty ---------- */
export const Spinner = ({ className = 'h-5 w-5' }) => <Loader2 className={cx('animate-spin text-brand-300', className)} />

export function PageLoader({ label = 'Loading…' }) {
  return <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-slate-300"><Spinner className="h-8 w-8" />{label}</div>
}

export function Empty({ icon: Icon = Info, title, children, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-white/15 px-6 py-12 text-center">
      <div className="rounded-2xl bg-brand-500/15 p-3 text-brand-300 ring-1 ring-brand-400/30"><Icon className="h-6 w-6" /></div>
      <h3 className="text-lg font-bold text-white">{title}</h3>
      {children && <p className="max-w-sm text-sm text-slate-300">{children}</p>}
      {action}
    </div>
  )
}

/* ---------- Status chip ---------- */
export const STATUS = {
  booked: { label: 'Booked', cls: 'bg-sky-500/15 text-sky-200 ring-sky-400/40', dot: 'bg-sky-400', bar: 'border-sky-400 bg-sky-500/20' },
  completed: { label: 'Completed', cls: 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/40', dot: 'bg-emerald-400', bar: 'border-emerald-400 bg-emerald-500/20' },
  no_show: { label: 'No-show', cls: 'bg-rose-500/15 text-rose-200 ring-rose-400/40', dot: 'bg-rose-400', bar: 'border-rose-400 bg-rose-500/20' },
  cancelled: { label: 'Cancelled', cls: 'bg-slate-500/15 text-slate-300 ring-slate-400/30', dot: 'bg-slate-400', bar: 'border-slate-500 bg-slate-500/15' },
}
export function StatusChip({ status }) {
  const s = STATUS[status] || STATUS.booked
  return <span className={cx('chip', s.cls)}><span className={cx('h-1.5 w-1.5 rounded-full', s.dot)} />{s.label}</span>
}

/* ---------- Stat card ---------- */
export function StatCard({ icon: Icon, label, value, hint, tone = 'brand' }) {
  const tones = {
    brand: 'from-brand-500/25 text-brand-200 ring-brand-400/30',
    teal: 'from-glow-500/25 text-teal-200 ring-teal-400/30',
    rose: 'from-rose-500/25 text-rose-200 ring-rose-400/30',
    amber: 'from-amber-500/25 text-amber-200 ring-amber-400/30',
    sky: 'from-sky-500/25 text-sky-200 ring-sky-400/30',
  }
  return (
    <div className="glass relative overflow-hidden p-5 animate-fade-up">
      <div className={cx('absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br to-transparent blur-xl', tones[tone])} />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">{label}</p>
          <p className="mt-2 font-display text-3xl font-bold text-white">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
        </div>
        {Icon && <div className={cx('rounded-xl bg-gradient-to-br p-2.5 ring-1', tones[tone])}><Icon className="h-5 w-5" /></div>}
      </div>
    </div>
  )
}

/* ---------- Modal ---------- */
export function Modal({ open, onClose, title, children, footer, wide }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div className="absolute inset-0 bg-ink-950/75 backdrop-blur-sm" onClick={onClose} />
      <div className={cx('glass relative max-h-[92vh] w-full overflow-y-auto rounded-b-none bg-ink-900/95 p-6 animate-fade-up sm:rounded-2xl', wide ? 'max-w-2xl' : 'max-w-lg')}>
        <div className="mb-5 flex items-center justify-between gap-4">
          <h3 className="text-xl font-bold text-white">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        {children}
        {footer && <div className="mt-6 flex flex-wrap justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}

/* ---------- Toasts ---------- */
const ToastCtx = createContext(() => {})
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200)
  }, [])
  const icons = { success: CheckCircle2, error: AlertTriangle, info: Info }
  const tones = {
    success: 'border-emerald-400/40 text-emerald-100',
    error: 'border-rose-400/50 text-rose-100',
    info: 'border-brand-400/40 text-brand-100',
  }
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
        {toasts.map((t) => {
          const I = icons[t.type]
          return (
            <div key={t.id} className={cx('pointer-events-auto flex items-start gap-3 rounded-xl border bg-ink-800/95 px-4 py-3 text-sm shadow-glass backdrop-blur animate-fade-up', tones[t.type])}>
              <I className="mt-0.5 h-4 w-4 shrink-0" /><span className="text-slate-100">{t.message}</span>
            </div>
          )
        })}
      </div>
    </ToastCtx.Provider>
  )
}
export const useToast = () => useContext(ToastCtx)

/* ---------- Field ---------- */
export function Field({ label, hint, children, className }) {
  return (
    <label className={cx('block', className)}>
      {label && <span className="label">{label}</span>}
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  )
}

export function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
      className={cx('relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition', checked ? 'bg-gradient-to-r from-brand-500 to-fuchsia-500' : 'bg-white/15')}>
      <span className={cx('inline-block h-5 w-5 transform rounded-full bg-white shadow transition', checked ? 'translate-x-5' : 'translate-x-0.5')} />
    </button>
  )
}
