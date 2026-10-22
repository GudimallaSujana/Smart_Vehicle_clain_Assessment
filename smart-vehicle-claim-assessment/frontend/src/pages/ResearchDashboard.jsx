import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Activity, Cpu, GaugeCircle, Microscope } from 'lucide-react'
import { api } from '../lib/api'
import DisclaimerBanner from '../components/DisclaimerBanner'

export default function ResearchDashboard() {
  const [metrics, setMetrics] = useState(null)
  useEffect(() => { api.getMetrics().then(d => setMetrics(d.metrics)).catch(() => {}) }, [])
  const chartData = [
    { metric: 'Precision', value: 0 },
    { metric: 'Recall', value: 0 },
    { metric: 'F1', value: 0 },
    { metric: 'mAP@50', value: 0 }
  ]
  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-brand-50 text-brand-600"><Microscope /></div>
        <div><h1 className="text-4xl font-black text-slate-950">Research / Admin Evaluation</h1><p className="text-slate-600">Actual experiment metrics only. Empty charts mean not evaluated yet.</p></div>
      </div>
      <DisclaimerBanner compact />
      <div className="mt-8 grid gap-5 lg:grid-cols-4">
        <MetricCard icon={GaugeCircle} title="Damage Detection" data={metrics?.damage_detection} />
        <MetricCard icon={Activity} title="Severity" data={metrics?.severity} />
        <MetricCard icon={Cpu} title="Processing" data={metrics?.processing} />
        <MetricCard icon={Microscope} title="Cost Estimation" data={metrics?.cost_estimation} />
      </div>
      <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-black text-slate-950">Detection metrics chart</h2>
        <div className="h-72"><ResponsiveContainer><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="metric" /><YAxis /><Tooltip /><Bar dataKey="value" fill="#2563eb" radius={[8,8,0,0]} /></BarChart></ResponsiveContainer></div>
        <p className="mt-4 text-sm text-slate-500">Not evaluated yet — run training/evaluation scripts with verified labelled data to populate results.</p>
      </div>
      <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-black text-slate-950">Severity confusion matrix</h2>
        <div className="grid max-w-md grid-cols-4 gap-2 text-center text-sm font-semibold text-slate-500">
          {['', 'Minor', 'Moderate', 'Severe', 'Minor', '—', '—', '—', 'Moderate', '—', '—', '—', 'Severe', '—', '—', '—'].map((v, i) => <div key={i} className="rounded-xl bg-slate-50 p-3">{v}</div>)}
        </div>
      </div>
    </main>
  )
}

function MetricCard({ icon: Icon, title, data }) {
  return <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><Icon /></div><h3 className="font-black text-slate-950">{title}</h3><pre className="mt-3 whitespace-pre-wrap rounded-2xl bg-slate-50 p-3 text-xs text-slate-600">{JSON.stringify(data || 'Not evaluated yet', null, 2)}</pre></div>
}
