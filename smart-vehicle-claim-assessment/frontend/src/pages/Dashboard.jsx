import { useEffect, useState } from 'react'
import { CalendarDays, Car, FilePlus2, Gauge, IndianRupee, RefreshCw } from 'lucide-react'
import { api, formatINR } from '../lib/api'
import StatusBadge from '../components/StatusBadge'
import DisclaimerBanner from '../components/DisclaimerBanner'

export default function Dashboard({ onStart, onOpenClaim }) {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listClaims()
      setClaims(data.claims || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])
  const totalEstimate = claims.reduce((sum, c) => sum + Number(c.estimated_amount || 0), 0)
  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black text-slate-950">My Claims</h1>
          <p className="mt-2 text-slate-600">Track draft submissions, AI assessment status, and preliminary estimates.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 font-semibold text-slate-700 shadow-sm"><RefreshCw size={18} /> Refresh</button>
          <button onClick={onStart} className="inline-flex items-center gap-2 rounded-2xl bg-brand-600 px-5 py-3 font-bold text-white shadow-soft"><FilePlus2 size={18} /> New Claim</button>
        </div>
      </div>
      <div className="mb-8 grid gap-5 md:grid-cols-3">
        <Kpi icon={Car} label="Claims" value={claims.length} />
        <Kpi icon={IndianRupee} label="Preliminary settlement total" value={formatINR(totalEstimate)} />
        <Kpi icon={Gauge} label="Needs verification" value={claims.filter(c => String(c.eligibility || '').includes('VERIFICATION') || String(c.claim_status || '').includes('REVIEW')).length} />
      </div>
      <DisclaimerBanner compact />
      {error && <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">{error}</div>}
      {loading ? (
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{[1,2,3].map(i => <div key={i} className="loading-shimmer relative h-56 overflow-hidden rounded-3xl bg-slate-100" />)}</div>
      ) : !claims.length ? (
        <div className="mt-8 rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-brand-50 text-brand-600"><Car /></div>
          <h2 className="text-2xl font-bold text-slate-900">No claims yet</h2>
          <p className="mt-2 text-slate-500">Start with a draft claim or seed a demo claim from the landing page.</p>
          <button onClick={onStart} className="mt-5 rounded-2xl bg-brand-600 px-5 py-3 font-bold text-white">Start Claim Assessment</button>
        </div>
      ) : (
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {claims.map((claim) => (
            <button key={claim.claim_id} onClick={() => onOpenClaim?.(claim.claim_id)} className="group rounded-3xl border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-soft">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs font-black uppercase tracking-widest text-brand-600">{claim.claim_id}</div>
                  <h3 className="mt-1 text-xl font-bold text-slate-950">{claim.vehicle?.registration_number || 'Vehicle'} · {claim.vehicle?.make || ''} {claim.vehicle?.model || ''}</h3>
                </div>
                <StatusBadge status={claim.eligibility || claim.claim_status} />
              </div>
              {claim.demo_mode ? <div className="mb-3 rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">Demo Data — Not a Real Insurance Claim</div> : null}
              <div className="space-y-3 text-sm text-slate-600">
                <div className="flex items-center gap-2"><CalendarDays size={16} /> Accident: {claim.accident_date || 'Not provided'}</div>
                <div className="flex items-center gap-2"><Gauge size={16} /> Severity: {claim.damage_severity || 'Unknown'}</div>
                <div className="flex items-center gap-2"><IndianRupee size={16} /> Estimate: {formatINR(claim.estimated_amount)}</div>
              </div>
              <div className="mt-5 text-sm font-bold text-brand-700 group-hover:translate-x-1 transition">Open assessment →</div>
            </button>
          ))}
        </div>
      )}
    </main>
  )
}

function Kpi({ icon: Icon, label, value }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><Icon /></div>
        <div>
          <div className="text-sm text-slate-500">{label}</div>
          <div className="text-2xl font-black text-slate-950">{value}</div>
        </div>
      </div>
    </div>
  )
}
