import CloseIcon from './CloseIcon.jsx';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { session } from '../../features/auth/api.js';
import './WelcomeNotice.css';
export default function WelcomeNotice() {
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const location = useLocation(),
    panel = useRef(null);
  const userId = session.getSnapshot().user?.id ?? null;
  const previous = useRef({
    path: null,
    userId
  });
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  useEffect(() => {
    const before = previous.current;
    const enteredHome = location.pathname === '/home' && before.path !== '/home';
    const loggedIn = userId !== null && userId !== before.userId;
    previous.current = {
      path: location.pathname,
      userId
    };
    if (enteredHome || loggedIn) setOpen(true);else if (before.userId !== null && userId === null) setOpen(false);
  }, [location.pathname, userId]);
  useEffect(() => {
    const dialog = panel.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    if (!open) return;
    const old = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = old;
      if (dialog.open) dialog.close();
    };
  }, [open]);
  const role = session.getSnapshot().user?.role;
  const posting = role === 'ADMIN' ? {
    to: '/admin/dashboard',
    label: 'Trang quản trị'
  } : role === 'BROKER' ? {
    to: '/post',
    label: 'Đăng tin mới'
  } : userId !== null ? {
    to: '/account/broker-application',
    label: 'Đăng ký quyền đăng tin'
  } : {
    to: '/register',
    label: 'Đăng ký tài khoản'
  };
  return <dialog ref={panel} className="welcome-notice" aria-labelledby="welcome-notice-title" onCancel={close} onClose={close} onClick={event => {
    if (event.target === panel.current) close();
  }}>
    <div className="welcome-notice-content">
      <header><span>SMARTPROP · THÔNG BÁO</span><button type="button" onClick={close} aria-label="Đóng thông báo" autoFocus><CloseIcon /></button></header>
      <div className="welcome-notice-body">
        <p className="welcome-notice-eyebrow">BẮT ĐẦU CÙNG SMARTPROP</p>
        <h2 id="welcome-notice-title">Tìm nhà phù hợp.<br />Đăng tin thuận tiện.</h2>
        <ol>
          <li><span className="welcome-notice-number">01</span><div><h3>Đăng tin bán hoặc cho thuê</h3><p>Đăng ký tài khoản, sau đó đăng ký quyền đăng tin trong Hồ sơ cá nhân. Bạn có thể đăng tin sau khi được quản trị viên phê duyệt.</p></div></li>
          <li><span className="welcome-notice-number">02</span><div><h3>Hoàn thiện thông tin cá nhân</h3><p>Cập nhật thông tin liên hệ và bổ sung nhu cầu sinh hoạt để nhận gợi ý phù hợp hơn.</p></div></li>
          <li><span className="welcome-notice-number">03</span><div><h3>Bật cá nhân hóa khi cần tư vấn</h3><p>Chọn tiện ích bạn quan tâm, ưu tiên quan trọng nhất và bật “Cho phép chatbot dùng thông tin này để tư vấn” trong trang Tài khoản.</p></div></li>
        </ol>
        <nav aria-label="Bắt đầu sử dụng SmartProp">
          <Link to={posting.to} onClick={close} className="sp-button sp-button-primary">{posting.label} ↗</Link>
          <Link to={userId === null ? '/login' : '/account'} onClick={close} className="sp-button sp-button-secondary">{userId === null ? 'Đăng nhập' : 'Cập nhật hồ sơ'} ↗</Link>
        </nav>
      </div>
      <footer><button type="button" className="sp-button sp-button-secondary" onClick={close}>Đã hiểu</button></footer>
    </div>
  </dialog>;
}
