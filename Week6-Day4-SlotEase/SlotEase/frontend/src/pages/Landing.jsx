import { Link } from 'react-router-dom'
import {
  ArrowRight, BarChart3, CalendarCheck2, Check, Clock4, Lock, MessageCircle, ShieldCheck, Smartphone, Sparkles, Zap,
} from 'lucide-react'
import { Aurora, Logo, StatusChip } from '../components/ui'
import { useAuth } from '../auth'

const features = [
  { icon: ShieldCheck, title: 'Zero double bookings', text: 'The database itself refuses a second booking for the same slot. Two phones, one winner — always.' },
  { icon: Smartphone, title: '30-second booking', text: 'Customers pick a service, a date and a free slot on a mobile-first page. No calls, no WhatsApp ping-pong.' },
  { icon: CalendarCheck2, title: 'Run the day from one screen', text: "Today's list, a weekly calendar and one-tap Completed / No-show buttons." },
  { icon: BarChart3, title: 'Numbers that matter', text: 'Bookings, no-show rate, busiest day and revenue estimates — every month.' },
  { icon: MessageCircle, title: 'Instant confirmations', text: 'Booking reference on screen, e-mail confirmation and a WhatsApp click-to-chat link.' },
  { icon: Lock, title: 'Private by design', text: 'Every business is its own tenant. Nobody sees anybody else’s customers.' },
]

const steps = ['Open link', 'Load slots', 'Calculate', 'Book', 'Lock + save', 'Notify']

export default function Landing() {
  const { user } = useAuth()
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <Aurora />
      <div className="relative z-10">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
          <Logo />
          <nav className="flex items-center gap-2">
            <a href="#pricing" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:text-white sm:block">Pricing</a>
            <Link to="/glow-salon" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:text-white sm:block">Live demo</Link>
            {user ? (
              <Link to="/dashboard" className="btn-primary">Dashboard <ArrowRight className="h-4 w-4" /></Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost">Log in</Link>
                <Link to="/register" className="btn-primary hidden sm:inline-flex">Start free</Link>
              </>
            )}
          </nav>
        </header>

        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-10 sm:px-6 lg:grid-cols-2 lg:pt-16">
          <div className="animate-fade-up">
            <span className="chip bg-brand-500/15 text-brand-200 ring-brand-400/40"><Sparkles className="h-3.5 w-3.5" /> Built for clinics, salons & physio centres</span>
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.08] text-white sm:text-5xl lg:text-6xl">
              Bookings that <span className="gradient-text">never clash.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-300">
              Give customers a beautiful booking link. Run your whole day from one dashboard. Stop losing money to double bookings and forgotten no-shows.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" className="btn-primary px-6 py-3 text-base">Create your booking page <ArrowRight className="h-4 w-4" /></Link>
              <Link to="/glow-salon" className="btn-ghost px-6 py-3 text-base">Try the demo salon</Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-300">
              {['Set up in 5 minutes', 'Rs 499 / month', 'Cancel anytime'].map((t) => (
                <span key={t} className="inline-flex items-center gap-1.5"><Check className="h-4 w-4 text-glow-400" />{t}</span>
              ))}
            </div>
          </div>

          {/* Mock dashboard preview */}
          <div className="glass relative p-5 animate-fade-up [animation-delay:120ms]">
            <div className="absolute -inset-px -z-10 rounded-2xl bg-gradient-to-br from-brand-500/40 via-transparent to-glow-500/30 blur-xl" />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Glow Salon · Today</p>
                <p className="font-display text-lg font-bold text-white">Sat 10 Oct</p>
              </div>
              <div className="flex gap-2 text-xs">
                <span className="chip bg-brand-500/15 text-brand-200 ring-brand-400/40">12 bookings</span>
                <span className="chip bg-rose-500/15 text-rose-200 ring-rose-400/40">2 no-shows</span>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {[
                ['10:00', 'Priya R', 'Haircut', 'completed'],
                ['10:45', 'Arun K', 'Beard Trim', 'no_show'],
                ['17:30', 'Karthik S', 'Haircut + Beard', 'booked'],
              ].map(([t, n, s, st]) => (
                <div key={t} className="glass-soft flex items-center gap-3 px-3 py-2.5">
                  <span className="w-12 font-mono text-sm font-semibold text-white">{t}</span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-white">{n}</p><p className="truncate text-xs text-slate-400">{s}</p></div>
                  <StatusChip status={st} />
                </div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[['214', 'bookings'], ['6%', 'no-show'], ['₹6,450', 'today est.']].map(([v, l]) => (
                <div key={l} className="glass-soft py-3"><p className="font-display text-lg font-bold text-white">{v}</p><p className="text-[11px] uppercase tracking-wider text-slate-400">{l}</p></div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
          <div className="glass flex flex-wrap items-center justify-center gap-2 p-4 sm:justify-between">
            {steps.map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-glow-500 text-xs font-bold text-white">{i + 1}</span>
                <span className="text-sm font-semibold text-slate-100">{s}</span>
                {i < steps.length - 1 && <ArrowRight className="hidden h-4 w-4 text-slate-500 md:block" />}
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
          <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">Everything a small business needs. <span className="gradient-text">Nothing it doesn’t.</span></h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: I, title, text }) => (
              <div key={title} className="glass group p-6 transition hover:-translate-y-1 hover:border-brand-400/40">
                <div className="inline-flex rounded-xl bg-gradient-to-br from-brand-500/30 to-glow-500/20 p-3 ring-1 ring-white/10"><I className="h-5 w-5 text-brand-200" /></div>
                <h3 className="mt-4 text-lg font-bold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
          <div className="glass relative mx-auto max-w-xl overflow-hidden p-8 text-center">
            <div className="absolute inset-x-0 -top-24 mx-auto h-48 w-48 rounded-full bg-brand-500/40 blur-3xl" />
            <p className="relative text-sm font-semibold uppercase tracking-widest text-brand-200">Starter plan</p>
            <p className="relative mt-3 font-display text-6xl font-extrabold text-white">₹499<span className="text-xl font-semibold text-slate-400"> / month</span></p>
            <ul className="relative mx-auto mt-6 max-w-xs space-y-2 text-left text-sm text-slate-200">
              {['Unlimited bookings', 'Public booking page', 'Owner dashboard & stats', 'E-mail + WhatsApp confirmations', 'Optional AI business insights'].map((t) => (
                <li key={t} className="flex items-center gap-2"><Zap className="h-4 w-4 text-glow-400" />{t}</li>
              ))}
            </ul>
            <Link to="/register" className="btn-primary relative mt-8 w-full py-3 text-base">Start your 14-day trial</Link>
          </div>
        </section>

        <footer className="border-t border-white/10 py-8 text-center text-sm text-slate-400">
          <div className="flex items-center justify-center gap-2"><Clock4 className="h-4 w-4" /> SlotEase — appointment booking for small businesses</div>
        </footer>
      </div>
    </div>
  )
}
