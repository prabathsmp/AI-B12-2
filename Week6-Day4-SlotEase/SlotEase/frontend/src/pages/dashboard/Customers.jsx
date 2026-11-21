import { useEffect, useMemo, useState } from 'react'
import { MessageCircle, Phone, Search, Users } from 'lucide-react'
import { api } from '../../api'
import { Empty, PageLoader, useToast } from '../../components/ui'
import { cx, initials, prettyDate } from '../../utils'
import { PageHeader } from './Layout'

export default function Customers() {
  const toast = useToast()
  const [rows, setRows] = useState(null)
  const [q, setQ] = useState('')
  useEffect(() => { api('/customers').then(setRows).catch((e) => toast(e.message, 'error')) }, [toast])

  const list = useMemo(() => (rows || []).filter((c) => `${c.name} ${c.phone}`.toLowerCase().includes(q.toLowerCase())), [rows, q])
  if (!rows) return <PageLoader />

  return (
    <>
      <PageHeader title="Customers" subtitle={`${rows.length} people have booked with you`}
        actions={<div className="relative w-64"><Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
          <input className="input pl-9" placeholder="Search name or phone" value={q} onChange={(e) => setQ(e.target.value)} /></div>} />
      {list.length === 0 ? <div className="glass p-6"><Empty icon={Users} title="No customers found">Customers appear here automatically after their first booking.</Empty></div> : (
        <div className="glass overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead><tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-slate-400">
              <th className="px-5 py-3 font-semibold">Customer</th><th className="px-5 py-3 font-semibold">Visits</th>
              <th className="px-5 py-3 font-semibold">No-shows</th><th className="px-5 py-3 font-semibold">Last visit</th><th className="px-5 py-3" /></tr></thead>
            <tbody className="divide-y divide-white/[0.07]">
              {list.map((c) => {
                const digits = c.phone.replace(/\D/g, '')
                return (
                  <tr key={c.id} className="hover:bg-white/[0.03]">
                    <td className="px-5 py-3"><div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500/40 to-glow-500/30 text-xs font-bold text-white ring-1 ring-white/15">{initials(c.name)}</div>
                      <div><p className="font-semibold text-white">{c.name}</p><p className="text-xs text-slate-400">{c.phone}</p></div></div></td>
                    <td className="px-5 py-3"><span className="font-semibold text-white">{c.visits}</span>{c.visits > 1 && <span className="ml-2 chip bg-brand-500/15 text-brand-200 ring-brand-400/30">repeat</span>}</td>
                    <td className="px-5 py-3"><span className={cx('font-semibold', c.no_shows ? 'text-rose-300' : 'text-slate-400')}>{c.no_shows}</span></td>
                    <td className="px-5 py-3 text-slate-200">{c.last_visit ? prettyDate(c.last_visit.slice(0, 10)) : '—'}</td>
                    <td className="px-5 py-3"><div className="flex justify-end gap-1">
                      <a href={`tel:${c.phone}`} className="btn-ghost btn-sm" aria-label="Call"><Phone className="h-3.5 w-3.5" /></a>
                      <a href={`https://wa.me/${digits.length === 10 ? '91' + digits : digits}`} target="_blank" rel="noreferrer" className="btn btn-sm border border-[#25D366]/40 bg-[#25D366]/10 text-[#7ef0a8]" aria-label="WhatsApp"><MessageCircle className="h-3.5 w-3.5" /></a>
                    </div></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
