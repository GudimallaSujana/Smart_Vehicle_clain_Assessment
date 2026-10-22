import { UploadCloud } from 'lucide-react'

export default function FileDropzone({ label, help, accept, multiple = true, onFiles, disabled = false }) {
  return (
    <label className={`group flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed p-8 text-center transition ${disabled ? 'border-slate-200 bg-slate-50 text-slate-400' : 'border-brand-200 bg-brand-50/60 text-slate-700 hover:border-brand-400 hover:bg-brand-50'}`}>
      <UploadCloud className="mb-3 text-brand-600 transition group-hover:-translate-y-1" size={36} />
      <span className="text-lg font-bold">{label}</span>
      <span className="mt-1 max-w-md text-sm text-slate-500">{help}</span>
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="hidden"
        onChange={(e) => onFiles?.(Array.from(e.target.files || []))}
      />
    </label>
  )
}
