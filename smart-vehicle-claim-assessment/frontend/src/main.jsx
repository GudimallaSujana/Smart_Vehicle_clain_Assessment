import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity,
  ArrowRight,
  BadgeIndianRupee,
  Camera,
  Car,
  CarFront,
  Check,
  ChevronRight,
  ClipboardList,
  FileText,
  Grid2X2,
  IndianRupee,
  Loader2,
  LogOut,
  MapPin,
  Plus,
  Shield,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Zap
} from 'lucide-react'
import './index.css'
import crashHeroUrl from './assets/crash_hero.png'
import accidentPreviewUrl from './assets/accident_preview.png'
import { api, formatINR } from './lib/api'

const defaultIncident = {
  vehicle: '2021 Hyundai Creta SX',
  registration: 'TS09AB1234',
  make: 'Hyundai',
  model: 'Creta SX',
  year: 2021,
  colour: 'White',
  location: 'Bandra West, Mumbai',
  description: 'Front impact at a signal; bumper and headlamp visibly damaged.',
  accident_date: '2026-09-30'
}

const emptyEstimate = {
  repair: null,
  payable: null,
  deductible: null,
  rows: [],
  ready: false,
  status: 'AWAITING_EVIDENCE'
}

const CURRENT_DATE = '2026-10-02'

