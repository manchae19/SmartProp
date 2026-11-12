let loading;
export const hasGoogleMapsKey = () => !!import.meta.env?.VITE_GOOGLE_MAPS_API_KEY?.trim();
export function loadGoogleMaps() {
  if (globalThis.google?.maps?.importLibrary) return Promise.resolve(globalThis.google.maps);
  if (!hasGoogleMapsKey()) return Promise.reject(Error('GOOGLE_MAPS_NOT_CONFIGURED'));
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    let settled = false;
    const done = error => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      globalThis.__smartpropGoogleMapsReady = () => {};
      if (error) {
        script.remove();
        reject(Error('GOOGLE_MAPS_UNAVAILABLE'));
      } else resolve(globalThis.google.maps);
    };
    const timeout = setTimeout(() => done(true), 15000);
    globalThis.__smartpropGoogleMapsReady = () => done(!globalThis.google?.maps?.importLibrary);
    const prior = globalThis.gm_authFailure;
    globalThis.gm_authFailure = () => {
      done(true);
      globalThis.dispatchEvent(new Event('smartprop:google-maps-unavailable'));
      if (typeof prior === 'function') prior();
    };
    script.async = true;
    script.onerror = () => done(true);
    script.src = 'https://maps.googleapis.com/maps/api/js?' + new URLSearchParams({
      key: import.meta.env.VITE_GOOGLE_MAPS_API_KEY.trim(),
      v: 'weekly',
      loading: 'async',
      callback: '__smartpropGoogleMapsReady',
      language: 'vi',
      region: 'VN',
      libraries: 'places,marker'
    });
    document.head.appendChild(script);
  });
  loading = loading.catch(error => {
    loading = null;
    throw error;
  });
  return loading;
}
export const googleMapId = () => import.meta.env?.VITE_GOOGLE_MAPS_MAP_ID?.trim() || 'DEMO_MAP_ID';
