import { AlertTriangle, CheckCircle2, Clock, ShieldAlert, XCircle } from 'lucide-react'
import { classNames } from '../lib/api'

const styles = {
  VERIFIED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  ELIGIBLE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  NEEDS_VERIFICATION: 'bg-amber-50 text-amber-700 border-amber-200',
  NEEDS_REVIEW: 'bg-amber-50 text-amber-700 border-amber-200',
  HUMAN_REVIEW: 'bg-amber-50 text-amber-700 border-amber-200',
  SUSPICIOUS_EVIDENCE: 'bg-orange-50 text-orange-700 border-orange-200',
  NOT_ELIGIBLE: 'bg-rose-50 text-rose-700 border-rose-200',
  INELIGIBLE: 'bg-rose-50 text-rose-700 border-rose-200',
  REJECTED: 'bg-rose-50 text-rose-700 border-rose-200',
  PRELIMINARY_ESTIMATE: 'bg-blue-50 text-blue-700 border-blue-200',
  DRAFT: 'bg-slate-50 text-slate-700 border-slate-200'
}

export default function StatusBadge({ status, className = '' }) {
  const normalized = String(status || 'DRAFT').toUpperCase().replaceAll(' ', '_')
  const Icon = normalized.includes('VERIFIED') || normalized.includes('ELIGIBLE') || normalized === 'PRELIMINARY_ESTIMATE'
    ? CheckCircle2
    : normalized.includes('SUSPICIOUS')
      ? ShieldAlert
      : normalized.includes('NOT') || normalized.includes('REJECT') || normalized.includes('INELIGIBLE')
        ? XCircle
        : normalized.includes('DRAFT')
          ? Clock
          : AlertTriangle
  return (
    <span className={classNames('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold', styles[normalized] || 'bg-slate-50 text-slate-700 border-slate-200', className)}>
      <Icon size={14} /> {String(status || 'Draft').replaceAll('_', ' ')}
    </span>
  )
}
