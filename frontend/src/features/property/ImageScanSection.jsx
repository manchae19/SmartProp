import React from "react";
import {
  useSetup,
  propsForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  renderList,
  display,
  rootProps,
} from "../../shared/components/rendering.js";
import {
  ref,
  computed,
  watch,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { RouterLink } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import PrivateImage from "../../shared/components/PrivateImage.jsx";

const labels = {
  PENDING: "Đang chờ kiểm tra",
  SCANNING: "Đang kiểm tra ảnh",
  CLEAN: "Không phát hiện ảnh trùng",
  MATCHES: "Có ảnh tương đồng",
  FAILED: "Không thể kiểm tra",
  NO_IMAGES: "Chưa có ảnh để kiểm tra",
};

function setup(__props) {
  const props = propsForSetup(__props, {
    propertyId: String,
    compact: { type: Boolean, default: false },
  });
  const scan = ref(null);
  const error = ref("");
  const loading = ref(false);
  let timer = null;
  let serial = 0;

  const groups = computed(() => {
    const grouped = new Map();
    for (const result of scan.value?.images || []) {
      for (const match of [...(result.matches || []), ...(result.intraMatches || [])]) {
        const intra = match.classification?.startsWith("INTRA_");
        const key = intra ? "intra:" + match.propertyId : "listing:" + match.propertyId;
        const previous = grouped.get(key);
        if (!previous || Number(match.similarity) > Number(previous.similarity)) {
          grouped.set(key, {
            ...match,
            sourceImageId: result.imageId,
            intra: !!intra,
          });
        }
      }
    }
    return [...grouped.values()].slice(0, 5);
  });
  const status = computed(() => scan.value?.status || (loading.value ? "SCANNING" : ""));
  const statusLabel = computed(() => labels[status.value] || "Đang kiểm tra ảnh");
  const isScanning = computed(() => ["PENDING", "SCANNING"].includes(status.value));
  const hasMatches = computed(() => groups.value.length > 0);

  async function load() {
    if (!props.propertyId) return;
    const run = ++serial;
    loading.value = true;
    try {
      const result = await api(
        "/properties/" + encodeURIComponent(props.propertyId) + "/image-scan",
        { authenticated: !!session.token },
      );
      if (run === serial) {
        scan.value = result;
        error.value = "";
      }
    } catch (e) {
      if (run === serial) error.value = errorText(e);
    } finally {
      if (run === serial) {
        loading.value = false;
        if (timer) clearTimeout(timer);
        timer = null;
        if (isScanning.value) timer = setTimeout(load, 2500);
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
    scan,
    error,
    loading,
    groups,
    status,
    statusLabel,
    isScanning,
    hasMatches,
    load,
  };
}

export default React.forwardRef(function ImageScanSection(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className:
          "bg-brand-card rounded-3xl p-5 shadow-sm border border-brand-line",
        "data-sp-image-scan": "",
      })}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-brand-navy">
            {"Kiểm tra hình ảnh"}
          </h3>
          <p className="text-[11px] text-brand-muted mt-1">
            {"So khớp nội bộ với ảnh của các tin đang công khai. Đây là tín hiệu tham khảo, không phải kết luận gian lận."}
          </p>
        </div>
        <span className="text-[11px] font-bold text-brand-muted shrink-0">
          {display(ctx.statusLabel)}
        </span>
      </div>
      {ctx.error ? (
        <p className="text-xs text-[var(--ui-danger-text)] mt-3">
          {"Không thể kiểm tra: " + ctx.error}
        </p>
      ) : null}
      {ctx.hasMatches ? (
        <div className="mt-4 grid gap-2">
          {renderList(ctx.groups, (match) => (
            <div
              key={[match.classification, match.propertyId, match.imageId].join("|")}
              className="flex gap-3 rounded-2xl border border-brand-line p-2.5"
            >
              <PrivateImage
                src={match.imageUrl}
                alt="Ảnh đối chiếu"
                className="w-16 h-16 rounded-xl object-cover shrink-0"
              />
              <div className="min-w-0 text-xs">
                <p className="font-bold text-brand-navy truncate">
                  {match.intra
                    ? "Ảnh trùng trong cùng tin"
                    : "Ảnh tương đồng với tin khác"}
                </p>
                <p className="text-brand-muted mt-0.5">
                  {match.classification === "EXACT_DUPLICATE" ||
                  match.classification === "INTRA_EXACT_DUPLICATE"
                    ? "Trùng khớp chính xác"
                    : match.classification === "NEAR_DUPLICATE" ||
                        match.classification === "INTRA_NEAR_DUPLICATE"
                      ? "Rất giống"
                      : "Tương đồng"}
                  {match.similarity != null
                    ? " · " + Math.round(Number(match.similarity) * 100) + "%"
                    : ""}
                </p>
                {match.listingCode && !match.intra ? (
                  <p className="text-brand-muted mt-0.5 truncate">
                    {"Mã tin: " + match.listingCode}
                  </p>
                ) : null}
                {match.listingUrl && !match.intra ? (
                  <RouterLink
                    to={match.listingUrl}
                    className="font-bold text-[var(--ui-accent)] mt-1 inline-block"
                  >
                    {"Xem tin liên quan"}
                  </RouterLink>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}
      {ctx.scan?.status === "FAILED" ? (
        <p className="text-[11px] text-brand-muted mt-3">
          {ctx.scan?.errorCode
            ? "Lỗi quét: " + ctx.scan.errorCode + ". Hệ thống sẽ thử lại khi bạn lưu hoặc gửi duyệt."
            : "Hệ thống sẽ thử lại khi bạn lưu hoặc gửi duyệt."}
        </p>
      ) : null}
      {ctx.scan?.limitations?.length ? (
        <p className="text-[10px] text-brand-muted mt-3 leading-relaxed">
          {ctx.scan.limitations[0]}
        </p>
      ) : null}
    </section>,
  ]);
});
