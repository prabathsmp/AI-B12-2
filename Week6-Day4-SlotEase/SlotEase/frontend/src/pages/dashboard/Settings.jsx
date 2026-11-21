import { useState } from 'react'
import { Bot, Building2, Eye, EyeOff, KeyRound, Save, ShieldCheck, Trash2 } from 'lucide-react'
import { api, getAiSettings, setAiSettings } from '../../api'
import { useAuth } from '../../auth'
import { Field, Spinner, useToast } from '../../components/ui'
import { PageHeader } from './Layout'

const TIMEZONES = ['Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Colombo', 'Europe/London', 'America/New_York', 'UTC']
const MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1']

export default function Settings() {
  const { business, setBusiness } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState({ name: business.name, phone: business.phone, category: business.category, address: business.address, timezone: business.timezone })
  const [busy, setBusy] = useState(false)
  const [ai, setAi] = useState(getAiSettings())
  const [show, setShow] = useState(false)

  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    try { setBusiness(await api('/business', { method: 'PUT', body: form })); toast('Business profile saved') } catch (err) { toast(err.message, 'error') } finally { setBusy(false) }
  }
  const saveAi = (e) => {
    e.preventDefault()
    if (ai.key && !ai.key.startsWith('sk-')) return toast('OpenAI keys start with "sk-"', 'error')
    setAiSettings(ai); toast(ai.key ? 'AI enabled for this browser' : 'AI settings saved')
  }
  const clearAi = () => { setAiSettings(null); setAi({ key: '', model: 'gpt-4o-mini' }); toast('API key removed', 'info') }

  return (
    <>
      <PageHeader title="Settings" subtitle="Your business profile and optional integrations." />
      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={save} className="glass space-y-4 p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><Building2 className="h-5 w-5 text-brand-300" />Business profile</h2>
          <Field label="Business name"><input className="input" required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="WhatsApp phone" hint="Customers can message you after booking."><input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Category"><input className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
          </div>
          <Field label="Address"><input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Shown on your booking page" /></Field>
          <Field label="Timezone"><select className="input" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
            {TIMEZONES.map((t) => <option key={t} className="bg-ink-900">{t}</option>)}</select></Field>
          <Field label="Booking link"><code className="block rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-teal-200">{window.location.origin}/{business.slug}</code></Field>
          <button className="btn-primary" disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : <><Save className="h-4 w-4" />Save profile</>}</button>
        </form>

        <form onSubmit={saveAi} className="glass relative space-y-4 overflow-hidden p-6">
          <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-fuchsia-500/20 blur-3xl" />
          <h2 className="relative flex items-center gap-2 text-lg font-bold text-white"><Bot className="h-5 w-5 text-fuchsia-300" />AI features (optional)</h2>
          <p className="relative text-sm text-slate-300">SlotEase works fully without AI. Add your own OpenAI key to unlock the <b className="text-white">AI business coach</b> on Stats and <b className="text-white">“Write with AI”</b> for service descriptions.</p>
          <Field label="OpenAI API key">
            <div className="relative"><KeyRound className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input className="input pl-9 pr-10 font-mono" type={show ? 'text' : 'password'} value={ai.key} onChange={(e) => setAi({ ...ai, key: e.target.value.trim() })} placeholder="sk-..." autoComplete="off" />
              <button type="button" onClick={() => setShow(!show)} className="absolute right-2 top-2 rounded-md p-1 text-slate-400 hover:text-white" aria-label="Show key">{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div>
          </Field>
          <Field label="Model"><select className="input" value={ai.model} onChange={(e) => setAi({ ...ai, model: e.target.value })}>
            {MODELS.map((m) => <option key={m} className="bg-ink-900">{m}</option>)}</select></Field>
          <div className="relative flex items-start gap-3 rounded-xl border border-emerald-400/30 bg-emerald-500/10 p-3 text-xs text-emerald-100">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
            The key is stored only in this browser (localStorage) and sent per request over the API proxy. The server never saves or logs it.
          </div>
          <div className="relative flex flex-wrap gap-2">
            <button className="btn-primary"><Save className="h-4 w-4" />Save AI settings</button>
            {getAiSettings().key && <button type="button" onClick={clearAi} className="btn-ghost"><Trash2 className="h-4 w-4" />Remove key</button>}
          </div>
          <p className="relative text-xs text-slate-400">Status: {getAiSettings().key ? <span className="font-semibold text-emerald-300">enabled</span> : <span className="font-semibold text-slate-300">not configured</span>}</p>
        </form>
      </div>
    </>
  )
}
