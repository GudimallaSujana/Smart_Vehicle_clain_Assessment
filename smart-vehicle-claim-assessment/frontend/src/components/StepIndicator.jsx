import { Check } from 'lucide-react'
import { classNames } from '../lib/api'

export default function StepIndicator({ steps, current, onJump }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="hidden gap-2 lg:flex">
        {steps.map((step, index) => {
          const active = index === current
          const done = index < current
          return (
            <button key={step} onClick={() => onJump?.(index)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
              <span className={classNames('flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold', done ? 'bg-emerald-500 text-white' : active ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-500')}>
                {done ? <Check size={17} /> : index + 1}
              </span>
              <span className={classNames('truncate text-sm font-semibold', active ? 'text-brand-700' : done ? 'text-emerald-700' : 'text-slate-500')}>{step}</span>
              {index < steps.length - 1 && <span className="mx-1 h-px flex-1 bg-slate-200" />}
            </button>
          )
        })}
      </div>
      <div className="lg:hidden">
        <div className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-600">
          <span>Step {current + 1} of {steps.length}</span>
          <span className="text-brand-700">{steps[current]}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="progress-line h-full rounded-full" style={{ width: `${((current + 1) / steps.length) * 100}%` }} />
        </div>
      </div>
    </div>
  )
}
