import { useEffect, useRef, useState } from 'react';
import { SiteLink } from "../../app/navigation.jsx";
import PrivateImage from '../../shared/components/PrivateImage.jsx';
import { compactPrice, price, displayDecimal, types } from '../property/property.js';
import { publicMapPoint } from '../map/locationDisplay.js';
export default function PropertyCarousel({
  items = [],
  busy,
  error,
  onRetry
}) {
  const [index, setIndex] = useState(0),
    [type, setType] = useState(''),
    [paused, setPaused] = useState(false),
    [hover, setHover] = useState(false);
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const root = useRef(null),
    list = items.filter(p => !type || p.propertyType === type).sort((a, b) => Number(!!b.images?.length) - Number(!!a.images?.length)).slice(0, 5),
    count = list.length;
  const active = count ? index % count : 0;
  useEffect(() => {
    const q = window.matchMedia('(prefers-reduced-motion: reduce)'),
      f = () => setReduced(q.matches);
    q.addEventListener('change', f);
    return () => q.removeEventListener('change', f);
  }, []);
  useEffect(() => {
    if (paused || hover || reduced || count < 2) return;
    const timer = setInterval(() => {
      if (!document.hidden) setIndex(i => i + 1);
    }, 5500);
    return () => clearInterval(timer);
  }, [paused, hover, reduced, count]);
  const step = n => setIndex(i => (i + n + count) % Math.max(1, count));
  return <div className="light-carousel" role="region" aria-roledescription="carousel" aria-label="Bất động sản nổi bật" ref={root} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} onFocusCapture={() => setHover(true)} onBlurCapture={e => {
    if (!e.currentTarget.contains(e.relatedTarget)) setHover(false);
  }} onKeyDown={e => {
    if (e.target !== root.current && !e.target.hasAttribute('data-carousel-control')) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      step(e.key === 'ArrowLeft' ? -1 : 1);
    }
  }} tabIndex={0}>
    <div className="light-carousel-stage">
      {busy && !items.length ? <p className="light-carousel-empty" role="status">Đang tải tin nổi bật…</p> : error ? <div className="light-carousel-empty" role="alert">Chưa tải được tin. <button type="button" onClick={onRetry}>Thử lại</button></div> : !count ? <p className="light-carousel-empty">Chưa có tin thuộc loại hình này. <SiteLink to="/listings">Xem danh sách ↗</SiteLink></p> : list.map((p, i) => {
        let offset = (i - active + count) % count;
        if (offset > count / 2) offset -= count;
        const cover = p.images?.find(x => x.cover) || p.images?.[0];
        return <article key={p.id} data-featured-id={p.id} className={'light-slide' + (offset === 0 ? ' is-active' : '')} style={{
          '--offset': offset,
          '--depth': Math.abs(offset),
          zIndex: 5 - Math.abs(offset)
        }} aria-label={i + 1 + ' / ' + count}>
        <SiteLink className="light-slide-photo" to={'/listing/' + p.id} tabIndex={offset === 0 ? 0 : -1}>{cover?.url ? <PrivateImage src={cover.url} alt={p.title} /> : <span>Chưa có ảnh</span>}</SiteLink>
        <div className="light-slide-body"><p className="light-slide-meta">{p.district || p.city} · {types[p.propertyType] || p.propertyType}</p><h2 title={p.title}><SiteLink to={'/listing/' + p.id} tabIndex={offset === 0 ? 0 : -1}>{p.title}</SiteLink></h2><strong className="light-slide-price" title={price(p)}>{compactPrice(p)}</strong><p>{displayDecimal(p.areaSqmExact ?? p.areaSqm)} m²{p.bedrooms != null ? ' · ' + p.bedrooms + ' phòng ngủ' : ''}</p><div className="light-slide-links"><SiteLink to={'/listing/' + p.id} tabIndex={offset === 0 ? 0 : -1}>Khám phá không gian ↗</SiteLink>{publicMapPoint(p) && <SiteLink to={{
                path: '/map',
                query: {
                  propertyId: p.id
                }
              }} tabIndex={offset === 0 ? 0 : -1}>⌖ Bản đồ</SiteLink>}</div></div>
      </article>;
      })}
    </div>
    {count > 1 && <div className="light-carousel-controls"><button type="button" data-carousel-control aria-label="Tin trước" onClick={() => step(-1)}>←</button><div className="light-carousel-dots">{list.map((p, i) => <button type="button" key={p.id} aria-label={'Xem tin ' + (i + 1)} aria-current={i === active ? 'true' : undefined} onClick={() => setIndex(i)} />)}</div><button type="button" data-carousel-control aria-label="Tin tiếp theo" onClick={() => step(1)}>→</button><button type="button" aria-label={paused ? 'Tiếp tục carousel' : 'Tạm dừng carousel'} aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? '▷' : 'Ⅱ'}</button></div>}
    <div className="light-carousel-types" role="group" aria-label="Loại hình tin nổi bật">{Object.entries({
        '': 'Tất cả',
        HOUSE: 'Nhà phố',
        VILLA: 'Biệt thự',
        APARTMENT: 'Căn hộ'
      }).map(([key, label]) => <button type="button" key={key} aria-pressed={type === key} onClick={() => {
        setType(key);
        setIndex(0);
      }}>{label}</button>)}</div>
  </div>;
}
