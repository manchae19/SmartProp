import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './CoordinateReviewMap.css';

/**
 * Bản đồ xác minh tọa độ cho admin.
 *
 * Chỉ hiển thị marker khi có tọa độ hợp lệ. Không tự di chuyển marker, không tự suy
 * ranh giới thửa đất. Admin nhìn đúng dữ liệu backend trả về.
 */
export default function CoordinateReviewMap({ latitude, longitude, address, district, ward, mismatch }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [baseLayer, setBaseLayer] = useState('street');
  const [tileError, setTileError] = useState('');

  const hasPoint = Number.isFinite(latitude) && Number.isFinite(longitude)
    && Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180;

  useEffect(() => {
    if (!containerRef.current || !hasPoint) return undefined;

    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, {
        center: [latitude, longitude],
        zoom: 16,
        scrollWheelZoom: true,
      });
      mapRef.current.attributionControl.setPrefix('');
    }

    const map = mapRef.current;

    // Đổi lớp nền: gỡ lớp cũ trước khi thêm lớp mới.
    map.eachLayer(layer => {
      if (layer instanceof L.TileLayer) map.removeLayer(layer);
    });

    const url = baseLayer === 'satellite'
      ? 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
      : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const attribution = baseLayer === 'satellite'
      ? 'Ảnh vệ tinh: Esri World Imagery'
      : '&copy; OpenStreetMap';

    const tiles = L.tileLayer(url, { attribution, maxZoom: 19 });
    tiles.on('tileerror', () => setTileError('Không tải được lớp nền bản đồ.'));
    tiles.addTo(map);

    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    const icon = L.divIcon({
      className: 'review-marker' + (mismatch ? ' is-mismatch' : ''),
      html: '<span></span>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
    markerRef.current = L.marker([latitude, longitude], { icon, keyboard: false })
      .addTo(map)
      .bindPopup(
        `<strong>${escapeHtml(address || 'Chưa có địa chỉ')}</strong><br/>`
        + `${escapeHtml([ward, district].filter(Boolean).join(', '))}<br/>`
        + `${latitude.toFixed(7)}, ${longitude.toFixed(7)}`,
      );

    map.setView([latitude, longitude], map.getZoom());

    return undefined;
  }, [latitude, longitude, address, district, ward, mismatch, baseLayer, hasPoint]);

  useEffect(() => () => {
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
      markerRef.current = null;
    }
  }, []);

  if (!hasPoint) {
    return (
      <div className="review-map review-map--empty" role="status">
        Tin này chưa có tọa độ hợp lệ để hiển thị trên bản đồ.
      </div>
    );
  }

  return (
    <div className="review-map">
      <div className="review-map__toolbar">
        <div className="review-map__layers" role="group" aria-label="Lớp nền bản đồ">
          <button
            type="button"
            className={baseLayer === 'street' ? 'is-active' : ''}
            aria-pressed={baseLayer === 'street'}
            onClick={() => setBaseLayer('street')}
          >
            Đường phố
          </button>
          <button
            type="button"
            className={baseLayer === 'satellite' ? 'is-active' : ''}
            aria-pressed={baseLayer === 'satellite'}
            onClick={() => setBaseLayer('satellite')}
          >
            Vệ tinh
          </button>
        </div>
        <button
          type="button"
          className="review-map__recenter"
          onClick={() => mapRef.current?.setView([latitude, longitude], 17)}
        >
          Về vị trí tin đăng
        </button>
      </div>
      <div ref={containerRef} className="review-map__canvas" aria-label="Bản đồ vị trí tin đăng" />
      {tileError && <p className="review-map__error" role="alert">{tileError}</p>}
      <p className="review-map__coords">
        {latitude.toFixed(7)}, {longitude.toFixed(7)}
      </p>
    </div>
  );
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}
