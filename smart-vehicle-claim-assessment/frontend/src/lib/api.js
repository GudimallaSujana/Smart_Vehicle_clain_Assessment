const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })
  if (!res.ok) {
    let detail = `Request failed: ${res.status}`
    try {
      const data = await res.json()
      detail = data.message || data.detail || detail
    } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  listClaims: () => request('/claims'),
  createClaim: (payload) => request('/claims', { method: 'POST', body: JSON.stringify(payload) }),
  getClaim: (id) => request(`/claims/${id}`),
  uploadImage: (claimId, file, viewType) => {
    const form = new FormData()
    form.append('file', file)
    form.append('view_type', viewType)
    return request(`/claims/${claimId}/images`, { method: 'POST', body: form })
  },
  uploadDocument: (claimId, file, documentType) => {
    const form = new FormData()
    form.append('file', file)
    form.append('document_type', documentType)
    return request(`/claims/${claimId}/documents`, { method: 'POST', body: form })
  },
  analyzeClaim: (id) => request(`/claims/${id}/analyze`, { method: 'POST' }),
  seedDemo: () => request('/demo/seed', { method: 'POST' }),
  getMetrics: () => request('/research/metrics'),
  getPricing: () => request('/admin/pricing?demo_only=true'),
  addPricing: (item) => request('/admin/pricing', { method: 'POST', body: JSON.stringify(item) }),
  reportUrl: (id) => `${API_BASE}/claims/${id}/report`,
  imageUrl: (claimId, imageId, overlay = false) => `${API_BASE}/claims/${claimId}/images/${imageId}/file?overlay=${overlay}`
}

export function formatINR(value) {
  if (value === null || value === undefined || value === '') return 'Not available'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value))
}

export function classNames(...items) {
  return items.filter(Boolean).join(' ')
}
