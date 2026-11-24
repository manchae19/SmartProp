import React, { useEffect, useState } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { completeGoogleLink, errorText } from "./api.js";

export default function GoogleLinkCompleteView() {
  const router = useAppNavigation();
  const [state, setState] = useState({ busy: true, error: "", complete: false });

  useEffect(() => {
    let active = true;
    if (new URLSearchParams(window.location.search).get("status") === "failed") {
      setState({ busy: false, error: "Không thể xác minh tài khoản Google. Liên kết chưa được tạo; vui lòng bắt đầu lại từ phần Bảo mật.", complete: false });
      return () => { active = false; };
    }
    completeGoogleLink().then(() => {
      if (active) setState({ busy: false, error: "", complete: true });
    }).catch(error => {
      if (active) setState({ busy: false, error: errorText(error), complete: false });
    });
    return () => { active = false; };
  }, []);

  return <main className="sp-container py-16">
    <section className="mx-auto max-w-lg rounded-panel border border-brand-line bg-brand-card p-8">
      <p className="text-xs font-semibold tracking-widest text-brand-accent">{"SMARTPROP · BẢO MẬT"}</p>
      <h1 className="mt-3 text-2xl font-semibold">{"Liên kết Google"}</h1>
      {state.busy ? <p role="status" className="mt-4 text-sm leading-7 text-brand-muted">{"Đang kiểm tra phiên SmartProp và hoàn tất liên kết an toàn…"}</p> : state.complete ? <div>
        <p role="status" className="mt-4 text-sm leading-7 text-[var(--ui-success-text)]">{"Google đã được liên kết với tài khoản SmartProp của bạn. Tài khoản và phiên hiện tại vẫn được giữ nguyên."}</p>
        <button type="button" className="sp-button sp-button-primary mt-6" onClick={() => router.replace("/account")}>{"Quay lại Hồ sơ / Bảo mật"}</button>
      </div> : <div>
        <p role="alert" className="mt-4 text-sm leading-7 text-[var(--ui-error-text)]">{state.error}</p>
        <button type="button" className="sp-button sp-button-primary mt-6" onClick={() => router.replace("/account")}>{"Quay lại Hồ sơ / Bảo mật"}</button>
      </div>}
    </section>
  </main>;
}
