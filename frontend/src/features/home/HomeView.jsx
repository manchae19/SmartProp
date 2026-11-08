import React, { useEffect, useState } from 'react';
import { useSetup } from '../../shared/state/store.js';
import { useRouter, RouterLink } from '../../shared/routing/router.jsx';
import { usePublicListings } from '../property/usePublicListings.js';
import { usePublicProjects } from '../project/usePublicProjects.js';
import { useListingFilters } from '../property/useListingFilters.js';
import { listingLink, lifestylePresets } from '../property/listingFilters.js';
import { districts } from '../map/districts.js';
import { types } from '../property/property.js';
import { publicMapPoint } from '../map/locationDisplay.js';
import ListingFilters from '../property/ListingFilters.jsx';
import HomeGIS from '../map/HomeGIS.jsx';
import ProjectDirectory from '../project/ProjectDirectory.jsx';
import MarketSummary from '../market/MarketSummary.jsx';
import MarketIntelligence from '../market/MarketIntelligence.jsx';
import TopSearchedAreas from '../market/TopSearchedAreas.jsx';
import HomeSectionNav from './HomeSectionNav.jsx';
import PropertyCarousel from './PropertyCarousel.jsx';
import { LegacyState } from '../../shared/lib/legacy.js';
import './HomeView.css';

