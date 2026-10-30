<script setup>
import { computed, ref, nextTick } from 'vue'
const tab = ref('valuation')
const valuationButton = ref(null), loanButton = ref(null)
async function handleTabKey(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  tab.value = event.key === 'Home' ? 'valuation' : event.key === 'End' ? 'loan' : tab.value === 'valuation' ? 'loan' : 'valuation'
  await nextTick()
  ;(tab.value === 'valuation' ? valuationButton.value : loanButton.value)?.focus()
}
const valuation = ref({ area: 80, unitPrice: 45, adjustment: 0 })
const loan = ref({ propertyPrice: 4, downPayment: 30, years: 20, interest: 9 })
const complete = values => Object.values(values).every(value => value !== '' && value != null && Number.isFinite(Number(value)))
const validValuation = computed(() => complete(valuation.value) && Number(valuation.value.area) > 0 && Number(valuation.value.unitPrice) > 0 && Number(valuation.value.adjustment) >= -100)
const estimate = computed(() => validValuation.value ? Number(valuation.value.area) * Number(valuation.value.unitPrice) * 1e6 * (1 + Number(valuation.value.adjustment) / 100) : null)
const validLoan = computed(() => complete(loan.value) && Number(loan.value.propertyPrice) > 0 && Number(loan.value.downPayment) >= 0 && Number(loan.value.downPayment) <= 100 && Number(loan.value.years) >= 1 && Number(loan.value.years) <= 50 && Number(loan.value.interest) >= 0 && Number(loan.value.interest) <= 100)
const principal = computed(() => Number(loan.value.propertyPrice) * 1e9 * (1 - Number(loan.value.downPayment) / 100))
const monthly = computed(() => {
  if (!validLoan.value) return null
  const months = Math.round(Number(loan.value.years) * 12), rate = Number(loan.value.interest) / 1200
  return rate === 0 ? principal.value / months : principal.value * rate / (1 - (1 + rate) ** -months)
})
const money = value => value == null || !Number.isFinite(value) ? '—' : Math.round(value).toLocaleString('vi-VN') + ' ₫'
defineExpose({ select: value => { tab.value = value === 'investment' ? 'loan' : 'valuation' } })
</script>
<template>
  <div class="finance-box">
    <div class="finance-tabs" role="tablist" aria-label="Công cụ tài chính" @keydown="handleTabKey"><button id="valuation-tab" ref="valuationButton" type="button" role="tab" :aria-selected="tab === 'valuation'" aria-controls="valuation-panel" :tabindex="tab === 'valuation' ? 0 : -1" @click="tab = 'valuation'">Ước tính giá trị</button><button id="loan-tab" ref="loanButton" type="button" role="tab" :aria-selected="tab === 'loan'" aria-controls="loan-panel" :tabindex="tab === 'loan' ? 0 : -1" @click="tab = 'loan'">Tính khoản vay</button></div>
    <div v-show="tab === 'valuation'" id="valuation-panel" role="tabpanel" aria-labelledby="valuation-tab" class="finance-panel">
      <div><h3>Chủ động ước tính theo giả định của bạn</h3><RouterLink to="/valuation" class="mt-3 inline-block text-sm font-semibold underline">Tham khảo giá bằng mô hình v6 ↗</RouterLink><p>Phép tính diện tích × đơn giá × điều chỉnh do bạn nhập. Đây không phải định giá AI hoặc kết quả thẩm định.</p><div class="finance-inputs"><label>Diện tích (m²)<input v-model="valuation.area" type="number" min="0.01" step="0.01" /></label><label>Đơn giá (triệu VND/m²)<input v-model="valuation.unitPrice" type="number" min="0.01" step="0.01" /></label><label>Điều chỉnh (%)<input v-model="valuation.adjustment" type="number" min="-100" step="0.1" /></label></div></div>
      <div class="finance-result" aria-live="polite"><small>GIÁ TRỊ THAM KHẢO</small><strong>{{ money(estimate) }}</strong><p v-if="!validValuation">Nhập diện tích, đơn giá lớn hơn 0 và điều chỉnh từ −100%.</p><p v-else>Kết quả dựa hoàn toàn trên giả định bạn cung cấp, không ghi vào tin đăng.</p></div>
    </div>
    <div v-show="tab === 'loan'" id="loan-panel" role="tabpanel" aria-labelledby="loan-tab" class="finance-panel">
      <div><h3>Lên kế hoạch khoản vay mua nhà</h3><p>Ước tính khoản trả góp đều với lãi suất cố định. Chưa gồm phí, bảo hiểm hoặc biến động lãi suất của ngân hàng.</p><div class="finance-inputs"><label>Giá bất động sản (tỷ VND)<input v-model="loan.propertyPrice" type="number" min="0.01" step="0.01" /></label><label>Trả trước (%)<input v-model="loan.downPayment" type="number" min="0" max="100" /></label><label>Thời hạn (năm)<input v-model="loan.years" type="number" min="1" max="50" /></label><label>Lãi suất (%/năm)<input v-model="loan.interest" type="number" min="0" max="100" step="0.1" /></label></div></div>
      <div class="finance-result" aria-live="polite"><small>TRẢ GÓP ƯỚC TÍNH / THÁNG</small><strong>{{ money(monthly) }}</strong><p v-if="validLoan">Khoản vay: {{ money(principal) }}</p><p v-else>Kiểm tra giá, tỷ lệ trả trước 0–100%, thời hạn 1–50 năm và lãi suất 0–100%.</p><p>Đây là công cụ tham khảo, không phải cam kết cấp tín dụng.</p></div>
    </div>
  </div>
</template>
<style scoped>
.finance-box{border:1px solid #e7e1d7;border-radius:24px;background:white;overflow:hidden}.finance-tabs{display:flex;border-bottom:1px solid #e7e1d7;padding:18px 24px;gap:12px}.finance-tabs button{padding:12px 20px;background:#f1eee8;border-radius:30px;font-size:13px;font-weight:650;cursor:pointer}.finance-tabs button[aria-selected=true]{background:#142b4f;color:white}.finance-panel{display:grid;grid-template-columns:1.4fr 1fr;gap:35px;padding:32px}.finance-panel h3{font-size:23px;font-weight:650;line-height:1.4}.finance-panel p{color:#536178;font-size:13px;line-height:1.9;margin-top:12px}.finance-inputs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:25px}label{display:flex;flex-direction:column;gap:9px;font-size:12px;color:#536178}input{width:100%;min-height:45px;border:1px solid #d7dce4;border-radius:10px;padding:10px 12px;color:#142b4f}.finance-result{border-radius:18px;background:#142b4f;padding:28px;color:#fff;align-self:stretch;display:flex;flex-direction:column;justify-content:center}.finance-result small{letter-spacing:.15em;font-size:13px;color:#dfbe86}.finance-result strong{font-size:clamp(25px,2.7vw,35px);margin:18px 0 6px;overflow-wrap:anywhere}.finance-result p{color:#ced6e3;font-size:12px}:focus-visible{outline:3px solid #b3915f;outline-offset:3px}@media(max-width:850px){.finance-panel{grid-template-columns:1fr;gap:24px;padding:22px}.finance-result{padding:24px}.finance-tabs{padding:16px;gap:7px}.finance-tabs button{padding:11px 16px}}@media(max-width:400px){.finance-inputs{grid-template-columns:1fr}}
</style>
