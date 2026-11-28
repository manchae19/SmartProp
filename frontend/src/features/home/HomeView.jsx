import { useState, useRef } from 'react';
import { SiteLink } from "../../app/navigation.jsx";
import { usePublicListings } from '../property/usePublicListings.js';
import { usePublicProjects } from '../project/usePublicProjects.js';
import { useListingFilters } from '../property/useListingFilters.js';
import { listingLink, lifestylePresets } from '../property/listingFilters.js';
import { publicMapPoint } from '../map/locationDisplay.js';
import HomeGIS from '../map/HomeGIS.jsx';
import ProjectDirectory from '../project/ProjectDirectory.jsx';
import MarketSummary from '../market/MarketSummary.jsx';
import MarketIntelligence from '../market/MarketIntelligence.jsx';
import TopSearchedAreas from '../market/TopSearchedAreas.jsx';
import HomeSectionNav from './HomeSectionNav.jsx';
import { HomeNewsPreview } from '../news/NewsView.jsx';
import PropertyCarousel from './PropertyCarousel.jsx';
import ResourceState from "../../shared/components/ResourceState.jsx";
import AppIcon from '../../shared/components/AppIcon.jsx';
import DiscoveryIcon from '../../shared/components/DiscoveryIcon.jsx';
import './HomeView.css';
import './HomeProjects.css';
import './HomeLifestyle.css';
import './HomeLocationDiscovery.css';
import './HomeMarketStory.css';
import './HomeClosing.css';
import './HomeMarket.css';
function useHomeViewState(inputProps = {}, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const search = useListingFilters();
  const _searchLatest = useRef(search);
  _searchLatest.current = search;
  return {
    ...inputProps,
    search,
    state: usePublicListings(() => _searchLatest.current.filters, {
      size: 6
    }),
    projects: usePublicProjects({
      size: 3
    })
  };
}
const banner = '/images/home/banner.png';
function SectionHeading({
  eyebrow,
  title,
  description,
  to,
  link = 'Xem tất cả ↗'
}) {
  return <div className="light-heading"><div><p className="light-eyebrow">{eyebrow}</p><h2>{title}</h2>{description && <p>{description}</p>}</div>{to && <SiteLink className="light-text-link" to={to}>{link}</SiteLink>}</div>;
}
export default function HomeView() {
  const view = useHomeViewState({}, undefined);
  const [demo, setDemo] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const items = view.state.items;
  const selected = items.find(p => p.id === selectedId) || items.find(publicMapPoint);
  const mapLink = listingLink('/map', view.search.filters, selected ? {
    propertyId: selected.id
  } : {});
  return <div className="home-light">
    <section id="home" className="light-hero" aria-labelledby="hero-title">
      <img className="light-banner" src={banner} alt="Minh họa Cầu Rồng Đà Nẵng và pháo hoa" width="2200" height="1134" decoding="async" fetchPriority="high" onError={e => {
        e.currentTarget.hidden = true;
      }} />
      <div className="light-hero-wash" />
      <div className="light-container light-hero-intro"><div><p className="light-eyebrow">ĐÀ NẴNG · KHÔNG GIAN SỐNG CỦA BẠN</p><h1 id="hero-title">Hiểu vị trí.<br /><span>Chọn không gian.</span></h1><p>Khám phá bất động sản tại Đà Nẵng.<br />Tìm đúng vị trí, đúng ngân sách, đúng kỳ vọng.</p></div><nav className="light-hero-shortcuts" aria-label="Khám phá SmartProp">
        <p className="light-shortcuts-heading">BẮT ĐẦU KHÁM PHÁ</p>
        <SiteLink className="light-shortcut is-primary" to={listingLink('/listings', view.search.filters)}>
          <span className="light-shortcut-icon discovery"><DiscoveryIcon kind="search-home" /></span>
          <span className="light-shortcut-copy"><strong>Tìm kiếm ngay</strong><small>Khám phá tin đăng phù hợp</small></span>
          <AppIcon name="arrow" className="light-shortcut-arrow" />
        </SiteLink>
        <SiteLink className="light-shortcut" to="/advisor">
          <span className="light-shortcut-icon discovery"><DiscoveryIcon /></span>
          <span className="light-shortcut-copy"><strong><span>AI tư vấn</span>{' '}<span>bất động sản</span></strong><small>Gợi ý theo nhu cầu của bạn</small></span>
          <AppIcon name="arrow" className="light-shortcut-arrow" />
        </SiteLink>
        <SiteLink className="light-shortcut" to={mapLink}>
          <span className="light-shortcut-icon discovery"><DiscoveryIcon kind="location" /></span>
          <span className="light-shortcut-copy"><strong><span>Bản đồ GIS</span>{' '}<span>và tiện ích</span></strong><small>Xem bất động sản trên bản đồ</small></span>
          <AppIcon name="arrow" className="light-shortcut-arrow" />
        </SiteLink>
      </nav></div>
      <div id="search" className="light-container"><PropertyCarousel items={items} busy={view.state.busy} error={view.state.error} onRetry={() => view.state.load()} /></div>
    </section>
    <HomeSectionNav filters={view.search.filters} district={view.search.filters.district} />
    <section id="gis" className="light-section light-tinted"><div className="light-container"><SectionHeading eyebrow="KHÁM PHÁ KHÔNG GIAN SỐNG" title={<><span>Mỗi vị trí.</span><span>Một góc nhìn mới.</span></>} description="Khám phá vị trí bất động sản và các tiện ích xung quanh trên bản đồ." to={mapLink} link="Khám phá GIS đầy đủ ↗" /><div className="light-map-preview"><HomeGIS items={items} total={view.state.totalElements} selectedId={selected?.id} onUpdateSelectedId={setSelectedId} busy={view.state.busy} error={view.state.error} mapLink={mapLink} onRetry={() => view.state.load()} /></div></div></section>
    <HomeNewsPreview />
    <section id="projects" className="light-section light-container"><SectionHeading eyebrow="DỰ ÁN THÀNH PHỐ" title="Dự án nổi bật tại Đà Nẵng." description="Tìm hiểu không gian sống từ các chủ đầu tư và đơn vị phát triển." to="/projects" link="Xem tất cả dự án ↗" /><ProjectDirectory limit={3} />
      <ResourceState state={view.projects} />{view.projects.items.length > 0 && <div className="light-backend-projects"><h3>Dự án trên SmartProp</h3>{view.projects.items.slice(0, 3).map(project => <SiteLink key={project.id} to={'/projects/' + project.id}><strong>{project.name}</strong><span>{project.developer || ''} ↗</span></SiteLink>)}</div>}
    </section>
    <section id="lifestyle" className="light-section light-tinted"><div className="light-container"><SectionHeading eyebrow="CHỌN THEO NHU CẦU" title="Một phong cách sống. Nhiều lựa chọn." description="Gợi ý theo tiêu chí tìm kiếm; không cam kết khoảng cách hay lợi nhuận." to="/listings" /><div className="light-lifestyles">{lifestylePresets.map(item => <SiteLink key={item.id} to={listingLink('/listings', item.filters)} title={item.explanation}><div className="lifestyle-image"><img src={'/media/projects/' + item.image + '.jpg'} alt="" width="640" height="400" decoding="async" loading="lazy" /></div><strong>{item.title}<span className="lifestyle-arrow" aria-hidden="true">↗</span></strong><span>{item.explanation}</span></SiteLink>)}</div></div></section>
    <section id="market" className="light-section light-container"><SectionHeading eyebrow="GÓC NHÌN TỪ DỮ LIỆU" title="Thị trường. Có cơ sở để hiểu." to="/market" link="Khám phá thị trường ↗" /><MarketSummary district={view.search.filters.district} /><p className="light-market-note">Khám phá 7 quận/huyện · Minh họa biểu trưng trung lập</p><TopSearchedAreas mode="listings" /><details className="light-demo" open={demo} onToggle={e => setDemo(e.currentTarget.open)}><summary><span className="market-story-title">Biểu đồ trình diễn giao diện<span className="market-story-meta">Dữ liệu mô phỏng UI (không phải thống kê thực tế hay AI V1.3)</span></span><span className="market-story-toggle">{demo ? 'Thu gọn' : 'Xem minh họa'}<span className="market-story-chevron" aria-hidden="true" /></span></summary><MarketIntelligence /></details></section>
    <section id="account" className="light-container light-tools"><div><p className="light-eyebrow">ĐI XA HƠN VỚI SMARTPROP</p><h2>Từ khám phá đến quyết định.</h2></div><div className="light-actions"><SiteLink className="light-button secondary" to="/valuation">Ước tính giá trị ↗</SiteLink><SiteLink className="light-button secondary" to="/advisor/chat">Trò chuyện AI ↗</SiteLink><SiteLink className="light-button" to="/account">Tài khoản của bạn ↗</SiteLink></div></section>
  </div>;
}