function parseISODate(value) {
  if (!value) return null
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

function getPolicyValidity(policy = {}, accidentDateValue) {
  const start = parseISODate(policy.start_date)
  const end = parseISODate(policy.end_date)
  const today = parseISODate(CURRENT_DATE)
  const accident = parseISODate(accidentDateValue || defaultIncident.accident_date || CURRENT_DATE)
  if (!start || !end) {
    return {
      status: 'NEEDS_VERIFICATION',
      label: 'Policy dates need verification',
      detail: 'Upload a clear policy document or correct OCR-extracted start/end dates before relying on the estimate.'
    }
  }
  if (start && accident && start > accident) {
    return {
      status: 'NOT_ACTIVE_ON_ACCIDENT_DATE',
      label: 'Policy not active on accident date',
      detail: `Policy starts ${policy.start_date}, after the reported accident date.`
    }
  }
  if (end && accident && end < accident) {
    return {
      status: 'EXPIRED_ON_ACCIDENT_DATE',
      label: 'Policy expired before accident',
      detail: `Policy ended ${policy.end_date}, before the reported accident date.`
    }
  }
  if (end && today && end < today) {
    return {
      status: 'EXPIRED_NOW',
      label: 'Policy paperwork is expired now',
      detail: `Policy ended ${policy.end_date}. Ask the insurer to verify whether the accident-period cover is still acceptable for claim processing.`
    }
  }
  return {
    status: 'ACTIVE',
    label: 'Policy active / not expired',
    detail: `Policy is valid until ${policy.end_date}.`
  }
}

function isPolicyBlocking(policyStatus) {
  return ['EXPIRED_ON_ACCIDENT_DATE', 'NOT_ACTIVE_ON_ACCIDENT_DATE'].includes(policyStatus?.status)
}

function App() {
  const savedName = typeof window !== 'undefined' ? window.localStorage.getItem('svc_user_name') : ''
  const [authScreen, setAuthScreen] = useState(savedName ? 'app' : 'login')
  const [userName, setUserName] = useState(savedName || '')
  const [page, setPage] = useState('overview')
  const [selectedRecent, setSelectedRecent] = useState(null)
  const [step, setStep] = useState(0)
  const [incident, setIncident] = useState(defaultIncident)
  const [claim, setClaim] = useState(null)
  const [estimate, setEstimate] = useState(emptyEstimate)
  const [health, setHealth] = useState(null)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [uploadedViews, setUploadedViews] = useState([])
  const [policyFileName, setPolicyFileName] = useState('')
  const displayName = userName?.trim() || 'User'
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'U'
  const recentAssessments = useMemo(() => [
    {
      id: 'RPT-20260618-001',
      color: 'green',
      name: 'Rohan Mehta',
      vehicle: 'Maruti Suzuki Brezza',
      car: 'Maruti Suzuki Brezza · 18 Jun 2026',
      date: '18 Jun 2026',
      status: 'Review complete',
      amount: '₹34,800',
      payable: '₹30,200',
      deductible: '₹4,600',
      severity: 'Moderate',
      location: 'Pune, Maharashtra',
      summary: 'Rear bumper scrape and tail-lamp check completed with preliminary repair estimate.'
    },
    {
      id: 'RPT-20260618-002',
      color: 'amber',
      name: 'Priya Shah',
      vehicle: 'Tata Nexon EV',
      car: 'Tata Nexon EV · 18 Jun 2026',
      date: '18 Jun 2026',
      status: 'Awaiting documents',
      amount: '—',
      payable: 'Pending',
      deductible: 'Pending policy proof',
      severity: 'Needs verification',
      location: 'Ahmedabad, Gujarat',
      summary: 'Assessment is paused until policy proof and clearer side-view images are uploaded.'
    },
    {
      id: claim?.claim_id || 'RPT-20260618-003',
      color: 'blue',
      name: displayName,
      vehicle: 'Hyundai Creta SX',
      car: 'Hyundai Creta SX · 18 Jun 2026',
      date: '18 Jun 2026',
      status: 'Assessment ready',
      amount: estimate.ready ? formatINR(estimate.repair) : '—',
      payable: estimate.ready ? formatINR(estimate.payable) : 'Pending',
      deductible: estimate.deductible ? formatINR(estimate.deductible) : 'Pending',
      severity: 'Moderate',
      location: defaultIncident.location,
      summary: defaultIncident.description
    }
  ], [displayName, estimate.repair, estimate.payable, estimate.deductible, claim?.claim_id])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: 'offline' }))
  }, [])

  const showToast = (message) => {
    setToast(message)
    window.clearTimeout(showToast._timer)
    showToast._timer = window.setTimeout(() => setToast(''), 3600)
  }

  const handleLogin = (name) => {
    const cleanName = (name || 'User').trim() || 'User'
    setUserName(cleanName)
    window.localStorage.setItem('svc_user_name', cleanName)
    setAuthScreen('app')
    setPage('overview')
    showToast(`Welcome, ${cleanName}`)
  }

  const handleLogout = () => {
    window.localStorage.removeItem('svc_user_name')
    setUserName('')
    setClaim(null)
    setUploadedViews([])
    setPolicyFileName('')
    setStep(0)
    setPage('overview')
    setAuthScreen('logout')
  }

  const startAssessment = () => {
    setClaim(null)
    setUploadedViews([])
    setPolicyFileName('')
    setEstimate(emptyEstimate)
    setPage('assessment')
    setStep(0)
  }

  const openDetailedReport = () => {
    setPage('report')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const openRecentAssessment = (assessment) => {
    setSelectedRecent(assessment)
    setPage('recent-detail')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const openRecentList = () => {
    setPage('recent')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const ensureClaim = async () => {
    if (claim) return claim
    const payload = {
      user: { name: displayName },
      vehicle: {
        registration_number: incident.registration,
        make: incident.make,
        model: incident.model,
        year: incident.year,
        colour: incident.colour,
        vehicle_value: 850000
      },
      accident: {
        accident_date: '2026-09-30',
        claim_date: '2026-10-02',
        accident_location: incident.location,
        accident_description: incident.description
      },
      policy: {
        policy_number: 'DEMO-POLICY-2026',
        policy_type: 'Comprehensive / Package Policy',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        idv: 850000,
        deductible: 6500,
        coverage: ['Own Damage', 'Accidental external damage'],
        exclusions: ['Wear and tear', 'Mechanical breakdown not arising from accident']
      },
      demo_mode: true,
      manual_repair_estimate: null
    }
    const created = await api.createClaim(payload)
    setClaim(created.claim)
    return created.claim
  }

  const continueToPhotos = async () => {
    setBusy(true)
    try {
      await ensureClaim()
      setStep(1)
      showToast('Draft autosaved')
    } catch (err) {
      showToast(err.message)
    } finally {
      setBusy(false)
    }
  }

  const uploadViews = async (files) => {
    if (!files?.length) return
    setBusy(true)
    try {
      const current = await ensureClaim()
      const views = ['front', 'rear', 'left side', 'closeup damage']
      for (let index = 0; index < files.length; index++) {
        await api.uploadImage(current.claim_id, files[index], views[index % views.length])
      }
      const fresh = await api.getClaim(current.claim_id)
      setClaim(fresh.claim)
      setUploadedViews(Array.from(files).map((file, index) => ({ name: file.name, view: views[index % views.length] })))
      showToast(`${files.length} photo${files.length > 1 ? 's' : ''} uploaded`)
    } catch (err) {
      showToast(err.message)
    } finally {
      setBusy(false)
    }
  }

  const uploadPolicy = async (files) => {
    if (!files?.length) return
    setBusy(true)
    try {
      const current = await ensureClaim()
      await api.uploadDocument(current.claim_id, files[0], 'policy')
      const fresh = await api.getClaim(current.claim_id)
      setClaim(fresh.claim)
      setPolicyFileName(files[0].name)
      showToast('Policy proof uploaded. OCR review is ready.')
    } catch (err) {
      showToast(err.message)
    } finally {
      setBusy(false)
    }
  }

  const runEstimate = async () => {
    setBusy(true)
    try {
      const imageCount = (claim?.images?.length || 0) + uploadedViews.length
      const documentCount = (claim?.documents?.length || 0) + (policyFileName ? 1 : 0)
      if (imageCount === 0 || documentCount === 0) {
        setEstimate({ ...emptyEstimate, status: 'AWAITING_EVIDENCE' })
        setStep(imageCount === 0 ? 1 : 2)
        showToast('Upload accident photos and policy proof before running the estimate.')
        return
      }

      const current = await ensureClaim()
      const analyzed = await api.analyzeClaim(current.claim_id)
      const analyzedClaim = analyzed.claim
      setClaim(analyzedClaim)
      const policyStatus = getPolicyValidity(analyzedClaim?.policy || {}, analyzedClaim?.accident_date)
      if (isPolicyBlocking(policyStatus) || analyzedClaim?.policy_json?.outcome === 'NOT_ELIGIBLE') {
        setEstimate({
          ...emptyEstimate,
          deductible: analyzedClaim?.estimation?.deductible ?? null,
          status: policyStatus.status || 'POLICY_NOT_ELIGIBLE',
          policyStatus
        })
        setStep(3)
        showToast(`${policyStatus.label}. Estimate paused until policy is verified.`)
        return
      }
      if (analyzedClaim?.estimation?.repair_cost) {
        const rows = (analyzedClaim.estimation.cost_breakdown || []).map((row, index) => ({
          part: row.component || `Component ${index + 1}`,
          action: row.replacement_cost > 0 ? 'Replace' : 'Repair',
          confidence: Math.max(35, Math.round((analyzedClaim.damage_assessments?.[index]?.confidence || 0.55) * 100)),
          amount: row.line_total || row.repair_cost || 0
        }))
        setEstimate({
          repair: analyzedClaim.estimation.repair_cost,
          payable: analyzedClaim.estimation.estimated_settlement ?? null,
          deductible: analyzedClaim.estimation.deductible ?? null,
          rows,
          ready: true,
          status: analyzedClaim.estimation.status || 'PRELIMINARY_ESTIMATE',
          policyStatus
        })
        setStep(3)
        showToast('Estimate ready — preliminary assessment only')
      } else {
        setEstimate({
          ...emptyEstimate,
          deductible: analyzedClaim?.estimation?.deductible ?? null,
          status: analyzedClaim?.estimation?.status || 'NEEDS_PRICING_OR_MANUAL_ESTIMATE',
          policyStatus
        })
        setStep(3)
        showToast('Estimate needs pricing/manual repair estimate. No amount was generated.')
      }
    } catch (err) {
      setEstimate({ ...emptyEstimate, status: 'ANALYSIS_FAILED' })
      showToast(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (authScreen === 'login') {
    return <LoginPage onLogin={handleLogin} />
  }

  if (authScreen === 'logout') {
    return <LogoutPage onLogin={() => setAuthScreen('login')} />
  }

  return (
    <div className="vc-app">
      <Sidebar page={page} setPage={setPage} startAssessment={startAssessment} onLogout={handleLogout} userName={displayName} initials={initials} />
      <section className="vc-shell">
        <Topbar page={page} health={health} onLogout={handleLogout} userName={displayName} initials={initials} />
        {toast ? <div className="vc-toast">{toast}</div> : null}
        {page === 'overview' && <Overview onStart={startAssessment} onPolicy={() => setPage('policy')} estimate={estimate} userName={displayName} recentAssessments={recentAssessments} onOpenRecent={openRecentAssessment} onViewAllRecent={openRecentList} />}
        {page === 'assessment' && (
          <Assessment
            step={step}
            setStep={setStep}
            incident={incident}
            setIncident={setIncident}
            continueToPhotos={continueToPhotos}
            uploadViews={uploadViews}
            uploadPolicy={uploadPolicy}
            runEstimate={runEstimate}
            busy={busy}
            uploadedViews={uploadedViews}
            policyFileName={policyFileName}
            claim={claim}
            estimate={estimate}
            startAgain={startAssessment}
            onViewReport={openDetailedReport}
          />
        )}
        {page === 'policy' && <PolicyFinder />}
        {page === 'recent' && <RecentAssessmentsPage assessments={recentAssessments} onOpenRecent={openRecentAssessment} onBack={() => setPage('overview')} />}
        {page === 'recent-detail' && <RecentAssessmentDetail assessment={selectedRecent || recentAssessments[0]} estimate={estimate} onBack={openRecentList} onOpenReport={openDetailedReport} onVerifyPolicy={() => setPage('policy')} onManualReview={openDetailedReport} />}
        {page === 'report' && <DetailedReport claim={claim} estimate={estimate} incident={incident} onBack={() => setPage('assessment')} onStart={startAssessment} />}
      </section>
    </div>
  )
}


function LoginPage({ onLogin }) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const submit = (event) => {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) {
      setError('Please enter your name to continue.')
      return
    }
    onLogin(clean)
  }

  return (
    <main className="vc-auth-page">
      <section className="vc-auth-card">
        <div className="vc-logo auth-logo">
          <span className="vc-logo-mark"><CarFront size={21} /></span>
          <span>vaahan<span>claim</span></span>
        </div>
        <div className="vc-eyebrow auth-eyebrow"><span /> Secure workspace</div>
        <h1>Sign in to continue.</h1>
        <p>Enter your name to open your vehicle claim workspace.</p>
        <form onSubmit={submit} className="vc-login-form">
          <label>Your name
            <input value={name} onChange={(event) => { setName(event.target.value); setError('') }} placeholder="Example: Arjun Kapoor" autoFocus />
          </label>
          {error ? <div className="vc-auth-error">{error}</div> : null}
          <button className="vc-primary full" type="submit">Login <ArrowRight size={17} /></button>
        </form>
        <div className="vc-auth-note"><ShieldCheck size={17} /> AI-assisted preliminary assessment only. Final approval is subject to insurer verification.</div>
      </section>
      <section className="vc-auth-preview">
        <CrashVisual large />
        <div className="vc-auth-preview-copy">
          <strong>Know your claim before you file.</strong>
          <span>Damage photos · policy proof · preliminary estimate</span>
        </div>
      </section>
    </main>
  )
}

function LogoutPage({ onLogin }) {
  return (
    <main className="vc-auth-page">
      <section className="vc-auth-card logout-card">
        <div className="vc-logo auth-logo">
          <span className="vc-logo-mark"><CarFront size={21} /></span>
          <span>vaahan<span>claim</span></span>
        </div>
        <div className="vc-icon-tile green"><Check size={24} /></div>
        <h1>You’re logged out.</h1>
        <p>Your local session has been cleared from this browser preview.</p>
        <button className="vc-primary full" onClick={onLogin}>Login again <ArrowRight size={17} /></button>
      </section>
    </main>
  )
}

function Sidebar({ page, setPage, startAssessment, onLogout, userName, initials }) {
  const item = (id, label, Icon, onClick) => (
    <button className={`vc-nav-item ${page === id ? 'active' : ''}`} onClick={onClick || (() => setPage(id))}>
      <Icon size={18} />
      <span>{label}</span>
      {id === 'assessment' ? <Plus size={16} className="vc-nav-plus" /> : null}
    </button>
  )

  return (
    <aside className="vc-sidebar">
      <div className="vc-logo">
        <span className="vc-logo-mark"><CarFront size={21} /></span>
        <span>vaahan<span>claim</span></span>
      </div>
      <div className="vc-side-kicker"><span>Workspace</span><span>01</span></div>
      <nav className="vc-nav">
        {item('overview', 'Overview', Grid2X2)}
        {item('assessment', 'New assessment', Plus, startAssessment)}
        {item('policy', 'Policy finder', Shield)}
      </nav>
      <div className="vc-user-card">
        <span className="vc-avatar">{initials}</span>
        <div><strong>{userName}</strong><small>Signed in</small></div>
      </div>
      <button className="vc-logout-btn" onClick={onLogout}><LogOut size={16} /> Logout</button>
      <div className="vc-live-desk">
        <div className="vc-live-row">
          <Activity size={17} />
          <strong>Live claim desk</strong>
          <span className="vc-dot" />
        </div>
        <p>Typically replies in 2 min</p>
      </div>
    </aside>
  )
}

function Topbar({ page, health, onLogout, initials }) {
  const title = page === 'overview' ? 'Overview' : page === 'policy' ? 'Policy finder' : page === 'report' ? 'Detailed report' : page === 'recent' ? 'Recent assessments' : page === 'recent-detail' ? 'Assessment details' : 'New assessment'
  return (
    <header className="vc-topbar">
      <div className="vc-crumb">Workspace <ChevronRight size={13} /> <strong>{title}</strong></div>
      <div className="vc-secure">
        <span className={`vc-pulse ${health?.status === 'ok' ? 'ok' : ''}`} />
        Secure workspace
        <span className="vc-avatar">{initials}</span>
        <button className="vc-top-logout" onClick={onLogout}><LogOut size={14} /> Logout</button>
      </div>
    </header>
  )
}

function Overview({ onStart, onPolicy, estimate, userName, recentAssessments, onOpenRecent, onViewAllRecent }) {
  return (
    <main className="vc-main vc-overview">
      <div className="vc-page-head overview-head">
        <div>
          <div className="vc-eyebrow"><span /> Claim intelligence / 2026</div>
          <h1>hello {userName}</h1>
          <p>Turn a difficult moment into a clear next step.</p>
        </div>
        <button className="vc-primary" onClick={onStart}><Plus size={17} /> Start assessment <ArrowRight size={17} /></button>
      </div>

      <section className="vc-hero-card">
        <div className="vc-hero-copy">
          <div className="vc-eyebrow blue"><span /> Live estimate engine</div>
          <h2>Know your claim <br /><em>before you file.</em></h2>
          <p>Upload damage photos, add your policy and get a transparent repair estimate in under 3 minutes.</p>
          <button className="vc-text-action" onClick={onStart}>Assess vehicle <ArrowRight size={17} /></button>
        </div>
        <div className="vc-hero-visual">
          <CrashVisual large />
          <div className="vc-ai-ready"><Zap size={15} /> <strong>AI vision ready</strong><span>4 angles · 96% clarity</span></div>
        </div>
      </section>

      <section className="vc-pulse-section">
        <div className="vc-section-row">
          <div><h3>Your pulse</h3><p>A quick read on your claim activity</p></div>
          <button className="vc-ghost">View insights <ArrowRight size={15} /></button>
        </div>
        <div className="vc-stat-grid">
          <Stat label="Total assessments" value="13" sub="+3 this month" icon={ClipboardList} tone="blue" />
          <Stat label="Repair cost tracked" value={estimate.ready ? formatINR(estimate.repair) : '—'} sub="Across 12 vehicles" icon={IndianRupee} tone="amber" />
          <Stat label="Insurer payable" value={estimate.ready ? formatINR(estimate.payable) : '—'} sub="81.4% of estimates" icon={ShieldCheck} tone="green" />
          <Stat label="Active reviews" value="1" sub="Need your attention" icon={Zap} tone="rose" />
        </div>
      </section>

      <section className="vc-recent-section">
        <div className="vc-section-row">
          <div><h3>Recent assessments</h3><p>Your latest vehicle reports, all in one place</p></div>
          <button className="vc-ghost" onClick={onViewAllRecent}>View all <ArrowRight size={15} /></button>
        </div>
        {recentAssessments.map((assessment) => (
          <RecentRow key={assessment.id} {...assessment} onClick={() => onOpenRecent(assessment)} />
        ))}
      </section>

      <button className="vc-wide-cta" onClick={onPolicy}>
        <Sparkles size={20} />
        <span><strong>Make your next policy work harder</strong><small>Compare coverage that actually matches your driving life.</small></span>
        <b>Find better cover</b><ArrowRight size={17} />
      </button>
    </main>
  )
}

function Assessment({ step, setStep, incident, setIncident, continueToPhotos, uploadViews, uploadPolicy, runEstimate, busy, uploadedViews, policyFileName, claim, estimate, startAgain, onViewReport }) {
  return (
    <main className="vc-main vc-assessment">
      <div className="vc-page-head compact">
        <div>
          <div className="vc-eyebrow"><span /> New assessment</div>
          <h1>Let’s make sense of it.</h1>
          <p>We’ll guide you from incident to estimate, one clear step at a time.</p>
        </div>
        <div className="vc-autosave">Draft autosaved · just now</div>
      </div>
      <Stepper step={step} setStep={setStep} />
      <div className="vc-assessment-grid">
        <section className="vc-panel">
          {step === 0 && (
            <IncidentStep incident={incident} setIncident={setIncident} onNext={continueToPhotos} busy={busy} />
          )}
          {step === 1 && (
            <VehicleViewsStep onUpload={uploadViews} uploadedViews={uploadedViews} busy={busy} onNext={() => setStep(2)} onBack={() => setStep(0)} />
          )}
          {step === 2 && (
            <PolicyProofStep onUpload={uploadPolicy} fileName={policyFileName} busy={busy} onRun={runEstimate} onBack={() => setStep(1)} />
          )}
          {step === 3 && (
            <EstimateStep estimate={estimate} claim={claim} onStartAgain={startAgain} onViewReport={onViewReport} uploadedViews={uploadedViews} policyFileName={policyFileName} onNeedPhotos={() => setStep(1)} onNeedPolicy={() => setStep(2)} />
          )}
        </section>
        <AssessmentPreview incident={incident} complete={step === 3} />
      </div>
    </main>
  )
}

function Stepper({ step, setStep }) {
  const steps = ['Incident', 'Vehicle views', 'Policy proof', 'Estimate']
  return (
    <div className="vc-stepper">
      {steps.map((label, index) => (
        <React.Fragment key={label}>
          <button className={`vc-step ${index < step ? 'done' : ''} ${index === step ? 'active' : ''}`} onClick={() => setStep(index)}>
            <span>{index < step ? <Check size={14} /> : index + 1}</span>{label}
          </button>
          {index < steps.length - 1 ? <i /> : null}
        </React.Fragment>
      ))}
    </div>
  )
}

function IncidentStep({ incident, setIncident, onNext, busy }) {
  return (
    <div className="vc-form-step">
      <IconTile icon={MapPin} tone="blue" />
      <h2>Tell us what happened</h2>
      <p>A few details help us calibrate the estimate to your situation.</p>
      <label>Vehicle <small>Required</small>
        <select value={incident.vehicle} onChange={(e) => setIncident({ ...incident, vehicle: e.target.value })}>
          <option>2021 Hyundai Creta SX</option>
          <option>2022 Tata Nexon EV</option>
          <option>2020 Maruti Suzuki Brezza</option>
        </select>
      </label>
      <label>Accident location <small>Required</small>
        <div className="vc-input-with-icon"><MapPin size={16} /><input value={incident.location} onChange={(e) => setIncident({ ...incident, location: e.target.value })} /></div>
      </label>
      <label>What happened? <small>Optional</small>
        <textarea value={incident.description} onChange={(e) => setIncident({ ...incident, description: e.target.value })} />
      </label>
      <button className="vc-primary full" onClick={onNext} disabled={busy}>{busy ? <Loader2 className="spin" size={17} /> : null} Continue to photos <ArrowRight size={17} /></button>
    </div>
  )
}

function VehicleViewsStep({ onUpload, uploadedViews, busy, onNext, onBack }) {
  const inputRef = useRef(null)
  const cards = ['Front', 'Rear', 'Left side', 'Close-up']
  return (
    <div className="vc-form-step">
      <IconTile icon={UploadCloud} tone="amber" />
      <h2>Show us the damage</h2>
      <p>Add clear photos from different angles. More views mean a sharper estimate.</p>
      <button className="vc-dropzone" onClick={() => inputRef.current?.click()} disabled={busy}>
        <UploadCloud size={28} />
        <strong>{busy ? 'Uploading photos…' : 'Drop photos here or browse'}</strong>
        <span>JPG, PNG · up to 10 photos · 10MB each</span>
      </button>
      <input ref={inputRef} type="file" multiple accept="image/png,image/jpeg" hidden onChange={(e) => onUpload(Array.from(e.target.files || []))} />
      <div className="vc-view-cards">
        {cards.map((card, index) => (
          <div className={`vc-view-card ${uploadedViews[index] ? 'filled' : ''}`} key={card}>
            <span>{index + 1}</span><strong>{card}</strong><small>{uploadedViews[index]?.name || 'Recommended'}</small>
          </div>
        ))}
      </div>
      <div className="vc-actions"><button className="vc-ghost" onClick={onBack}>Back</button><button className="vc-primary" onClick={onNext}>Add policy proof <ArrowRight size={17} /></button></div>
    </div>
  )
}

function PolicyProofStep({ onUpload, fileName, busy, onRun, onBack }) {
  const inputRef = useRef(null)
  return (
    <div className="vc-form-step">
      <IconTile icon={FileText} tone="green" />
      <h2>Bring your policy into focus</h2>
      <p>We’ll read the important numbers so your payable amount is easy to understand.</p>
      <button className="vc-policy-upload" onClick={() => inputRef.current?.click()} disabled={busy}>
        <FileText size={25} />
        <span><strong>{fileName || 'Upload insurance policy'}</strong><small>PDF or clear photo · Max 15MB</small></span>
        <b>{busy ? 'Reading…' : 'Browse'}</b>
      </button>
      <input ref={inputRef} type="file" accept="application/pdf,image/png,image/jpeg" hidden onChange={(e) => onUpload(Array.from(e.target.files || []))} />
      <div className="vc-cover-note"><ShieldCheck size={18} /><span><strong>We’ll check your cover</strong><small>IDV · deductible · depreciation · NCB</small></span><b>Secure & private</b></div>
      <div className="vc-actions"><button className="vc-ghost" onClick={onBack}>Back</button><button className="vc-primary" onClick={onRun} disabled={busy}>{busy ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />} Run estimate</button></div>
    </div>
  )
}

function EstimateStep({ estimate, claim, onStartAgain, onViewReport, uploadedViews = [], policyFileName = '', onNeedPhotos, onNeedPolicy }) {
  const hasImages = Boolean((claim?.images?.length || 0) || uploadedViews.length)
  const hasPolicyProof = Boolean((claim?.documents?.length || 0) || policyFileName)

  if (!estimate?.ready) {
    const pricingNeeded = estimate?.status === 'NEEDS_PRICING_OR_MANUAL_ESTIMATE'
    const policyBlocked = ['EXPIRED_ON_ACCIDENT_DATE', 'NOT_ACTIVE_ON_ACCIDENT_DATE', 'EXPIRED_NOW'].includes(estimate?.status)
    return (
      <div className="vc-estimate-step">
        <div className="vc-estimate-head">
          <div>
            <div className="vc-ready pending"><Sparkles size={16} /> Estimate not ready</div>
            <h2>{policyBlocked ? 'Policy validity needs review.' : pricingNeeded ? 'Pricing information needed.' : 'Upload evidence first.'}</h2>
            <p>
              {policyBlocked
                ? (estimate?.policyStatus?.detail || 'Policy dates indicate the paperwork is expired or not active for this claim. Estimate is paused until insurer verification.')
                : pricingNeeded
                  ? 'Photos and policy were processed, but no configured price/manual repair estimate was available. The system will not invent a repair amount.'
                  : 'No preliminary amount is shown until accident photos and policy proof are uploaded and analyzed.'}
            </p>
          </div>
          <button className="vc-ghost" onClick={onStartAgain}>Start another <Plus size={16} /></button>
        </div>
        <div className="vc-evidence-required">
          <div className={hasImages ? 'done' : ''}>
            <span>{hasImages ? <Check size={16} /> : '1'}</span>
            <strong>Accident photos</strong>
            <p>{hasImages ? 'Uploaded and ready for analysis.' : 'Upload at least one clear vehicle damage photo.'}</p>
            {!hasImages ? <button className="vc-ghost" onClick={onNeedPhotos}>Upload photos</button> : null}
          </div>
          <div className={hasPolicyProof && !policyBlocked ? 'done' : policyBlocked ? 'warning' : ''}>
            <span>{policyBlocked ? '!' : hasPolicyProof ? <Check size={16} /> : '2'}</span>
            <strong>Policy proof</strong>
            <p>{policyBlocked ? (estimate?.policyStatus?.label || 'Policy not valid') : hasPolicyProof ? 'Policy proof is available and not expired based on extracted/configured dates.' : 'Upload policy PDF/photo so deductible and cover can be checked.'}</p>
            {!hasPolicyProof || policyBlocked ? <button className="vc-ghost" onClick={onNeedPolicy}>{policyBlocked ? 'Review policy' : 'Upload policy'}</button> : null}
          </div>
          <div className={pricingNeeded ? '' : hasImages && hasPolicyProof ? 'done' : ''}>
            <span>{pricingNeeded ? '!' : hasImages && hasPolicyProof ? <Check size={16} /> : '3'}</span>
            <strong>{pricingNeeded ? 'Pricing / repair estimate' : 'Run analysis'}</strong>
            <p>{pricingNeeded ? 'Add admin pricing or upload a repair estimate document to calculate settlement.' : 'The estimate will appear here only after analysis completes.'}</p>
          </div>
        </div>
        <div className="vc-why no-amount"><Sparkles size={17} /><span><strong>No amount generated yet.</strong> This avoids showing fake or demo settlement values before evidence is available.</span></div>
      </div>
    )
  }

  return (
    <div className="vc-estimate-step">
      <div className="vc-estimate-head"><div><div className="vc-ready"><Check size={16} /> Estimate ready</div><h2>Your claim, decoded.</h2><p>A transparent preview based on the details and damage views provided.</p></div><button className="vc-ghost" onClick={onStartAgain}>Start another <Plus size={16} /></button></div>
      <div className="vc-money-panel">
        <Money label="Estimated repair cost" value={formatINR(estimate.repair)} sub="Parts, labour and GST included" />
        <Money label="Insurer payable" value={formatINR(estimate.payable)} sub={`After ${formatINR(estimate.deductible)} deductible`} green />
        <Money label="You pay" value={formatINR(estimate.deductible)} amber />
      </div>
      <div className="vc-policy-check"><ShieldCheck size={17} /><span><strong>{estimate?.policyStatus?.label || 'Policy active / not expired'}</strong><small>{estimate?.policyStatus?.detail || 'Policy dates were checked before showing this estimate.'}</small></span></div>
      <div className="vc-confidence-title"><strong>Damage confidence</strong><span>Based on uploaded/demo views</span></div>
      <div className="vc-damage-list">
        {estimate.rows.map((row) => <DamageRow key={row.part} row={row} />)}
      </div>
      <div className="vc-why"><Sparkles size={17} /><span><strong>Why this estimate?</strong> Your uploaded evidence, deductible and configured/manual pricing were used. Final settlement may vary after insurer/surveyor verification.</span></div>
      <button className="vc-primary report-link" onClick={onViewReport}>View detailed explanation <ArrowRight size={17} /></button>
    </div>
  )
}

function AssessmentPreview({ incident, complete }) {
  return (
    <aside className="vc-preview-card">
      <div className="vc-preview-head"><span>Assessment preview</span><b className={complete ? 'complete' : ''}>{complete ? 'Complete' : 'In progress'}</b></div>
      <div className="vc-preview-photo"><CrashVisual /><span><MapPin size={14} /> {incident.location}</span></div>
      <dl>
        <dt>Vehicle</dt><dd>{incident.vehicle}</dd>
        <dt>Incident</dt><dd>{incident.description}</dd>
      </dl>
      <div className="vc-data-note"><ShieldCheck size={16} /><span><strong>Your data stays yours</strong><small>Encrypted and only used for this assessment.</small></span></div>
    </aside>
  )
}


const severityRank = { Unknown: 0, Minor: 1, Moderate: 2, Severe: 3 }

function cleanPartLabel(part = '') {
  return String(part || 'visible exterior panel')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function summarizeFindingsFromAssessment(claim, estimate, incident) {
  const raw = claim?.damage_assessments || []
  if (!raw.length) {
    return estimate.rows.map((row) => ({
      part: cleanPartLabel(row.part),
      type: row.action,
      severity: row.confidence >= 88 ? 'Severe' : row.confidence >= 78 ? 'Moderate' : 'Needs verification',
      confidence: row.confidence,
      explanation: `${row.action} cost has been included because this component is part of the visible impact estimate. A workshop/surveyor must confirm repair versus replacement before settlement.`
    }))
  }

  const grouped = new Map()
  for (const item of raw) {
    const confidence = Math.round((item.confidence || 0) * 100)
    if (confidence < 30 && raw.length > 3) continue
    const partKey = cleanPartLabel(item.damaged_part || 'visible exterior panel')
    const entry = grouped.get(partKey) || {
      part: partKey,
      types: new Set(),
      severity: 'Unknown',
      confidence: 0,
      area: 0
    }
    entry.types.add(String(item.damage_type || 'visible damage'))
    if (severityRank[item.severity] > severityRank[entry.severity]) entry.severity = item.severity
    entry.confidence = Math.max(entry.confidence, confidence)
    entry.area = Math.max(entry.area, Number(item.damage_area?.area_ratio || 0))
    grouped.set(partKey, entry)
  }

  return Array.from(grouped.values())
    .sort((a, b) => (severityRank[b.severity] - severityRank[a.severity]) || (b.confidence - a.confidence))
    .slice(0, 6)
    .map((entry) => ({
      part: entry.part,
      type: Array.from(entry.types).join(' + '),
      severity: entry.severity,
      confidence: entry.confidence,
      explanation: buildHumanDamageExplanation(entry, incident)
    }))
}

function buildHumanDamageExplanation(entry, incident) {
  const part = entry.part.toLowerCase()
  const types = Array.from(entry.types || []).join(' + ')
  const severityWord = String(entry.severity || 'review').toLowerCase()
  let detail = 'Inspect the exact panel location and confirm repair scope.'
  if (part.includes('headlight') || part.includes('headlamp')) {
    detail = 'Check lens surface, mounting tabs and lamp alignment.'
  } else if (part.includes('bumper')) {
    detail = 'Check bumper cover, clips, brackets and paint transfer.'
  } else if (part.includes('bonnet') || part.includes('hood')) {
    detail = 'Check panel gap, hood edge and latch alignment.'
  } else if (part.includes('fender')) {
    detail = 'Check wheel-arch edge, side panel scuffs and local denting.'
  } else if (part.includes('tail') || part.includes('boot') || part.includes('rear')) {
    detail = 'Rear-side signal; match it against rear-view evidence before inclusion.'
  } else if (part.includes('damage')) {
    detail = 'Close-up signal; map it to the exact vehicle component.'
  }
  return `${entry.part}: ${severityWord} ${types} signal. ${detail}`
}

function DetailedReport({ claim, estimate, incident, onBack, onStart }) {
  const vehicle = claim?.vehicle || {}
  const policy = claim?.policy || {}
  const policyStatus = estimate?.policyStatus || getPolicyValidity(policy, claim?.accident_date || defaultIncident.accident_date)
  const damageFindings = summarizeFindingsFromAssessment(claim, estimate, incident)
  const policyFactors = claim?.policy_json?.factors?.length ? claim.policy_json.factors : [
    { factor: 'Policy validity', evidence: 'Configured/demo comprehensive policy active for the accident date', effect: 'Supports preliminary own-damage assessment', status: 'ELIGIBLE' },
    { factor: 'Deductible / Excess', evidence: formatINR(estimate.deductible), effect: 'Reduced from estimated repair amount', status: 'APPLIED' },
    { factor: 'Final approval', evidence: 'Insurer survey and document verification pending', effect: 'Manual/insurer verification required', status: 'NEEDS_VERIFICATION' }
  ]
  const checks = claim?.verification_checks?.length ? claim.verification_checks : [
    { check_name: 'Image evidence', status: 'NEEDS_VERIFICATION', explanation: 'Photos are sufficient for preliminary estimate; final inspection may request more angles.' },
    { check_name: 'Policy proof', status: 'NEEDS_VERIFICATION', explanation: 'Policy fields are parsed/configured for decision support, not final approval.' },
    { check_name: 'Hidden damage', status: 'NEEDS_VERIFICATION', explanation: 'Internal/mechanical damage cannot be confirmed from exterior photos alone.' }
  ]
  const reportUrl = claim?.claim_id ? api.reportUrl(claim.claim_id) : null

  return (
    <main className="vc-main vc-report-page">
      <div className="vc-page-head compact">
        <div>
          <div className="vc-eyebrow"><span /> Detailed preliminary report</div>
          <h1>Explain the estimate.</h1>
          <p>See how incident details, visual findings, policy factors and deductible shaped the preliminary result.</p>
        </div>
        <div className="vc-report-actions">
          <button className="vc-ghost" onClick={onBack}>Back to estimate</button>
          {reportUrl ? (
            <a className="vc-primary" href={reportUrl} target="_blank" rel="noreferrer" download>
              Download PDF <ArrowRight size={17} />
            </a>
          ) : (
            <button className="vc-primary" onClick={onStart}>Create claim first <ArrowRight size={17} /></button>
          )}
        </div>
      </div>

      <section className="vc-report-summary">
        <div><small>Estimated repair cost</small><strong>{formatINR(estimate.repair)}</strong><span>Parts, labour and materials from configured/manual estimate</span></div>
        <div><small>Applicable deductible</small><strong>{formatINR(estimate.deductible)}</strong><span>Excess applied before settlement estimate</span></div>
        <div><small>Preliminary settlement</small><strong className="green">{formatINR(estimate.payable)}</strong><span>Not final approval or binding payout</span></div>
      </section>

      <section className="vc-report-grid">
        <article className="vc-report-card">
          <h2>1. Claim and vehicle information</h2>
          <dl className="vc-report-dl">
            <dt>Claim ID</dt><dd>{claim?.claim_id || 'Draft / demo preview'}</dd>
            <dt>Vehicle</dt><dd>{incident.vehicle}</dd>
            <dt>Registration Number</dt><dd>{vehicle.registration_number || defaultIncident.registration}</dd>
            <dt>Accident location</dt><dd>{incident.location}</dd>
            <dt>Incident summary</dt><dd>{incident.description}</dd>
          </dl>
        </article>
        <article className="vc-report-card">
          <h2>2. Policy information used</h2>
          <dl className="vc-report-dl">
            <dt>Policy type</dt><dd>{policy.policy_type || 'Comprehensive / Package Policy'}</dd>
            <dt>Policy number</dt><dd>{policy.policy_number || 'Configured/demo policy'}</dd>
            <dt>IDV</dt><dd>{formatINR(policy.idv || 850000)}</dd>
            <dt>Deductible</dt><dd>{formatINR(policy.deductible || estimate.deductible)}</dd>
            <dt>Policy validity</dt><dd><span className={`vc-policy-status ${policyStatus.status === 'ACTIVE' ? 'active' : 'warning'}`}>{policyStatus.label}</span></dd>
            <dt>Validity detail</dt><dd>{policyStatus.detail}</dd>
          </dl>
        </article>
      </section>

      <section className="vc-report-card full">
        <h2>3. Damaged part details</h2>
        <div className="vc-report-table">
          <div className="vc-report-tr head"><span>Damaged part</span><span>Damage type</span><span>Severity</span><span>Confidence</span><span>Explanation</span></div>
          {damageFindings.map((row, index) => (
            <div className="vc-report-tr" key={`${row.part}-${index}`}>
              <span>{row.part}</span>
              <span>{row.type}</span>
              <span>{row.severity}</span>
              <span>{row.confidence}%</span>
              <span>{row.explanation}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="vc-report-card full">
        <h2>4. Policy analysis reasoning</h2>
        <div className="vc-factor-list">
          {policyFactors.map((factor, index) => (
            <div className="vc-factor" key={`${factor.factor}-${index}`}>
              <b>{factor.factor}</b>
              <span>{factor.evidence}</span>
              <em>{factor.effect}</em>
              <strong>{factor.status}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="vc-report-card full">
        <h2>5. Evidence verification and manual-review checks</h2>
        <div className="vc-check-list">
          {checks.map((check, index) => (
            <div className="vc-check" key={`${check.check_name}-${index}`}>
              <span className="vc-check-dot" />
              <div><strong>{check.check_name}</strong><p>{check.explanation}</p></div>
              <b>{check.status}</b>
            </div>
          ))}
        </div>
      </section>

      <section className="vc-report-card full disclaimer-card">
        <h2>6. Claim disclaimer</h2>
        <p>
          AI-assisted preliminary assessment only. Final claim eligibility, repair assessment and settlement are subject to insurer verification,
          policy terms, documentation, inspection and applicable regulations.
        </p>
        <div className="vc-report-footer-actions">
          <button className="vc-ghost" onClick={onBack}>Back to estimate</button>
        </div>
      </section>
    </main>
  )
}

function PolicyFinder() {
  const policies = [
    { initials: 'HD', name: 'Demo Secure Motor', premium: 12840, idv: 850000, score: 94, features: ['Zero depreciation', 'Engine protection', '24/7 roadside assist'], best: true },
    { initials: 'IC', name: 'Complete Car Protect', premium: 11680, idv: 720000, score: 91, features: ['Consumables cover', 'Key replacement', 'Cashless garages'] },
    { initials: 'BA', name: 'Drive Smart Plus', premium: 10240, idv: 680000, score: 87, features: ['NCB protect', 'Personal accident', 'Fast-track claims'] }
  ]
  return (
    <main className="vc-main vc-policy-page">
      <div className="vc-page-head policy-head">
        <div>
          <div className="vc-eyebrow"><span /> Cover, without the confusion</div>
          <h1>Find your better cover.</h1>
          <p>Compare policies that fit your car, your roads and your peace of mind.</p>
        </div>
        <div className="vc-chip"><Car size={15} /> Hyundai Creta · Mumbai</div>
      </div>
      <section className="vc-match-hero">
        <div><Sparkles size={17} /><span>Personalized match</span><h2>Protection that <br />keeps up with you.</h2><p>Demo comparison scored against your vehicle profile and driving context.</p></div>
        <div className="vc-score"><small>Best match</small><strong>94</strong><span>/ 100</span></div>
      </section>
      <div className="vc-tabs"><button className="active">All cover</button><button>Lowest premium</button><button>Highest IDV</button><span>3 demo matches</span></div>
      <div className="vc-policy-grid">
        {policies.map((policy) => <PolicyCard key={policy.name} policy={policy} />)}
      </div>
      <p className="vc-disclaimer-line">Demo-only policy comparison UI. Upload/configure actual insurer wording and pricing before real-world use.</p>
    </main>
  )
}

function PolicyCard({ policy }) {
  return (
    <article className={`vc-policy-card ${policy.best ? 'best' : ''}`}>
      {policy.best ? <div className="vc-best-tag"><Sparkles size={14} /> Best fit for you</div> : null}
      <div className="vc-policy-top"><span>{policy.initials}</span><div><small>Demo insurer</small><strong>{policy.name}</strong></div><b>{policy.score}<em>match</em></b></div>
      <div className="vc-policy-money"><div><small>Annual premium</small><strong>{formatINR(policy.premium)}</strong></div><div><small>Max IDV</small><strong>{formatINR(policy.idv)}</strong></div></div>
      <ul>{policy.features.map((feature) => <li key={feature}><Check size={15} /> {feature}</li>)}</ul>
      <button>View policy details <ArrowRight size={16} /></button>
    </article>
  )
}

function CrashVisual({ large = false }) {
  return (
    <div className={`vc-crash-visual ${large ? 'large' : ''}`}>
      <img src={large ? crashHeroUrl : accidentPreviewUrl} alt="Damaged vehicle" />
    </div>
  )
}

function Stat({ label, value, sub, icon: Icon, tone }) {
  return <div className="vc-stat"><div><small>{label}</small><strong>{value}</strong><span>{sub}</span></div><i className={tone}><Icon size={20} /></i></div>
}

function RecentRow({ color, name, car, status, amount, onClick }) {
  return (
    <button className="vc-recent-row" onClick={onClick} type="button" aria-label={`Open assessment for ${name}`}>
      <span className={color}><Car size={18} /></span>
      <div><strong>{name}</strong><small>{car}</small></div>
      <b className={color}>{status}</b>
      <strong>{amount}</strong>
      <ArrowRight size={16} />
    </button>
  )
}

function IconTile({ icon: Icon, tone }) { return <div className={`vc-icon-tile ${tone}`}><Icon size={24} /></div> }
function Money({ label, value, sub, green, amber }) { return <div className={`vc-money ${green ? 'green' : ''} ${amber ? 'amber' : ''}`}><small>{label}</small><strong>{value}</strong>{sub ? <span>{sub}</span> : null}</div> }
function DamageRow({ row }) { return <div className="vc-damage-row"><span>!</span><div><strong>{row.part}</strong><small>{row.action}</small></div><i><b style={{ width: `${row.confidence}%` }} /></i><em>{row.confidence}%</em><strong>{formatINR(row.amount)}</strong></div> }

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
