import React from "react";
import { useSetup, propsForSetup } from "../../shared/state/store.js";
import { mergeProps, renderList, display, rootProps } from "../../shared/components/rendering.js";
import { ref, computed, watch, onBeforeUnmount } from "../../shared/state/store.js";
import { api, session, errorText } from "../auth/api.js";

/**
 * YOLOv8 object analysis panel for a listing.
 *
 * Deliberately worded as an observation, never a certification: it lists what a
 * model reported, and says so. It must never read as "this interior is verified"
 * or as a claim about bedrooms, area or legal status.
 */
const statusLabels = {
  PENDING: "Đang chờ phân tích",
  ANALYZING: "Đang phân tích ảnh",
  HAS_OBJECTS: "Có đối tượng được nhận diện",
  NO_OBJECTS: "Không phát hiện đối tượng",
  FAILED: "Không thể phân tích",
  NO_IMAGES: "Chưa có ảnh để phân tích",
  UNAVAILABLE: "Chưa bật phân tích ảnh",
};

const imageStatusLabels = {
  PENDING: "Đang chờ",
  SCANNING: "Đang phân tích",
  COMPLETED: "Hoàn tất",
  PENDING_RETRY: "Sẽ thử lại",
};

function setup(__props) {
  const props = propsForSetup(__props, {
    propertyId: String,
    compact: { type: Boolean, default: false },
  });
  const analysis = ref(null);
  const error = ref("");
  const loading = ref(false);
  const expanded = ref(false);
  let timer = null;
  let serial = 0;

  const status = computed(() => analysis.value?.status || (loading.value ? "ANALYZING" : ""));
  const statusLabel = computed(() => statusLabels[status.value] || "Chưa phân tích");
  const isAnalyzing = computed(() => ["PENDING", "ANALYZING"].includes(status.value));

  // Aggregate counts across every image of the listing.
  const totals = computed(() => {
    const merged = {};
    for (const image of analysis.value?.images || []) {
      for (const [label, count] of Object.entries(image.countsByLabel || {})) {
        merged[label] = (merged[label] || 0) + count;
      }
    }
    return Object.entries(merged).sort((a, b) => b[1] - a[1]);
  });

  const totalDetections = computed(() =>
    (analysis.value?.images || []).reduce((sum, image) => sum + (image.detectionCount || 0), 0)
  );

  const documentImages = computed(() =>
    (analysis.value?.images || []).filter((image) => image.documentHint?.likelyDocument)
  );

  const hasObjects = computed(() => totalDetections.value > 0);

  async function load() {
    if (!props.propertyId) return;
    const run = ++serial;
    loading.value = true;
    try {
      const result = await api(
        "/properties/" + encodeURIComponent(props.propertyId) + "/image-analysis",
        { authenticated: !!session.token }
      );
      if (run === serial) {
        analysis.value = result;
        error.value = "";
      }
    } catch (e) {
      if (run === serial) error.value = errorText(e);
    } finally {
      if (run === serial) {
        loading.value = false;
        if (timer) clearTimeout(timer);
        timer = null;
        if (isAnalyzing.value) timer = setTimeout(load, 2500);
      }
    }
  }

  watch(() => props.propertyId, load, { immediate: true });
  onBeforeUnmount(() => {
    serial++;
    if (timer) clearTimeout(timer);
  });

  return {
    props,
    analysis,
    error,
    loading,
    status,
    statusLabel,
    isAnalyzing,
    totals,
    totalDetections,
    documentImages,
    hasObjects,
    expanded,
    load,
  };
}

