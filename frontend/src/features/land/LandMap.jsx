import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { PLANNING_GROUPS, planningGroup, loadNeighbors, loadFloodMap, loadPlanningCells } from './landApi.js';
import './LandMap.css';

const COLOR = Object.fromEntries(PLANNING_GROUPS.map(([id, , color]) => [id, color]));
const CORRIDOR_METERS = 80;

// Width in pixels of an `meters`-wide band at the map centre, so the illustrative flood band
// keeps its ground size while zooming (it is a display aid, not a surveyed flood extent).
function metersToPixels(map, meters) {
  const lat = map.getCenter().lat;
  const metersPerPixel = 40075016.686 * Math.cos(lat * Math.PI / 180) / Math.pow(2, map.getZoom() + 8);
  return Math.max(2, meters / metersPerPixel);
}

/**
 * Map of one land record and its surroundings.
 * - recordId: source code or land UUID; null with floodIds shows only flood reference roads.
 * - floodIds: flood record ids to draw; defaults to the records linked to the selected plot.
 */
export default function LandMap({ recordId = null, floodIds = null, located = true, height = 320, onSelect, showAllFlood = true }) {
  const box = useRef(null), mapRef = useRef(null), cellsRef = useRef(null), floodRef = useRef(null), planningRef = useRef(null);
  const [expanded, setExpanded] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const boundsRef = useRef(null);
  useEffect(() => {
    const resize = () => mapRef.current?.invalidateSize();
    const timer = setTimeout(resize, 80);
    const close = e => { if (e.key === 'Escape') setExpanded(false); };
    window.addEventListener('keydown', close);
    return () => { clearTimeout(timer); window.removeEventListener('keydown', close); };
  }, [expanded]);
  const [hidden, setHidden] = useState(() => new Set());
  const [showFlood, setShowFlood] = useState(true);
  const [showWaterMarkers, setShowWaterMarkers] = useState(false);
  const [status, setStatus] = useState('loading');
  const [linkedFlood, setLinkedFlood] = useState([]);
  const [counts, setCounts] = useState({});

  useEffect(() => {
    if (!located || !box.current) return undefined;
    const map = L.map(box.current, { zoomControl: true, attributionControl: true, preferCanvas: true, scrollWheelZoom: true });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map);
    map.setView([15.99, 108.21], 15);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, [located]);

  // Planning cells around the record.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !recordId) { setStatus(recordId ? 'loading' : 'ready'); return undefined; }
    const controller = new AbortController();
    setStatus('loading');
    Promise.all([loadNeighbors(recordId, {signal: controller.signal}), loadPlanningCells()]).then(([data, planning]) => {
      if (controller.signal.aborted) return;
      planningRef.current?.remove();
      const tally = {};
      for (const feature of planning.features) {
        const p = feature.properties, group = planningGroup(p.planningCode, p.planningCategory);
        tally[group] = (tally[group] || 0) + 1;
      }
      planningRef.current = L.geoJSON(planning, {
        style: feature => { const p=feature.properties, group=planningGroup(p.planningCode,p.planningCategory); return {color:COLOR[group],weight:0.7,fillColor:COLOR[group],fillOpacity:0.65}; },
        onEachFeature: (feature, layer) => {
          layer.bindTooltip(feature.properties.id, {sticky:true});
          if (onSelect) layer.on('click', () => {
            if (layer.options.opacity !== 0) onSelect({sourceCode:feature.properties.id,id:feature.properties.id});
          });
        },
      }).addTo(map);
      cellsRef.current?.remove();
      const layer = L.geoJSON({...data, features:data.features.filter(f=>f.properties.selected)}, {
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, {radius: feature.properties.selected ? 10 : 6}),
        style: feature => {
          const p = feature.properties, group = planningGroup(p.planningCode, p.planningCategory);
          return { color: p.selected ? '#c1121f' : COLOR[group], weight: p.selected ? 4 : 0.6, fillColor: group === 'water' ? '#b8e0f3' : COLOR[group], fillOpacity: p.selected ? 0.55 : 0.35, opacity: 1 };
        },
        onEachFeature: (feature, l) => {
          const p = feature.properties;
          l.bindTooltip(p.displayName || p.id, { sticky: true });
          if (onSelect && !p.selected && p.landId) l.on('click', () => onSelect(p));
        },
      }).addTo(map);
      cellsRef.current = layer;
      setCounts(tally);
      const selected = data.features.find(f => f.properties.selected);
      setLinkedFlood(selected?.properties?.floodDisplay?.recordIds || []);
      if (selected) { boundsRef.current = L.geoJSON(selected).getBounds(); map.fitBounds(boundsRef.current, { maxZoom: 18, padding: [40, 40] }); }
      setStatus('ready');
    }).catch(error => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, [recordId, onSelect, attempt, located]);

  // Hide planning groups without redrawing the geometry.
  useEffect(() => {
    planningRef.current?.eachLayer(l => {
      const p = l.feature.properties, group = planningGroup(p.planningCode, p.planningCategory);
      const off = hidden.has(group) && !p.selected;
      l.setStyle?.(off ? { fillOpacity: 0, opacity: 0 } : { fillOpacity: 0.65, opacity: 1 });
      l.getElement?.()?.setAttribute('pointer-events', off ? 'none' : 'auto');
    });
  }, [hidden, status]);

  // Flood reference roads and the illustrative 80 m band.
  const ids = floodIds ?? (showAllFlood ? null : linkedFlood);
  useEffect(() => {
    const map = mapRef.current;
    floodRef.current?.remove(); floodRef.current = null;
    if (!map || (!showFlood && !showWaterMarkers) || (ids && !ids.length)) return undefined;
    const controller = new AbortController();
    loadFloodMap(ids ? ids.slice(0, 200) : null, {signal: controller.signal}).then(data => {
      const group = L.layerGroup();
      const band = L.geoJSON(data, { style: { color: '#7cc4f5', opacity: 0.35, weight: metersToPixels(map, CORRIDOR_METERS * 2), lineCap: 'round' }, interactive: false });
      const line = L.geoJSON(data, { style: { color: '#0b4f8a', weight: 3 }, onEachFeature: (f, l) => l.bindTooltip('💧 ' + (f.properties.roadName || 'Tuyến tham chiếu') + ' — tuyến có tên trong nguồn nguy cơ ngập') });
      if (showFlood) group.addLayer(band).addLayer(line);
      // A droplet marks an actual OSM vertex of a source reference road, never
      // a surveyed flood location or a fabricated parcel coordinate.
      for (const feature of (showWaterMarkers ? data.features : []).slice(0, 200)) {
        let point = feature.geometry?.coordinates;
        while (Array.isArray(point) && Array.isArray(point[0])) point = point[Math.floor(point.length / 2)];
        if (!Array.isArray(point) || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) continue;
        const label=document.createElement('span');
        label.textContent=(feature.properties.roadName||'Tuyến tham chiếu')+' · vị trí trên đường OSM, chưa xác định điểm ngập thực tế';
        L.marker([point[1],point[0]], {icon:L.divIcon({className:'land-water-marker',html:'💧',iconSize:[26,30],iconAnchor:[13,15]})}).bindTooltip(label).addTo(group);
      }
      group.addTo(map);
      const resize = () => band.setStyle({ weight: metersToPixels(map, CORRIDOR_METERS * 2) });
      map.on('zoomend', resize);
      group.on('remove', () => map.off('zoomend', resize));
      floodRef.current = group;
      if (!recordId && data.features.length) map.fitBounds(line.getBounds(), { maxZoom: 16, padding: [30, 30] });
    }).catch(() => {});
    return () => controller.abort();
  }, [ids?.join(',') ?? 'all', showFlood, showWaterMarkers, recordId, located]);

  if (!located) return <div className="land-map-empty" role="note">Hồ sơ chưa có tọa độ khớp riêng; không hiển thị vị trí hoặc ranh để tránh chỉ nhầm.</div>;
  const toggle = id => setHidden(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  return <div className={'land-map' + (expanded ? ' is-expanded' : '')}>
    <div className="land-map-tools">
      {recordId && <button type="button" onClick={() => {if(boundsRef.current)mapRef.current?.fitBounds(boundsRef.current,{maxZoom:18,padding:[40,40]});}}>Về vị trí đang xem</button>}
      <button type="button" aria-expanded={expanded} onClick={() => setExpanded(v=>!v)}>{expanded?'Thu gọn bản đồ':'Mở rộng bản đồ'}</button>
    </div>
    <div ref={box} className="land-map-canvas" style={{ height }} aria-label="Bản đồ ô quy hoạch và lớp ngập" />
    {status === 'loading' && <p className="land-map-status" role="status">Đang tải bản đồ…</p>}
    {status === 'error' && <p className="land-map-status" role="alert">Chưa tải được bản đồ của hồ sơ này. <button type="button" onClick={()=>setAttempt(x=>x+1)}>Thử lại</button></p>}
    <details className="land-map-legend">
      <summary>Chú giải và lớp bản đồ</summary>
      {recordId && <fieldset><legend>Màu quy hoạch</legend>
        {PLANNING_GROUPS.map(([id, label, color]) => <label key={id}>
          <input type="checkbox" checked={!hidden.has(id)} onChange={() => toggle(id)} />
          <span className="swatch" style={{ background: color }} />{label} <small>({counts[id] || 0})</small>
        </label>)}
      </fieldset>}
      <label><input type="checkbox" checked={showFlood} onChange={e => setShowFlood(e.target.checked)} />
        <span className="swatch flood" />Tuyến tham chiếu ngập và dải minh họa {CORRIDOR_METERS} m</label>
      <label><input type="checkbox" checked={showWaterMarkers} onChange={e => setShowWaterMarkers(e.target.checked)} />💧 Giọt nước tham chiếu (chưa xác minh điểm ngập)</label>
      <p>Dải xanh là minh họa quanh tuyến có tên trong nguồn, không phải ranh ngập đo đạc. Ô quy hoạch chưa phải ranh thửa địa chính.</p>
    </details>
  </div>;
}
