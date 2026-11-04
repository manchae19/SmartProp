import { listingLink } from '../features/property/listingFilters.js'
import { isPublisher } from '../features/property/postForm.js'

export function siteNavigation(filters = {}) {
  return [
    { key: 'home', label: 'Trang chủ', to: listingLink('/home', filters) },
    { key: 'properties', label: 'Bất động sản', to: listingLink('/listings', filters) },
    { key: 'projects', label: 'Dự án', to: { path: '/projects' } },
    { key: 'gis', label: 'Bản đồ GIS', to: listingLink('/map', filters) },
    { key: 'market', label: 'Dữ liệu thị trường', to: { path: '/market' } },
    { key: 'tools', label: 'Công cụ', to: { path: '/valuation' } },
    { key: 'advisor', label: 'Tư vấn BĐS', to: { path: '/advisor' } },
  ]
}
export function activeNavigation(key, route) {
  const path = route.path || '', hash = route.hash || ''
  if (key === 'properties') return path === '/listings' || path.startsWith('/listing/') || path === '/home' && ['#properties', '#search'].includes(hash)
  if (key === 'projects') return path === '/projects' || path.startsWith('/projects/') || path === '/home' && hash === '#projects'
  if (key === 'gis') return path === '/map' || path === '/home' && hash === '#gis'
  if (key === 'market') return path === '/market' || path.startsWith('/market/') || path === '/home' && ['#market', '#market-current'].includes(hash)
  if (key === 'tools') return path === '/valuation'
  if (key === 'advisor') return path === '/advisor' || path.startsWith('/advisor/')
  return key === 'home' && path === '/home' && !['#properties', '#search', '#projects', '#gis', '#market', '#market-current'].includes(hash)
}
export const canPublish = isPublisher
export const canAccessAdmin = user => user?.status === 'ACTIVE' && user?.role === 'ADMIN'
export const usesPageLayout = path => !['/login', '/register', '/reset-password'].includes(path) && path !== '/admin' && !path.startsWith('/admin/')
export function homeSectionId(hash) {
  const id = String(hash || '').replace(/^#/, '')
  if (id === 'search') return 'properties'
  return ['home', 'properties', 'gis', 'lifestyle', 'market', 'market-current', 'projects', 'account'].includes(id) ? id : null
}
export function navigationOffset() {
  if (typeof document === 'undefined') return 0
  return (document.querySelector('.app-header')?.offsetHeight || 0) + (document.querySelector('.home-section-nav')?.offsetHeight || 0) + 16
}
export function scrollHomeSection(id) {
  const target = document.getElementById(homeSectionId(id))
  if (!target) return
  window.scrollTo({ top: Math.max(0, target.getBoundingClientRect().top + window.scrollY - navigationOffset()), behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
}
