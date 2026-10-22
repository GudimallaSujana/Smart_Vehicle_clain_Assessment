import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, ArrowLeft, ArrowRight, Bot, Car, CheckCircle2, ClipboardCheck, FileDown, FileText, Images, IndianRupee, Loader2, Save, ShieldCheck, UploadCloud } from 'lucide-react'
import { api, formatINR } from '../lib/api'
import DisclaimerBanner from '../components/DisclaimerBanner'
import DamageVisualization from '../components/DamageVisualization'
import FileDropzone from '../components/FileDropzone'
import StatusBadge from '../components/StatusBadge'
import StepIndicator from '../components/StepIndicator'

const steps = ['Vehicle Details', 'Accident Details', 'Upload Accident Images', 'Upload Documents', 'AI Damage Analysis', 'Policy Analysis', 'Cost Estimation', 'Final Preliminary Report']

export default function ClaimWizard({ initialClaimId, onBack }) {
  const [step, setStep] = useState(0)
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [vehicle, setVehicle] = useState({ registration_number: 'TS09AB1234', make: '', model: '', year: '', colour: '', vehicle_value: '' })
  const [accident, setAccident] = useState({ accident_date: '', claim_date: '', accident_location: '', accident_description: '' })
  const [policy, setPolicy] = useState({ policy_number: '', policy_type: '', start_date: '', end_date: '', idv: '', deductible: '' })
  const [manualEstimate, setManualEstimate] = useState('')
  const [imageViewType, setImageViewType] = useState('front')
  const [documentType, setDocumentType] = useState('policy')

  useEffect(() => {
    if (initialClaimId) {
      api.getClaim(initialClaimId).then((data) => {
        setClaim(data.claim)
        setStep(7)
      }).catch((err) => setError(err.message))
    }
  }, [initialClaimId])

  const createIfNeeded = async () => {
    if (claim) return claim
    setLoading(true)
    setError('')
    try {
      const payload = {
        user: { name: 'Vehicle Owner' },
        vehicle: {
          ...vehicle,
          year: vehicle.year ? Number(vehicle.year) : null,
          vehicle_value: vehicle.vehicle_value ? Number(vehicle.vehicle_value) : null
        },
        accident,
        policy: Object.values(policy).some(Boolean) ? {
          ...policy,
          idv: policy.idv ? Number(policy.idv) : null,
          deductible: policy.deductible ? Number(policy.deductible) : null,
          coverage: [],
          exclusions: []
        } : null,
        manual_repair_estimate: manualEstimate ? Number(manualEstimate) : null,
        demo_mode: false
      }
      const data = await api.createClaim(payload)
      setClaim(data.claim)
      return data.claim
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }

  const refresh = async (id = claim?.claim_id) => {
    if (!id) return
    const data = await api.getClaim(id)
    setClaim(data.claim)
  }

  const uploadImages = async (files) => {
    const current = await createIfNeeded()
    setLoading(true)
    setError('')
    try {
      for (const file of files) {
        await api.uploadImage(current.claim_id, file, imageViewType)
      }
      await refresh(current.claim_id)
      setStep(3)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  const uploadDocuments = async (files) => {
    const current = await createIfNeeded()
    setLoading(true)
    setError('')
    try {
      for (const file of files) {
        await api.uploadDocument(current.claim_id, file, documentType)
      }
      await refresh(current.claim_id)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  const analyze = async () => {
    const current = await createIfNeeded()
    setLoading(true)
    setError('')
    try {
      const data = await api.analyzeClaim(current.claim_id)
      setClaim(data.claim)
      setStep(7)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  const summary = useMemo(() => ({
    severity: claim?.claim_json?.damage_aggregation?.overall_severity || claim?.damage_assessments?.[0]?.severity || 'Unknown',
    repair: claim?.estimation?.repair_cost,
    settlement: claim?.estimation?.estimated_settlement,
    deductible: claim?.estimation?.deductible,
    eligibility: claim?.eligibility || 'NEEDS_VERIFICATION'
  }), [claim])

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 font-semibold text-slate-700 shadow-sm"><ArrowLeft size={18} /> Back</button>
        {claim?.claim_id && <div className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700">Claim ID: {claim.claim_id}</div>}
      </div>
      <div className="mb-6">
        <StepIndicator steps={steps} current={step} onJump={setStep} />
      </div>
      <DisclaimerBanner />
      {error && <div className="mt-5 flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700"><AlertCircle /> {error}</div>}
      <section className="mt-6 rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
        {step === 0 && <VehicleStep vehicle={vehicle} setVehicle={setVehicle} onNext={() => setStep(1)} loading={loading} />}
        {step === 1 && <AccidentStep accident={accident} setAccident={setAccident} policy={policy} setPolicy={setPolicy} manualEstimate={manualEstimate} setManualEstimate={setManualEstimate} onNext={async () => { await createIfNeeded(); setStep(2) }} loading={loading} />}
        {step === 2 && <ImageUploadStep claim={claim} viewType={imageViewType} setViewType={setImageViewType} onFiles={uploadImages} loading={loading} onNext={() => setStep(3)} />}
        {step === 3 && <DocumentUploadStep claim={claim} documentType={documentType} setDocumentType={setDocumentType} onFiles={uploadDocuments} loading={loading} onAnalyze={analyze} />}
        {step === 4 && <DamageStep claim={claim} loading={loading} onAnalyze={analyze} />}
        {step === 5 && <PolicyStep claim={claim} />}
        {step === 6 && <CostStep claim={claim} />}
        {step === 7 && <ReportStep claim={claim} summary={summary} onAnalyze={analyze} loading={loading} />}
      </section>
      <div className="mt-6 flex justify-between">
        <button disabled={step === 0} onClick={() => setStep(Math.max(step - 1, 0))} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 font-bold text-slate-700 disabled:opacity-40">Previous</button>
        <button disabled={step >= steps.length - 1} onClick={() => setStep(Math.min(step + 1, steps.length - 1))} className="rounded-2xl bg-slate-900 px-5 py-3 font-bold text-white disabled:opacity-40">Next</button>
      </div>
    </main>
  )
}

function VehicleStep({ vehicle, setVehicle, onNext, loading }) {
  return <div className="grid gap-8 lg:grid-cols-[.9fr_1.1fr]">
    <Intro icon={Car} title="Vehicle details" text="Enter Indian vehicle information. OCR from RC can later fill or validate these fields." />
    <div className="grid gap-4 md:grid-cols-2">
      <Input label="Vehicle Registration Number" value={vehicle.registration_number} onChange={v => setVehicle({ ...vehicle, registration_number: v.toUpperCase() })} placeholder="TS09AB1234" />
      <Input label="Make" value={vehicle.make} onChange={v => setVehicle({ ...vehicle, make: v })} placeholder="Hyundai / Maruti / Tata" />
      <Input label="Model" value={vehicle.model} onChange={v => setVehicle({ ...vehicle, model: v })} placeholder="i20 / Swift / Nexon" />
      <Input label="Year" value={vehicle.year} onChange={v => setVehicle({ ...vehicle, year: v })} placeholder="2021" type="number" />
      <Input label="Colour" value={vehicle.colour} onChange={v => setVehicle({ ...vehicle, colour: v })} placeholder="Blue" />
      <Input label="Vehicle Value / IDV if known" value={vehicle.vehicle_value} onChange={v => setVehicle({ ...vehicle, vehicle_value: v })} placeholder="500000" type="number" />
      <div className="md:col-span-2"><PrimaryButton onClick={onNext} loading={loading}>Save & continue</PrimaryButton></div>
    </div>
  </div>
}

function AccidentStep({ accident, setAccident, policy, setPolicy, manualEstimate, setManualEstimate, onNext, loading }) {
  return <div className="space-y-8">
    <div className="grid gap-8 lg:grid-cols-[.9fr_1.1fr]">
      <Intro icon={ClipboardCheck} title="Accident and policy details" text="Provide dates and description. The policy engine uses configurable rules and never guarantees approval." />
      <div className="grid gap-4 md:grid-cols-2">
        <Input label="Accident Date" type="date" value={accident.accident_date} onChange={v => setAccident({ ...accident, accident_date: v })} />
        <Input label="Claim Date" type="date" value={accident.claim_date} onChange={v => setAccident({ ...accident, claim_date: v })} />
        <Input label="Accident Location" value={accident.accident_location} onChange={v => setAccident({ ...accident, accident_location: v })} placeholder="Hyderabad, Telangana" />
        <Input label="Manual Repair Estimate (optional)" value={manualEstimate} onChange={setManualEstimate} type="number" placeholder="Use uploaded estimate if available" />
        <label className="md:col-span-2"><span className="text-sm font-bold text-slate-700">Accident Description</span><textarea value={accident.accident_description} onChange={e => setAccident({ ...accident, accident_description: e.target.value })} className="mt-2 h-28 w-full rounded-2xl border border-slate-200 p-3 outline-none focus:border-brand-400" placeholder="Example: front-left impact near bumper after low-speed collision." /></label>
      </div>
    </div>
    <div className="rounded-3xl bg-slate-50 p-5">
      <h3 className="mb-4 font-bold text-slate-900">Optional policy fields (OCR can also extract these)</h3>
      <div className="grid gap-4 md:grid-cols-3">
        <Input label="Policy Number" value={policy.policy_number} onChange={v => setPolicy({ ...policy, policy_number: v })} />
        <Input label="Policy Type" value={policy.policy_type} onChange={v => setPolicy({ ...policy, policy_type: v })} placeholder="Comprehensive / Own Damage / Third-Party" />
        <Input label="Deductible / Excess" value={policy.deductible} onChange={v => setPolicy({ ...policy, deductible: v })} type="number" />
        <Input label="Policy Start Date" type="date" value={policy.start_date} onChange={v => setPolicy({ ...policy, start_date: v })} />
        <Input label="Policy End Date" type="date" value={policy.end_date} onChange={v => setPolicy({ ...policy, end_date: v })} />
        <Input label="IDV" value={policy.idv} onChange={v => setPolicy({ ...policy, idv: v })} type="number" />
      </div>
    </div>
    <PrimaryButton onClick={onNext} loading={loading}>Create draft claim</PrimaryButton>
  </div>
}

function ImageUploadStep({ claim, viewType, setViewType, onFiles, loading, onNext }) {
  return <div className="space-y-6">
    <Intro icon={Images} title="Upload accident images" text="Use multiple views: front, rear, side, close-up and number plate/context where appropriate. Duplicates are not double-counted." />
    <select value={viewType} onChange={e => setViewType(e.target.value)} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 font-semibold">
      {['front', 'rear', 'left side', 'right side', 'side', 'closeup damage', 'number plate', 'additional evidence'].map(v => <option key={v} value={v}>{v}</option>)}
    </select>
    <FileDropzone disabled={loading} label="Upload accident photos" help="JPG, JPEG, PNG up to configured size. Blurry/dark/corrupted images get friendly validation messages." accept="image/png,image/jpeg" onFiles={onFiles} />
    <EvidenceGrid claim={claim} />
    <PrimaryButton onClick={onNext} loading={loading}>Continue to documents</PrimaryButton>
  </div>
}

function DocumentUploadStep({ claim, documentType, setDocumentType, onFiles, loading, onAnalyze }) {
  return <div className="space-y-6">
    <Intro icon={FileText} title="Upload RC, policy and supporting documents" text="OCR extracts fields into structured JSON. Review/correct uncertain fields before relying on the assessment." />
    <select value={documentType} onChange={e => setDocumentType(e.target.value)} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 font-semibold">
      {['policy', 'rc', 'driving_licence', 'repair_estimate', 'previous_claim', 'accident_document'].map(v => <option key={v} value={v}>{v.replaceAll('_', ' ')}</option>)}
    </select>
    <FileDropzone disabled={loading} label="Upload documents" help="PDF, JPG, JPEG, PNG. Low OCR confidence triggers review instead of silent use." accept="application/pdf,image/png,image/jpeg" onFiles={onFiles} />
    <DocumentCards claim={claim} />
    <PrimaryButton onClick={onAnalyze} loading={loading} icon={Bot}>Run AI assessment</PrimaryButton>
  </div>
}

function DamageStep({ claim, loading, onAnalyze }) {
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3"><Intro icon={Bot} title="AI damage analysis" text="Bounding boxes, inferred parts, damage type, severity and explanations are shown image-by-image." /><PrimaryButton onClick={onAnalyze} loading={loading} icon={Bot}>Run / Re-run Analysis</PrimaryButton></div>
    <DamageVisualization claim={claim} />
    <DamageTable claim={claim} />
  </div>
}

function PolicyStep({ claim }) {
  const policy = claim?.policy_json || {}
  return <div className="space-y-6">
    <Intro icon={ShieldCheck} title="Policy analysis" text="Factor → Evidence → Effect. Rules are configurable and not hard-coded to one insurer." />
    <StatusBadge status={policy.outcome || claim?.eligibility} />
    <div className="overflow-hidden rounded-3xl border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-600"><tr><th className="p-4">Factor</th><th className="p-4">Evidence</th><th className="p-4">Effect</th><th className="p-4">Status</th></tr></thead>
        <tbody>{(policy.factors || []).map((f, i) => <tr key={i} className="border-t border-slate-100"><td className="p-4 font-bold">{f.factor}</td><td className="p-4">{f.evidence}</td><td className="p-4">{f.effect}</td><td className="p-4"><StatusBadge status={f.status} /></td></tr>)}</tbody>
      </table>
    </div>
  </div>
}

function CostStep({ claim }) {
  const estimation = claim?.estimation || {}
  return <div className="space-y-6">
    <Intro icon={IndianRupee} title="Preliminary cost and settlement" text="Cost = part/repair + labour + material from configured pricing or uploaded repair estimate. No real-time prices are invented." />
    <div className="grid gap-5 md:grid-cols-3">
      <SummaryCard label="Repair estimate" value={formatINR(estimation.repair_cost)} />
      <SummaryCard label="Deductible / Excess" value={formatINR(estimation.deductible)} />
      <SummaryCard label="Preliminary settlement" value={formatINR(estimation.estimated_settlement)} highlight />
    </div>
    <div className="rounded-3xl bg-amber-50 p-4 text-sm text-amber-800">{estimation.explanation || 'Run analysis to calculate estimate.'}</div>
    <div className="grid gap-3">{(estimation.cost_breakdown || []).map((item, i) => <div key={i} className="rounded-2xl border border-slate-200 p-4"><div className="font-bold">{item.component} · {item.damage_type} · {item.severity}</div><div className="text-sm text-slate-500">Source: {item.source} {item.demo_only ? '· Demo only' : ''}</div><div className="mt-2 font-black text-slate-900">{formatINR(item.line_total || item.repair_cost)}</div></div>)}</div>
  </div>
}

function ReportStep({ claim, summary, onAnalyze, loading }) {
  if (!claim) return <div className="text-slate-500">Create a claim to see the final report.</div>
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-4">
      <Intro icon={FileDown} title="Final preliminary report" text="Download or share the PDF with an insurer/claim representative for verification." />
      <div className="flex gap-3"><PrimaryButton onClick={onAnalyze} loading={loading} icon={Bot}>Re-run</PrimaryButton><a className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 font-bold text-white" href={api.reportUrl(claim.claim_id)} target="_blank" rel="noreferrer"><FileDown size={18} /> Download PDF</a></div>
    </div>
    {claim.demo_mode ? <div className="rounded-2xl bg-amber-50 p-4 font-bold text-amber-800">Demo Data — Not a Real Insurance Claim</div> : null}
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
      <SummaryCard label="Overall severity" value={summary.severity} />
      <SummaryCard label="Eligibility" value={<StatusBadge status={summary.eligibility} />} />
      <SummaryCard label="Repair estimate" value={formatINR(summary.repair)} />
      <SummaryCard label="Preliminary settlement" value={formatINR(summary.settlement)} highlight />
    </div>
    <VerificationSection claim={claim} />
    <DamageVisualization claim={claim} />
    <DamageTable claim={claim} />
  </div>
}

function EvidenceGrid({ claim }) {
  const images = claim?.images || []
  if (!images.length) return null
  return <div className="grid gap-4 md:grid-cols-3">{images.map(img => <div key={img.image_id} className="rounded-2xl border border-slate-200 bg-white p-3"><img src={api.imageUrl(claim.claim_id, img.image_id)} className="h-36 w-full rounded-xl object-cover" /><div className="mt-2 flex items-center justify-between"><span className="text-sm font-bold">{img.view_type}</span><StatusBadge status={img.validation_status} /></div></div>)}</div>
}

function DocumentCards({ claim }) {
  const docs = claim?.documents || []
  if (!docs.length) return null
  return <div className="grid gap-4 md:grid-cols-2">{docs.map(doc => <div key={doc.document_id} className="rounded-2xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between"><div className="font-bold">{doc.document_type}</div><StatusBadge status={doc.verification_status} /></div><div className="mt-2 text-xs text-slate-500">OCR confidence: {doc.ocr_confidence ?? 'Not available'}</div><pre className="mt-3 max-h-40 overflow-auto rounded-xl bg-slate-50 p-3 text-xs text-slate-600">{JSON.stringify(doc.extracted_fields, null, 2)}</pre></div>)}</div>
}

function VerificationSection({ claim }) {
  const checks = claim?.verification_checks || []
  return <div className="rounded-3xl border border-slate-200 bg-white p-5">
    <h3 className="mb-4 text-xl font-black text-slate-950">Evidence verification dashboard</h3>
    <div className="grid gap-3">{checks.map((check) => <div key={check.check_id || check.check_name} className="rounded-2xl bg-slate-50 p-4"><div className="mb-2 flex flex-wrap items-center justify-between gap-2"><div className="font-bold text-slate-900">{check.check_name}</div><StatusBadge status={check.status} /></div><p className="text-sm text-slate-600">{check.explanation}</p><p className="mt-2 text-xs font-semibold text-slate-500">Action: {check.recommended_action || 'Continue with caution'}</p></div>)}</div>
  </div>
}

function DamageTable({ claim }) {
  const rows = claim?.damage_assessments || []
  if (!rows.length) return <div className="rounded-2xl bg-slate-50 p-5 text-slate-500">No damage findings yet. Run analysis or upload clearer images.</div>
  return <div className="overflow-hidden rounded-3xl border border-slate-200"><table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Damaged part</th><th className="p-4">Damage type</th><th className="p-4">Severity</th><th className="p-4">Confidence</th><th className="p-4">Explanation</th></tr></thead><tbody>{rows.map((r) => <tr key={r.assessment_id || `${r.damaged_part}-${r.damage_type}`} className="border-t border-slate-100"><td className="p-4 font-bold">{r.damaged_part}</td><td className="p-4">{r.damage_type}</td><td className="p-4"><StatusBadge status={r.severity} /></td><td className="p-4">{Math.round((r.confidence || 0) * 100)}%</td><td className="p-4 text-slate-600">{r.explanation}</td></tr>)}</tbody></table></div>
}

function Intro({ icon: Icon, title, text }) {
  return <div><div className="mb-4 flex h-14 w-14 items-center justify-center rounded-3xl bg-brand-50 text-brand-600"><Icon size={28} /></div><h2 className="text-3xl font-black text-slate-950">{title}</h2><p className="mt-3 max-w-xl leading-7 text-slate-600">{text}</p></div>
}

function Input({ label, value, onChange, type = 'text', placeholder = '' }) {
  return <label><span className="text-sm font-bold text-slate-700">{label}</span><input type={type} value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-50" /></label>
}

function PrimaryButton({ children, onClick, loading, icon: Icon = Save }) {
  return <button onClick={onClick} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-600 px-5 py-3 font-bold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60">{loading ? <Loader2 className="animate-spin" size={18} /> : <Icon size={18} />} {children}</button>
}

function SummaryCard({ label, value, highlight = false }) {
  return <div className={`rounded-3xl border p-5 shadow-sm ${highlight ? 'border-brand-200 bg-brand-50' : 'border-slate-200 bg-white'}`}><div className="text-sm font-semibold text-slate-500">{label}</div><div className="mt-2 text-2xl font-black text-slate-950">{value}</div></div>
}
