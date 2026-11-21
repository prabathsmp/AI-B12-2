import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, Building2, KeyRound, Mail, Phone, Sparkles } from 'lucide-react'
import { useAuth } from '../auth'
import { Aurora, Field, Logo, Spinner } from '../components/ui'

const CATEGORIES = [
  ['salon', 'Salon / Barber'], ['clinic', 'Clinic'], ['physiotherapy', 'Physiotherapy'],
  ['spa', 'Spa / Wellness'], ['dental', 'Dental'], ['other', 'Other'],
]

const toSlug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 50)

export default function AuthPage({ mode }) {
  const isLogin = mode === 'login'
  const { user, login, register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ business_name: '', slug: '', category: 'salon', phone: '', email: '', password: '' })
  const [slugTouched, setSlugTouched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (user) return <Navigate to="/dashboard" replace />

  const set = (k) => (e) => {
    const v = e.target.value
    setForm((f) => ({ ...f, [k]: v, ...(k === 'business_name' && !slugTouched ? { slug: toSlug(v) } : {}) }))
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      if (isLogin) await login(form.email, form.password)
      else await register(form)
      nav('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const fillDemo = () => setForm((f) => ({ ...f, email: 'demo@slotease.app', password: 'demo1234' }))

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10">
      <Aurora />
      <div className="relative z-10 w-full max-w-md animate-fade-up">
        <div className="mb-8 flex justify-center"><Logo /></div>
        <div className="glass p-7 sm:p-8">
          <h1 className="text-2xl font-bold text-white">{isLogin ? 'Welcome back' : 'Create your booking page'}</h1>
          <p className="mt-1 text-sm text-slate-300">
            {isLogin ? 'Log in to manage your appointments.' : 'Your customers can book you online in minutes.'}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {!isLogin && (
              <>
                <Field label="Business name">
                  <div className="relative"><Building2 className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                    <input className="input pl-9" required minLength={2} value={form.business_name} onChange={set('business_name')} placeholder="Glow Salon" /></div>
                </Field>
                <Field label="Booking link" hint="Letters, numbers and dashes.">
                  <div className="flex items-stretch overflow-hidden rounded-xl border border-white/15 bg-ink-800/80 focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-500/20">
                    <span className="flex items-center border-r border-white/10 bg-white/5 px-3 text-sm text-slate-400">{window.location.host}/</span>
                    <input className="w-full bg-transparent px-3 py-2.5 text-sm text-white outline-none" required pattern="[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]"
                      value={form.slug} onChange={(e) => { setSlugTouched(true); setForm((f) => ({ ...f, slug: toSlug(e.target.value) })) }} placeholder="glow-salon" />
                  </div>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Type">
                    <select className="input" value={form.category} onChange={set('category')}>
                      {CATEGORIES.map(([v, l]) => <option key={v} value={v} className="bg-ink-900">{l}</option>)}
                    </select>
                  </Field>
                  <Field label="WhatsApp phone">
                    <div className="relative"><Phone className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                      <input className="input pl-9" value={form.phone} onChange={set('phone')} placeholder="98765 43210" /></div>
                  </Field>
                </div>
              </>
            )}
            <Field label="E-mail">
              <div className="relative"><Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input className="input pl-9" type="email" required value={form.email} onChange={set('email')} placeholder="you@business.com" autoComplete="email" /></div>
            </Field>
            <Field label="Password" hint={!isLogin ? 'At least 8 characters.' : undefined}>
              <div className="relative"><KeyRound className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input className="input pl-9" type="password" required minLength={isLogin ? 1 : 8} value={form.password} onChange={set('password')} placeholder="••••••••" autoComplete={isLogin ? 'current-password' : 'new-password'} /></div>
            </Field>

            {error && <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">{error}</p>}

            <button className="btn-primary w-full py-3" disabled={busy}>
              {busy ? <Spinner className="h-4 w-4 text-white" /> : <>{isLogin ? 'Log in' : 'Create account'} <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>

          {isLogin && (
            <button onClick={fillDemo} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-brand-400/40 bg-brand-500/10 px-3 py-2.5 text-sm font-medium text-brand-100 hover:bg-brand-500/20">
              <Sparkles className="h-4 w-4" /> Use demo account (Glow Salon)
            </button>
          )}

          <p className="mt-6 text-center text-sm text-slate-300">
            {isLogin ? <>New to SlotEase? <Link to="/register" className="font-semibold text-brand-300 hover:text-brand-200">Create an account</Link></>
              : <>Already have an account? <Link to="/login" className="font-semibold text-brand-300 hover:text-brand-200">Log in</Link></>}
          </p>
        </div>
      </div>
    </div>
  )
}
