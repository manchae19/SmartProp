import { useId } from 'react';
export default function DiscoveryIcon({ kind = 'robot', className = '' }) {
  const gradient = useId().replace(/:/g, '');
  const pin = kind === 'location';
  if (kind === 'search-home') return <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <rect x="3" y="3" width="34" height="34" rx="11" fill="#ffffff" fillOpacity=".12" />
    <path d="m9 19 11-9 11 9v11a1 1 0 0 1-1 1H11a1 1 0 0 1-1-1V19" stroke="#f5f8ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M16 31v-8h6" stroke="#f5f8ff" strokeWidth="1.8" strokeLinecap="round" />
    <circle cx="26" cy="23" r="4.5" fill="#254e7c" stroke="#dceaff" strokeWidth="1.8" />
    <path d="m29.5 26.5 4 4" stroke="#dceaff" strokeWidth="2.2" strokeLinecap="round" />
  </svg>;
  return <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <defs><linearGradient id={gradient} x1="8" y1="6" x2="32" y2="35" gradientUnits="userSpaceOnUse"><stop stopColor={pin ? '#b89aff' : '#68d3ff'} /><stop offset="1" stopColor={pin ? '#7043df' : '#2864e9'} /></linearGradient></defs>
    <ellipse cx="20" cy="35" rx={pin ? 8 : 12} ry="2.5" fill={pin ? '#8664e8' : '#3a80f5'} opacity=".15" />
    {pin ? <><path d="M20 3C12.8 3 8 8.3 8 14.7c0 8.4 12 19 12 19s12-10.6 12-19C32 8.3 27.2 3 20 3Z" fill={`url(#${gradient})`} /><circle cx="20" cy="14.5" r="5.2" fill="white" /><circle cx="20" cy="14.5" r="2.7" fill="#a78aef" /></> : <><path d="M20 9V5" stroke="#3977df" strokeWidth="2" strokeLinecap="round" /><circle cx="20" cy="4" r="2" fill="#9cc6ff" /><rect x="7" y="10" width="26" height="23" rx="9" fill={`url(#${gradient})`} /><rect x="3" y="17" width="4" height="10" rx="2" fill="#9dbbff" /><rect x="33" y="17" width="4" height="10" rx="2" fill="#9dbbff" /><rect x="11" y="15" width="18" height="11" rx="5" fill="#eaf5ff" /><circle cx="16" cy="20" r="2" fill="#235dbd" /><circle cx="24" cy="20" r="2" fill="#235dbd" /><path d="M17 29h6" stroke="#eaf5ff" strokeWidth="1.7" strokeLinecap="round" /></>}
  </svg>;
}
