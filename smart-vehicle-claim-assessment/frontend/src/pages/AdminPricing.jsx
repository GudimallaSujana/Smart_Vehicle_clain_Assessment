import { useEffect, useState } from 'react'
import { Database, Plus } from 'lucide-react'
import { api, formatINR } from '../lib/api'

export default function AdminPricing() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState({ vehicle_make: '', vehicle_model: '', component: '', damage_type: '', severity: 'Minor', repair_cost: '', replacement_cost: '', labor_cost: '', material_cost: '', source: 'admin_configured', valid_for_demo: false })
  const [message, setMessage] = useState('')
  const load = () => api.getPricing().then(d => setRows(d.pricing || [])).catch(err => setMessage(err.message))
  useEffect(() => { load() }, [])
  const submit = async () => {
    await api.addPricing({ ...form, repair_cost: Number(form.repair_cost || 0), replacement_cost: Number(form.replacement_cost || 0), labor_cost: Number(form.labor_cost || 0), material_cost: Number(form.material_cost || 0) })
    setMessage('Pricing item added. Configure real/admin-approved data only.')
    load()
  }
  return <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8"><div className="mb-8 flex items-center gap-4"><div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-brand-50 text-brand-600"><Database /></div><div><h1 className="text-4xl font-black text-slate-950">Pricing Configuration</h1><p className="text-slate-600">Admin-updatable repair pricing. Demo prices are clearly labelled and not real market prices.</p></div></div>{message && <div className="mb-5 rounded-2xl bg-amber-50 p-4 text-amber-800">{message}</div>}<div className="grid gap-6 lg:grid-cols-[.9fr_1.1fr]"><div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="mb-4 text-xl font-black">Add pricing item</h2><div className="grid gap-3 md:grid-cols-2">{Object.keys(form).filter(k => k !== 'valid_for_demo').map(k => <label key={k} className="text-sm font-bold text-slate-700">{k.replaceAll('_', ' ')}<input value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })} className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2" /></label>)}<label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={form.valid_for_demo} onChange={e => setForm({ ...form, valid_for_demo: e.target.checked })} /> Demo only</label></div><button onClick={submit} className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-brand-600 px-5 py-3 font-bold text-white"><Plus size={18} /> Add item</button></div><div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="mb-4 text-xl font-black">Configured prices</h2><div className="max-h-[540px] space-y-3 overflow-auto">{rows.map((r, i) => <div key={i} className="rounded-2xl bg-slate-50 p-4"><div className="font-bold">{r.vehicle_make} {r.vehicle_model} · {r.component} · {r.damage_type} · {r.severity}</div><div className="text-sm text-slate-500">{formatINR((Number(r.repair_cost || 0) + Number(r.replacement_cost || 0) + Number(r.labor_cost || 0) + Number(r.material_cost || 0)))} · {r.source} {r.valid_for_demo ? '· Demo only' : ''}</div></div>)}</div></div></div></main>
}
