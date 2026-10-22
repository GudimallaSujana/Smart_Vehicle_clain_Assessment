export default function VehicleIllustration() {
  return (
    <svg viewBox="0 0 760 520" className="h-full w-full" role="img" aria-label="Vehicle insurance illustration">
      <defs>
        <linearGradient id="carBody" x1="0" x2="1" y1="0" y2="1">
          <stop stopColor="#2563eb" />
          <stop offset="1" stopColor="#0f766e" />
        </linearGradient>
        <linearGradient id="shield" x1="0" x2="1">
          <stop stopColor="#f59e0b" />
          <stop offset="1" stopColor="#fde68a" />
        </linearGradient>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="18" stdDeviation="18" floodColor="#0f172a" floodOpacity="0.18" />
        </filter>
      </defs>
      <rect width="760" height="520" rx="42" fill="#eff6ff" />
      <circle cx="624" cy="100" r="72" fill="#dbeafe" />
      <circle cx="116" cy="410" r="90" fill="#ccfbf1" />
      <g filter="url(#shadow)">
        <path d="M154 298c18-58 63-105 116-105h211c58 0 100 43 124 105l39 9c29 7 49 32 49 62v38H75v-38c0-30 20-55 49-62l30-9Z" fill="url(#carBody)" />
        <path d="M261 216h214c32 0 62 26 79 70H182c18-42 45-70 79-70Z" fill="#bfdbfe" opacity="0.95" />
        <path d="M325 216v70M476 216l38 70" stroke="#1e3a8a" strokeWidth="9" strokeLinecap="round" opacity="0.35" />
        <rect x="106" y="330" width="92" height="36" rx="16" fill="#fde68a" />
        <rect x="568" y="330" width="92" height="36" rx="16" fill="#fecaca" />
        <circle cx="205" cy="407" r="62" fill="#0f172a" />
        <circle cx="555" cy="407" r="62" fill="#0f172a" />
        <circle cx="205" cy="407" r="30" fill="#94a3b8" />
        <circle cx="555" cy="407" r="30" fill="#94a3b8" />
        <rect x="319" y="342" width="127" height="35" rx="10" fill="#f8fafc" />
        <text x="382" y="365" textAnchor="middle" fontSize="18" fontWeight="700" fill="#0f172a">TS 09 AB 1234</text>
      </g>
      <g transform="translate(515 76)" filter="url(#shadow)">
        <path d="M72 0 136 25v54c0 52-28 88-64 107C36 167 8 131 8 79V25L72 0Z" fill="url(#shield)" />
        <path d="m39 82 22 22 44-56" fill="none" stroke="#0f172a" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <g transform="translate(124 104)">
        <rect x="0" y="0" width="178" height="128" rx="22" fill="white" opacity="0.92" />
        <path d="M30 38h118M30 65h84M30 92h132" stroke="#2563eb" strokeWidth="12" strokeLinecap="round" opacity="0.35" />
      </g>
      <path d="M167 305c41 20 82 16 123 3" stroke="#ef4444" strokeWidth="12" strokeLinecap="round" strokeDasharray="24 16" />
      <path d="M183 334 294 304M201 358l72-18" stroke="#7f1d1d" strokeWidth="7" strokeLinecap="round" />
    </svg>
  )
}