function setup() {
  const search = useListingFilters();
  return { search, state: usePublicListings(() => search.filters.value, { size: 6 }), projects: usePublicProjects({ size: 3 }) };
}
const banner = '/images/home/banner.png';
function SectionHeading({ eyebrow, title, description, to, link = 'Xem tất cả ↗' }) {
  return <div className="light-heading"><div><p className="light-eyebrow">{eyebrow}</p><h2>{title}</h2>{description && <p>{description}</p>}</div>{to && <RouterLink className="light-text-link" to={to}>{link}</RouterLink>}</div>;
}
export default function HomeView() {
  const ctx = useSetup(setup, {}), router = useRouter();
  const [filters, setFilters] = useState(() => ({ ...ctx.search.filters.value }));
  const [advanced, setAdvanced] = useState(false), [demo, setDemo] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const filterKey = JSON.stringify(ctx.search.filters.value);
  useEffect(() => setFilters(JSON.parse(filterKey)), [filterKey]);
  const items = ctx.state.items;
  const selected = items.find(p => p.id === selectedId) || items.find(publicMapPoint);
  const mapLink = listingLink('/map', ctx.search.filters.value, selected ? { propertyId: selected.id } : {});
  const goSearch = values => router.push(listingLink('/listings', values));
  const patch = (key, value) => setFilters(previous => ({ ...previous, [key]: value }));
  return <div className="home-light">
    <section id="home" className="light-hero" aria-labelledby="hero-title">
      <img className="light-banner" src={banner} alt="Minh họa Cầu Rồng Đà Nẵng và pháo hoa" fetchPriority="high" onError={e => { e.currentTarget.hidden = true; }} />
      <div className="light-hero-wash" />
      <div className="light-container light-hero-intro"><div><p className="light-eyebrow">ĐÀ NẴNG · KHÔNG GIAN SỐNG CỦA BẠN</p><h1 id="hero-title">Hiểu vị trí.<br /><span>Chọn không gian.</span></h1><p>Khám phá bất động sản tại Đà Nẵng.<br />Tìm đúng vị trí, đúng ngân sách, đúng kỳ vọng.</p><div className="light-actions"><a className="light-button" href="#search">⌕ &nbsp; Tìm kiếm ngay</a><RouterLink className="light-button secondary" to="/advisor">✧ &nbsp; Khám phá tư vấn AI</RouterLink></div></div><div className="light-hero-note"><strong>GIS</strong><span>Khám phá vị trí trực quan</span><strong>AI</strong><span>Gợi ý theo nhu cầu</span></div></div>
      <div className="light-container"><PropertyCarousel items={items} busy={ctx.state.busy} error={ctx.state.error} onRetry={() => ctx.state.load()} /></div>
    </section>
    <div id="search" className="light-container light-search-wrap">
      <div className="light-search"><div className="light-search-tabs"><strong>Tìm bất động sản</strong><RouterLink to={mapLink}>Khám phá bản đồ ↗</RouterLink><button onClick={() => setAdvanced(!advanced)} aria-expanded={advanced}>Tìm kiếm nâng cao {advanced ? '−' : '+'}</button></div>
        <form aria-label="Tìm kiếm nhanh" onSubmit={e => { e.preventDefault(); goSearch(filters); }}>
          <label>TỪ KHÓA<input value={filters.keyword || ''} onChange={e => patch('keyword', e.target.value)} placeholder="Tên tin, địa chỉ…" maxLength={200} /></label>
          <label>KHU VỰC<select value={filters.district || ''} onChange={e => patch('district', e.target.value)}><option value="">Đà Nẵng – Tất cả khu vực</option>{districts.filter(name => name !== 'Tất cả').map(name => <option key={name}>{name}</option>)}</select></label>
          <label>LOẠI BẤT ĐỘNG SẢN<select value={filters.propertyType || ''} onChange={e => patch('propertyType', e.target.value)}><option value="">Tất cả loại hình</option>{Object.entries(types).map(([key, name]) => <option value={key} key={key}>{name}</option>)}</select></label>
          <label>NGÂN SÁCH<select value={filters.maxPrice || ''} onChange={e => patch('maxPrice', e.target.value)}><option value="">Tất cả mức giá</option><option value="2000000000">Đến 2 tỷ</option><option value="5000000000">Đến 5 tỷ</option><option value="10000000000">Đến 10 tỷ</option></select></label>
          <button className="light-button" type="submit"><span aria-hidden="true">⌕</span> Tìm kiếm</button>
        </form>
        {advanced && <div className="light-advanced"><ListingFilters modelValue={filters} onUpdateModelValue={goSearch} /></div>}
      </div>
      <aside className="light-advisor"><span aria-hidden="true">✧</span><div><h2>Bạn có nhu cầu, SmartProp có gợi ý.</h2><p>Chọn ngân sách và khu vực – khám phá vị trí phù hợp cùng AI.</p></div><RouterLink className="light-button" to="/advisor">Khám phá tư vấn AI ↗</RouterLink></aside>
    </div>
    <HomeSectionNav filters={ctx.search.filters.value} district={ctx.search.filters.value.district} />
    <section id="gis" className="light-section light-tinted"><div className="light-container"><SectionHeading eyebrow="MỘT GÓC NHÌN, NHIỀU LỰA CHỌN" title="Hiểu vị trí. Chọn không gian." description="Khám phá vị trí thực của tin đăng và các tiện ích xung quanh." to={mapLink} link="Khám phá GIS đầy đủ ↗" /><div className="light-map-preview"><HomeGIS items={items} total={ctx.state.totalElements} selectedId={selected?.id} onUpdateSelectedId={setSelectedId} busy={ctx.state.busy} error={ctx.state.error} mapLink={mapLink} onRetry={() => ctx.state.load()} /></div></div></section>
    <section id="projects" className="light-section light-container"><SectionHeading eyebrow="DẤU ẤN THÀNH PHỐ" title="Dự án nổi bật tại Đà Nẵng." description="Tìm hiểu không gian sống từ các chủ đầu tư và đơn vị phát triển." to="/projects" link="Xem tất cả dự án ↗" /><ProjectDirectory limit={3} />
      <LegacyState state={ctx.projects} />{ctx.projects.items.length > 0 && <div className="light-backend-projects"><h3>Dự án trên SmartProp</h3>{ctx.projects.items.slice(0, 3).map(project => <RouterLink key={project.id} to={'/projects/' + project.id}><strong>{project.name}</strong><span>{project.developer || ''} ↗</span></RouterLink>)}</div>}
    </section>
    <section id="lifestyle" className="light-section light-tinted"><div className="light-container"><SectionHeading eyebrow="CHỌN THEO NHU CẦU" title="Một phong cách sống. Nhiều lựa chọn." description="Gợi ý theo tiêu chí tìm kiếm; không cam kết khoảng cách hay lợi nhuận." to="/listings" /><div className="light-lifestyles">{lifestylePresets.map(item => <RouterLink key={item.id} to={listingLink('/listings', item.filters)} title={item.explanation}><img src={'/media/projects/' + item.image + '.jpg'} alt="" loading="lazy" /><strong>{item.title} ↗</strong><span>{item.explanation}</span></RouterLink>)}</div></div></section>
    <section id="market" className="light-section light-container"><SectionHeading eyebrow="GÓC NHÌN TỪ DỮ LIỆU" title="Thị trường. Có cơ sở để hiểu." to="/market" link="Khám phá thị trường ↗" /><MarketSummary district={ctx.search.filters.value.district} /><p className="light-market-note">Khu vực gợi ý · Minh họa</p><TopSearchedAreas mode="listings" /><details className="light-demo" open={demo} onToggle={e => setDemo(e.currentTarget.open)}><summary>Biểu đồ mô phỏng · 3 / 6 / 12 tháng</summary>{demo && <MarketIntelligence />}</details></section>
    <section id="account" className="light-container light-tools"><div><p className="light-eyebrow">ĐI XA HƠN VỚI SMARTPROP</p><h2>Từ khám phá đến quyết định.</h2></div><div className="light-actions"><RouterLink className="light-button secondary" to="/valuation">Ước tính giá trị ↗</RouterLink><RouterLink className="light-button secondary" to="/advisor/chat">Trò chuyện AI ↗</RouterLink><RouterLink className="light-button" to="/account">Tài khoản của bạn ↗</RouterLink></div></section>
  </div>;
}
