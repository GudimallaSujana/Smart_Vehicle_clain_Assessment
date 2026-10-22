import { useState } from 'react'
import { Eye, Layers } from 'lucide-react'
import { api } from '../lib/api'
import StatusBadge from './StatusBadge'

export default function DamageVisualization({ claim }) {
  const [mode, setMode] = useState('overlay')
  const images = claim?.images || []
  if (!images.length) {
    return <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-slate-500">No images uploaded yet.</div>
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-slate-900">Damage visualization</h3>
          <p className="text-sm text-slate-500">Toggle original photo and AI-analysis overlay. Confidence is model confidence, not approval probability.</p>
        </div>
        <div className="rounded-full bg-slate-100 p-1">
          <button onClick={() => setMode('original')} className={`rounded-full px-4 py-2 text-sm font-semibold ${mode === 'original' ? 'bg-white shadow text-brand-700' : 'text-slate-500'}`}>Original</button>
          <button onClick={() => setMode('overlay')} className={`rounded-full px-4 py-2 text-sm font-semibold ${mode === 'overlay' ? 'bg-white shadow text-brand-700' : 'text-slate-500'}`}>AI Analysis</button>
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {images.map((image) => (
          <div key={image.image_id} className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 p-4">
              <div>
                <div className="flex items-center gap-2 font-bold text-slate-900"><Layers size={18} /> {image.view_type || 'Evidence image'}</div>
                <div className="text-xs text-slate-500">{image.original_filename}</div>
              </div>
              <StatusBadge status={image.validation_status || image.quality_json?.status} />
            </div>
            <img
              className="h-72 w-full bg-slate-100 object-contain"
              src={api.imageUrl(claim.claim_id, image.image_id, mode === 'overlay')}
              alt={`${mode} ${image.original_filename}`}
            />
            <div className="space-y-2 p-4 text-sm text-slate-600">
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-slate-100 px-3 py-1">Blur: {image.quality_json?.blur_score ?? '—'}</span>
                <span className="rounded-full bg-slate-100 px-3 py-1">Brightness: {image.quality_json?.brightness ?? '—'}</span>
                <span className="rounded-full bg-slate-100 px-3 py-1">{image.quality_json?.width}×{image.quality_json?.height}</span>
              </div>
              {(image.analysis_json?.detections || []).map((det, idx) => (
                <div key={idx} className="rounded-2xl bg-slate-50 p-3">
                  <div className="font-semibold text-slate-800">{det.damage_type} · {det.damaged_part} · {det.severity}</div>
                  <div className="text-xs text-slate-500">Confidence {Math.round((det.confidence || 0) * 100)}% · {det.method}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
