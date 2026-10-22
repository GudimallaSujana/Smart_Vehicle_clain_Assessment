import { ArrowRight, BrainCircuit, FileText, IndianRupee, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react'
import DisclaimerBanner from '../components/DisclaimerBanner'
import VehicleIllustration from '../components/VehicleIllustration'

export default function LandingPage({ onStart, onDemo }) {
  const cards = [
    { icon: UploadCloud, title: 'Upload evidence', text: 'Accident photos, RC, policy, licence and repair estimates in one assisted workflow.' },
    { icon: BrainCircuit, title: 'AI damage support', text: 'Image quality checks, candidate damage regions, severity scoring and explainable warnings.' },
    { icon: FileText, title: 'OCR + policy review', text: 'Extract policy/vehicle fields, review OCR mistakes, and compare against configurable conditions.' },
    { icon: IndianRupee, title: 'Preliminary estimate', text: 'Use admin-configured pricing or uploaded repair estimate. No invented real-world prices.' }
  ]
  return (
    <main className="vehicle-grid-bg min-h-screen bg-slate-50">
      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-12 lg:grid-cols-[1.05fr_.95fr] lg:px-8 lg:py-20">
        <div className="flex flex-col justify-center">
          <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-brand-100 bg-white px-4 py-2 text-sm font-semibold text-brand-700 shadow-sm">
            <Sparkles size={16} /> Indian-focused InsurTech decision support
          </div>
          <h1 className="max-w-4xl text-5xl font-black tracking-tight text-slate-950 md:text-7xl">
            Understand Your <span className="gradient-text">Vehicle Claim</span> Before You File
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
            Upload your accident photos and policy documents. Our AI-assisted system analyzes vehicle damage,
            extracts relevant information, and prepares a preliminary claim assessment for review.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <button onClick={onStart} className="inline-flex items-center gap-2 rounded-2xl bg-brand-600 px-6 py-4 font-bold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-brand-700">
              Start Claim Assessment <ArrowRight size={20} />
            </button>
            <button onClick={onDemo} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-4 font-bold text-slate-800 shadow-sm transition hover:-translate-y-0.5">
              Try Demo Mode
            </button>
          </div>
          <div className="mt-8">
            <DisclaimerBanner />
          </div>
        </div>
        <div className="relative min-h-[420px]">
          <div className="absolute -right-4 -top-4 h-32 w-32 rounded-full bg-amber-200 blur-3xl" />
          <div className="absolute -bottom-4 -left-4 h-40 w-40 rounded-full bg-teal-200 blur-3xl" />
          <div className="glass-card relative h-full overflow-hidden rounded-[2rem] p-4 shadow-soft">
            <VehicleIllustration />
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-6 pb-20 lg:px-8">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-black text-slate-950">How it works</h2>
            <p className="mt-2 text-slate-600">A bridge from vehicle owner evidence to an explainable preliminary report.</p>
          </div>
          <ShieldCheck className="hidden text-brand-600 md:block" size={40} />
        </div>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {cards.map((card, idx) => {
            const Icon = card.icon
            return (
              <div key={card.title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-soft">
                <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><Icon /></div>
                <div className="mb-2 text-xs font-black uppercase tracking-widest text-amber-500">Step {idx + 1}</div>
                <h3 className="text-xl font-bold text-slate-900">{card.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{card.text}</p>
              </div>
            )
          })}
        </div>
      </section>
    </main>
  )
}
