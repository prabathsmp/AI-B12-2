import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  BarChart3, CalendarDays, Clock4, Copy, ExternalLink, LayoutDashboard, LogOut, Menu, Settings, Sparkles, Tags, Users, X,
} from 'lucide-react'
import { useAuth } from '../../auth'
import { Aurora, Logo, useToast } from '../../components/ui'
import { cx, initials } from '../../utils'

const NAV = [
  { to: '/dashboard', end: true, icon: LayoutDashboard, label: 'Today' },
  { to: '/dashboard/calendar', icon: CalendarDays, label: 'Calendar' },
  { to: '/dashboard/services', icon: Tags, label: 'Services' },
  { to: '/dashboard/hours', icon: Clock4, label: 'Working hours' },
  { to: '/dashboard/customers', icon: Users, label: 'Customers' },
  { to: '/dashboard/stats', icon: BarChart3, label: 'Stats & insights' },
  { to: '/dashboard/settings', icon: Settings, label: 'Settings' },
]

export default function DashboardLayout() {
  const { business, user, logout } = useAuth()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const link = `${window.location.origin}/${business.slug}`

  const copy = async () => {
    try { await navigator.clipboard.writeText(link); toast('Booking link copied') } catch { toast(link, 'info') }
  }

  const Sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-5 py-5"><Logo to="/dashboard" small />
        <button className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
      </div>
      <div className="mx-4 mb-4 rounded-xl border border-white/10 bg-gradient-to-br from-brand-600/30 to-glow-500/10 p-4">
        <p className="text-[11px] font-bold uppercase tracking-wider text-brand-200">Your business</p>
        <p className="mt-1 truncate font-display text-base font-bold text-white">{business.name}</p>
        <p className="mt-0.5 inline-flex items-center gap-1 text-xs text-slate-300"><Sparkles className="h-3 w-3 text-amber-300" /> {business.plan} plan · ₹499/mo</p>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ to, end, icon: I, label }) => (
          <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
            className={({ isActive }) => cx('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition',
              isActive ? 'bg-white/10 text-white shadow-glass ring-1 ring-white/15' : 'text-slate-300 hover:bg-white/5 hover:text-white')}>
            {({ isActive }) => (<><I className={cx('h-[18px] w-[18px]', isActive ? 'text-brand-300' : 'text-slate-400')} />{label}
              {isActive && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gradient-to-r from-brand-400 to-glow-400" />}</>)}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-sm font-bold text-white">{initials(business.name)}</div>
        <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-white">{user.email}</p><p className="text-xs capitalize text-slate-400">{user.role}</p></div>
        <button onClick={logout} className="rounded-lg p-2 text-slate-300 hover:bg-rose-500/15 hover:text-rose-200" title="Log out" aria-label="Log out"><LogOut className="h-4 w-4" /></button>
      </div>
    </div>
  )

  return (
    <div className="relative min-h-screen">
      <Aurora />
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-white/10 bg-ink-950/70 backdrop-blur-xl lg:block">{Sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-white/10 bg-ink-950/95 animate-fade-up">{Sidebar}</aside>
        </div>
      )}
      <div className="relative z-10 lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/70 backdrop-blur-xl">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
            <button className="rounded-lg p-2 text-slate-200 hover:bg-white/10 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
            <div className="hidden min-w-0 flex-1 items-center gap-2 sm:flex">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Booking link</span>
              <code className="truncate rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-sm text-teal-200">{link}</code>
            </div>
            <div className="ml-auto flex gap-2">
              <button onClick={copy} className="btn-ghost btn-sm"><Copy className="h-3.5 w-3.5" />Copy link</button>
              <a href={`/${business.slug}`} target="_blank" rel="noreferrer" className="btn-primary btn-sm"><ExternalLink className="h-3.5 w-3.5" />View page</a>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8"><Outlet /></main>
      </div>
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-2xl font-extrabold text-white sm:text-3xl">{title}</h1>{subtitle && <p className="mt-1 text-sm text-slate-300">{subtitle}</p>}</div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