export default React.forwardRef(function ImageAnalysisSection(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className: "bg-brand-card rounded-3xl p-5 shadow-sm border border-brand-line",
        "data-sp-image-analysis": "",
      })}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-brand-navy">{"Phân tích nội dung ảnh"}</h3>
          <p className="text-[11px] text-brand-muted mt-1">
            {"Nhận diện đồ vật trong ảnh bằng YOLOv8. Đây là quan sát của mô hình, không phải xác nhận nội thất hay pháp lý của bất động sản."}
          </p>
        </div>
        <span className="text-[11px] font-bold text-brand-muted shrink-0">
          {display(ctx.statusLabel)}
        </span>
      </div>

      {ctx.error ? (
        <p className="text-xs text-[var(--ui-danger-text)] mt-3">
          {"Không thể phân tích: " + ctx.error}
        </p>
      ) : null}

      {ctx.hasObjects ? (
        <div className="mt-4">
          <p className="text-xs font-semibold text-brand-navy">
            {ctx.totalDetections + " đối tượng trong " + (ctx.analysis?.images?.length || 0) + " ảnh"}
          </p>
          <ul className="mt-2 flex flex-wrap gap-2" data-analysis-labels>
            {renderList(ctx.totals, (entry) => (
              <li
                key={entry[0]}
                className="rounded-full bg-brand-cream px-3 py-1 text-xs font-semibold text-brand-navy"
              >
                {entry[0] + " × " + entry[1]}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {ctx.status === "NO_OBJECTS" ? (
        <p className="text-xs text-brand-muted mt-3">
          {"Không phát hiện đồ vật nào thuộc danh sách hỗ trợ. Ảnh có thể là ngoại thất, giấy tờ, hoặc chỉ chứa đồ vật mô hình không nhận diện được."}
        </p>
      ) : null}

      {ctx.documentImages.length ? (
        <p
          className="text-[11px] text-brand-muted mt-3 rounded-xl bg-amber-50 p-2.5"
          data-analysis-document
        >
          {"Có " + ctx.documentImages.length + " ảnh giống giấy tờ/văn bản. Kết quả nhận diện trên ảnh này không đáng tin — hãy xem trực tiếp."}
        </p>
      ) : null}

      {ctx.status === "UNAVAILABLE" ? (
        <p className="text-xs text-brand-muted mt-3" data-analysis-unavailable>
          {"Tính năng phân tích ảnh chưa được bật trên hệ thống này. Phần kiểm tra ảnh trùng vẫn hoạt động bình thường."}
        </p>
      ) : null}

      {ctx.status === "FAILED" ? (
        <p className="text-[11px] text-brand-muted mt-3">
          {"Hệ thống sẽ thử lại khi bạn lưu hoặc gửi duyệt."}
        </p>
      ) : null}

      {ctx.analysis?.images?.length ? (
        <div className="mt-3">
          <button
            type="button"
            className="text-xs font-bold text-[var(--ui-accent)]"
            data-analysis-toggle
            onClick={() => (ctx.expanded = !ctx.expanded)}
          >
            {ctx.expanded ? "Thu gọn chi tiết" : "Xem chi tiết từng ảnh"}
          </button>
          {ctx.expanded ? (
            <ul className="mt-2 grid gap-2" data-analysis-details>
              {renderList(ctx.analysis.images, (image) => (
                <li
                  key={image.imageId}
                  className="rounded-2xl border border-brand-line p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-brand-navy">
                      {imageStatusLabels[image.status] || image.status}
                    </span>
                    <span className="text-brand-muted">
                      {image.detectionCount + " đối tượng"}
                    </span>
                  </div>
                  {image.detectionCount > 0 ? (
                    <p className="text-brand-muted mt-1">
                      {Object.entries(image.countsByLabel || {})
                        .map(([label, count]) => label + " × " + count)
                        .join(" · ")}
                    </p>
                  ) : null}
                  {image.documentHint?.likelyDocument ? (
                    <p className="text-brand-muted mt-1">Ảnh giống giấy tờ — kết quả chỉ tham khảo.</p>
                  ) : null}
                  {image.errorCode ? (
                    <p className="text-brand-muted mt-1">{"Lỗi: " + image.errorCode}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {ctx.analysis?.limitations?.length ? (
        <p className="text-[10px] text-brand-muted mt-3 leading-relaxed">
          {ctx.analysis.limitations[0]}
        </p>
      ) : null}
    </section>,
  ]);
});
