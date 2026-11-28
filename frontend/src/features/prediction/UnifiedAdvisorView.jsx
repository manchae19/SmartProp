import React, { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { SiteLink as RouterLink } from '../../app/navigation.jsx'
import { api, session, errorText } from '../auth/api.js'
import { districts } from '../map/districts.js'
import {
  advisorDistrictSuggestions,
  advisorResearchActorKey,
  effectiveBudgetPreview,
  formatAdvisorBudget,
  parseAdvisorBudget,
} from './advisorAnalysis.js'
import { createUnifiedAdvisorController } from './unifiedAdvisorState.js'
import AdvisorResults from './AdvisorResults.jsx'
import './advisorAnalysis.css'

const PRESETS = [1000000000, 2000000000, 3500000000, 5000000000, 10000000000]
const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value) || 0)

/**
 * Unified AI Advisor (ADVISOR_ORCHESTRATOR_V1) — the multi-evidence consultation
 * flow. Separate route/API from the Messenger RAG chat (/advisor, /advisor/chat).
 */
export default function UnifiedAdvisorView() {
  const [controller] = useState(() => createUnifiedAdvisorController({ api, session, errorText }))
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot)
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot)
  const { form, busy, error, result, submitted, selectedPoiId, researchAvailable } = state

  useEffect(() => controller.mount(), [controller])

  const canViewResearch = researchAvailable === true && advisorResearchActorKey(auth) !== ''
  const researchModeActive = canViewResearch && form.includeResearch === true

  const budgetHint = useMemo(() => {
    try {
      const preview = effectiveBudgetPreview(form.budgetVnd, form.budgetFlexibilityPct)
      const flex = preview.budgetFlexibilityPct > 0 ? `+${preview.budgetFlexibilityPct}%` : '0%'
      return `Ngân sách gốc: ${money(preview.statedBudgetVnd)} · Trần linh hoạt (${flex}): ${money(preview.effectiveCeilingVnd)}`
    } catch {
      return 'Nhập tổng ngân sách VNĐ bằng số nguyên, ví dụ 3.500.000.000'
    }
  }, [form.budgetVnd, form.budgetFlexibilityPct])

  const districtSuggestions = useMemo(
    () => advisorDistrictSuggestions(districts, result, canViewResearch),
    [result, canViewResearch]
  )

  const submittedSummary = useMemo(() => {
    if (!submitted || (submitted.includeResearch && !canViewResearch)) return ''
    const flex = submitted.budgetFlexibilityPct > 0 ? ` (+${submitted.budgetFlexibilityPct}% linh hoạt)` : ''
    const purpose = { LIVING: 'Mua để ở', INVESTMENT: 'Đầu tư', RENTAL: 'Mua khai thác cho thuê' }[submitted.purpose]
    return [
      money(submitted.budgetVnd) + flex,
      purpose,
      submitted.propertyType === 'ALL' ? 'Tất cả loại hình' : submitted.propertyType,
      submitted.district || 'Toàn khu vực Đà Nẵng',
      submitted.ward,
      submitted.minAreaSqm ? `Từ ${submitted.minAreaSqm} m²` : '',
    ].filter(Boolean).join(' · ')
  }, [submitted, canViewResearch])

  const visibleResult = result && (result.mode !== 'INTERNAL_RESEARCH' || canViewResearch) ? result : null

  return (
    <section className="advisor-page" aria-labelledby="advisor-title">
      <div className="advisor-intro">
        <p className="eyebrow">SMARTPROP · AI ADVISOR ORCHESTRATOR</p>
        <h1 id="advisor-title">Tư vấn bất động sản đa bằng chứng</h1>
        <p>
          Kết hợp xếp hạng phù hợp theo nhu cầu &amp; tiện ích khu vực (Hybrid V1.1), bằng chứng bất động sản tương đồng
          và định giá tham chiếu độc lập XGBoost V1.3 kèm giải thích TreeSHAP trong một luồng tư vấn thống nhất.
        </p>
      </div>

      <div className="quick-links">
        <RouterLink to="/valuation" className="advisor-btn secondary">Công cụ định giá AI độc lập ↗</RouterLink>
        <RouterLink to="/comparables" className="advisor-btn secondary">Tìm tin tương đồng ↗</RouterLink>
        <RouterLink to="/advisor/chat" className="advisor-btn secondary">Trò chuyện trợ lý AI (RAG) ↗</RouterLink>
      </div>

      <div className={`safe-note${researchModeActive ? ' research-note' : ''}`}>
        <span aria-hidden="true">{researchModeActive ? '!' : '✓'}</span>
        <div>
          <strong>{researchModeActive ? 'Chế độ nghiên cứu nội bộ (ADMIN · TiniX CC BY-NC 4.0)' : 'Chế độ công khai an toàn (SAFE)'}</strong>
          <p>
            {researchModeActive
              ? 'Bao gồm quan sát lịch sử TiniX AI đã lọc holdout — chỉ phục vụ nghiên cứu phi thương mại, không xem là tin đang bán.'
              : 'Chỉ sử dụng bất động sản và bằng chứng đối chiếu công khai hợp lệ; không truy xuất hoặc hiển thị dữ liệu nghiên cứu TiniX.'}
          </p>
        </div>
      </div>

      {canViewResearch ? (
        <div className="research-controls">
          <button
            type="button"
            className="advisor-btn secondary"
            aria-pressed={researchModeActive}
            onClick={() => controller.toggleResearch()}
          >
            {researchModeActive ? 'Quay lại chế độ công khai SAFE' : 'Bật dữ liệu nghiên cứu TiniX (Chỉ ADMIN)'}
          </button>
        </div>
      ) : null}

      <form className="advisor-form" aria-busy={busy} onSubmit={(e) => controller.submit(e)}>
        <div className="form-heading">
          <div>
            <h2>Tiêu chí tư vấn của bạn</h2>
            <p>Nhập ngân sách mục tiêu, mức linh hoạt tài chính và mục đích sử dụng bất động sản.</p>
          </div>
          <span className="required-note">* Thông tin bắt buộc</span>
        </div>

        <fieldset disabled={busy}>
          <div className="form-grid">
            <label>
              Ngân sách mục tiêu (VNĐ) *
              <input
                value={form.budgetVnd}
                inputMode="numeric"
                maxLength={32}
                required
                aria-describedby="budget-hint"
                autoComplete="off"
                onChange={(e) => controller.patch('budgetVnd', e.target.value)}
                onBlur={() => { try { controller.patch('budgetVnd', formatAdvisorBudget(form.budgetVnd)) } catch { /* keep invalid input */ } }}
              />
              <small id="budget-hint" data-budget-hint>{budgetHint}</small>
              <span className="budget-presets">
                {PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    aria-pressed={(() => { try { return parseAdvisorBudget(form.budgetVnd) === preset } catch { return false } })()}
                    onClick={() => controller.patch('budgetVnd', formatAdvisorBudget(String(preset)))}
                  >
                    {(preset / 1000000000).toString().replace('.', ',')} tỷ
                  </button>
                ))}
              </span>
            </label>

            <label>
              Biên ngân sách linh hoạt
              <select value={form.budgetFlexibilityPct} onChange={(e) => controller.patch('budgetFlexibilityPct', Number(e.target.value))}>
                <option value={0}>0% — Không vượt ngân sách</option>
                <option value={10}>+10% — Linh hoạt nhẹ</option>
                <option value={15}>+15% — Linh hoạt vừa</option>
                <option value={20}>+20% — Mở rộng cân nhắc</option>
              </select>
              <small>Các tin vượt ngân sách gốc sẽ được gắn nhãn cảnh báo riêng.</small>
            </label>

            <label>
              Mục đích mua *
              <select value={form.purpose} onChange={(e) => controller.patch('purpose', e.target.value)}>
                <option value="LIVING">Mua để ở thực (LIVING)</option>
                <option value="INVESTMENT">Mua đầu tư (INVESTMENT)</option>
                <option value="RENTAL">Mua khai thác cho thuê (RENTAL)</option>
              </select>
            </label>

            <label>
              Loại bất động sản *
              <select value={form.propertyType} onChange={(e) => controller.patch('propertyType', e.target.value)}>
                <option value="ALL">Tất cả loại hình</option>
                <option value="HOUSE">Nhà ở / Nhà phố</option>
                <option value="APARTMENT">Căn hộ chung cư</option>
                <option value="LAND">Đất nền</option>
                <option value="VILLA">Biệt thự</option>
                <option value="ROOM">Phòng cho thuê</option>
                <option value="COMMERCIAL">Thương mại / Mặt bằng</option>
              </select>
            </label>

            <label>
              Quận / Huyện ưu tiên
              <input list="advisor-districts" value={form.district} maxLength={100} placeholder="Tất cả khu vực" autoComplete="off" onChange={(e) => controller.patch('district', e.target.value)} />
              <small>Để trống hoặc nhập “Tất cả” để quét toàn Đà Nẵng.</small>
            </label>

            <label>
              Phường / Xã
              <input value={form.ward} maxLength={100} placeholder="Không bắt buộc" onChange={(e) => controller.patch('ward', e.target.value)} />
            </label>

            <label>
              Diện tích tối thiểu (m²)
              <input type="number" min="0.1" max="1000000" step="any" value={form.minAreaSqm} placeholder="Không giới hạn" onChange={(e) => controller.patch('minAreaSqm', e.target.value)} />
            </label>

            <label>
              Số lượng đề xuất
              <select value={form.limit} onChange={(e) => controller.patch('limit', Number(e.target.value))}>
                <option value={5}>Tối đa 5 bất động sản</option>
                <option value={10}>Tối đa 10 bất động sản</option>
              </select>
            </label>
          </div>

          <div className="evidence-options">
            <label className="check-pill">
              <input type="checkbox" checked={form.includeValuation} onChange={(e) => controller.patch('includeValuation', e.target.checked)} />
              <span>Định giá tham chiếu XGBoost V1.3 &amp; giải thích TreeSHAP</span>
            </label>
            <label className="check-pill">
              <input type="checkbox" checked={form.includeComparables} onChange={(e) => controller.patch('includeComparables', e.target.checked)} />
              <span>Đối chiếu bất động sản tương đồng (Comparable Evidence)</span>
            </label>
          </div>

          <datalist id="advisor-districts">
            {districtSuggestions.map((district) => <option key={district} value={district} />)}
          </datalist>

          <div className="form-footer">
            <p>Điểm phù hợp và định giá V1.3 là bằng chứng hỗ trợ quyết định độc lập; không thay thế thẩm định pháp lý hoặc khảo sát thực địa.</p>
            <div className="form-actions">
              <button className="advisor-btn secondary" type="button" onClick={() => controller.reset()}>Đặt lại</button>
              <button className="advisor-btn primary" type="submit" data-advisor-submit>{busy ? 'Đang tổng hợp tư vấn…' : 'Nhận tư vấn AI'}</button>
            </div>
          </div>
        </fieldset>
      </form>

      {error ? (
        <div role="alert" className="advisor-error" data-advisor-error>
          <div>
            <strong>Chưa thể tải kết quả tư vấn</strong>
            <p>{error}</p>
          </div>
          <button type="button" className="advisor-btn secondary" onClick={() => controller.submit()}>Thử lại</button>
        </div>
      ) : null}

      {busy ? (
        <div role="status" className="loading-panel" data-advisor-loading>
          <span className="loading-spinner" aria-hidden="true" />
          <div>
            <strong>Đang phân tích nhu cầu &amp; đối chiếu bằng chứng…</strong>
            <p>Đang xếp hạng khu vực, bất động sản phù hợp, mẫu tương đồng và mô hình định giá V1.3.</p>
          </div>
        </div>
      ) : null}

      {visibleResult ? (
        <>
          <div className="submitted-heading">
            <h2 tabIndex={-1}>Báo cáo tư vấn theo nhu cầu</h2>
            <p>{submittedSummary}</p>
          </div>
          <AdvisorResults
            result={visibleResult}
            selectedPoiId={selectedPoiId}
            onFocusPoi={({ poiId }) => controller.setSelectedPoiId(poiId)}
            canViewResearch={canViewResearch}
          />
        </>
      ) : null}

      {!visibleResult && !busy && !error ? (
        <div className="start-note">
          <strong>Quy trình tư vấn minh bạch &amp; không tự bịa số liệu</strong>
          <p>
            Nhấn “Nhận tư vấn AI” để xem tối đa 5 khu vực phù hợp nhất và danh sách bất động sản kèm điểm thành phần,
            tiện ích khu vực, mẫu tương đồng thực tế và mức định giá tham chiếu XGBoost V1.3 giải thích bằng TreeSHAP.
          </p>
        </div>
      ) : null}
    </section>
  )
}
