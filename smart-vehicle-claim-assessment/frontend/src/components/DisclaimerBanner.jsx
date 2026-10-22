import { Info } from 'lucide-react'

export default function DisclaimerBanner({ compact = false }) {
  return (
    <div className={`rounded-2xl border border-amber-200 bg-amber-50 text-amber-900 ${compact ? 'p-3 text-xs' : 'p-4 text-sm'} flex gap-3`}>
      <Info className="mt-0.5 shrink-0" size={compact ? 16 : 20} />
      <div>
        <strong>AI-assisted preliminary assessment only.</strong>{' '}
        Final claim eligibility, repair assessment, and settlement are subject to insurer verification,
        policy terms, documentation, inspection, and applicable regulations.
      </div>
    </div>
  )
}
