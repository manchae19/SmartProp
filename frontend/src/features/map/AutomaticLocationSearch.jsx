import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import {
  computed,
  onMounted,
  onBeforeUnmount,
  ref,
  watch,
} from "../../shared/state/store.js";
import {
  accuracyLabel,
  geocodingSignature,
  geocodingConfiguration,
  normalizeAddressQuery,
  searchLocations,
  geocodingErrorMessage,
} from "./geocoding.js";
import "./AutomaticLocationSearch.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    address: String,
    city: String,
    district: String,
    ward: String,
    disabled: Boolean,
  });
  const emit = emitForProps(__props, ["preview", "clear"]);
  const busy = ref(false),
    consent = ref(false),
    error = ref(""),
    status = ref(""),
    candidates = ref([]),
    selected = ref("");
  const retryRemaining = ref(0);
  let retryTimer;
  function clearRetry() {
    clearInterval(retryTimer);
    retryRemaining.value = 0;
  }
  function waitBeforeRetry(seconds) {
    clearRetry();
    const until = Date.now() + Math.min(86400, Math.max(1, seconds)) * 1000;
    const tick = () => {
      retryRemaining.value = Math.max(
        0,
        Math.ceil((until - Date.now()) / 1000),
      );
      if (!retryRemaining.value) clearInterval(retryTimer);
    };
    tick();
    retryTimer = setInterval(tick, 1000);
  }
  let revision = 0,
    configRevision = 0;
  const configuration = ref(null),
    checking = ref(true),
    configurationError = ref("");
  const query = computed(() => normalizeAddressQuery(props));
  const searchScope = computed(() =>
    [
      props.city === "Da Nang" ? "Đà Nẵng" : props.city,
      props.district,
      props.ward,
    ]
      .filter(Boolean)
      .join(" · "),
  );
  const providerName = computed(() =>
    configuration.value?.provider === "GOOGLE" ? "Google Maps" : "Geoapify",
  );
  async function checkConfiguration() {
    const run = ++configRevision;
    checking.value = true;
    configurationError.value = "";
    try {
      const value = await geocodingConfiguration();
      if (run === configRevision) configuration.value = value;
    } catch {
      if (run === configRevision) {
        configuration.value = null;
        configurationError.value =
          "Chưa kiểm tra được dịch vụ tìm vị trí. Bạn vẫn có thể đặt ghim thủ công.";
      }
    } finally {
      if (run === configRevision) checking.value = false;
    }
  }
  const signature = computed(() => geocodingSignature(props));
  const canSearch = computed(
    () =>
      !props.disabled &&
      !checking.value &&
      configuration.value?.available === true &&
      !busy.value &&
      retryRemaining.value === 0 &&
      consent.value &&
      !!props.address?.trim() &&
      !!props.city?.trim(),
  );
  async function search() {
    if (!canSearch.value) return;
    const current = ++revision;
    busy.value = true;
    error.value = "";
    status.value = "";
    candidates.value = [];
    selected.value = "";
    emit("clear");
    try {
      const result = await searchLocations({
        ...props,
        shareAddress: consent.value,
      });
      if (current !== revision) return;
      candidates.value = result.candidates;
      status.value = result.candidates.length
        ? "Chọn một kết quả trong khu vực đã chọn để xem ghim đề xuất; chưa lưu hoặc xác nhận vị trí."
        : "Không tìm thấy địa điểm phù hợp trong khu vực đã chọn. Bạn có thể điều chỉnh địa chỉ hoặc chọn ghim thủ công." +
          (result.status === "SCOPE_UNAVAILABLE"
            ? " Chưa có ranh giới đã kiểm chứng cho lựa chọn này; hệ thống không tự mở rộng phạm vi."
            : "");
      if (result.candidates.length === 1) {
        preview(result.candidates[0]);
        status.value =
          "Đã đưa bản đồ đến gợi ý duy nhất. Kiểm tra vị trí và độ chính xác trước khi xác nhận.";
      }
    } catch (e) {
      if (current === revision) {
        error.value = geocodingErrorMessage(e);
        if (e.status === 429) waitBeforeRetry(e.retryAfter || 2);
      }
    } finally {
      if (current === revision) busy.value = false;
    }
  }
  function preview(candidate) {
    selected.value = candidate.id;
    emit("preview", candidate);
  }
  function clearSelection() {
    selected.value = "";
  }
  exposeForSetup({
    clearSelection,
  });
  watch(signature, () => {
    revision++;
    clearRetry();
    busy.value = false;
    consent.value = false;
    candidates.value = [];
    selected.value = "";
    error.value = "";
    status.value = "";
    emit("clear");
  });
  onMounted(checkConfiguration);
  onBeforeUnmount(() => {
    revision++;
    configRevision++;
    clearRetry();
  });
  return {
    computed,
    onMounted,
    onBeforeUnmount,
    ref,
    watch,
    accuracyLabel,
    geocodingSignature,
    geocodingConfiguration,
    normalizeAddressQuery,
    searchLocations,
    geocodingErrorMessage,
    props,
    emit,
    busy,
    consent,
    error,
    status,
    candidates,
    selected,
    retryRemaining,
    retryTimer,
    clearRetry,
    waitBeforeRetry,
    revision,
    configRevision,
    configuration,
    checking,
    configurationError,
    query,
    searchScope,
    providerName,
    checkConfiguration,
    signature,
    canSearch,
    search,
    preview,
    clearSelection,
  };
}
export default React.forwardRef(function AutomaticLocationSearch(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "automatic-location",
        "aria-busy": ctx.busy,
        "data-sp-b9243b48": "",
      })}
    >
      <div
        {...mergeProps({
          className: "search-heading",
          "data-sp-b9243b48": "",
        })}
      >
        <div
          {...mergeProps({
            "data-sp-b9243b48": "",
          })}
        >
          <strong
            {...mergeProps({
              "data-sp-b9243b48": "",
            })}
          >
            {"Tìm vị trí từ địa chỉ"}
          </strong>
          <p
            {...mergeProps({
              "data-sp-b9243b48": "",
            })}
          >
            {
              "Giữ nguyên địa chỉ bạn nhập; kết quả tìm kiếm chỉ là đề xuất cần kiểm tra."
            }
          </p>
        </div>
        <button
          {...mergeProps({
            type: "button",
            disabled: !ctx.canSearch,
            onClick: ($event) => {
              return ctx.search?.($event);
            },
            "data-sp-b9243b48": "",
          })}
        >
          {display(ctx.busy ? "Đang tìm…" : "Tìm vị trí tự động")}
        </button>
      </div>
      {ctx.checking ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-b9243b48": "",
          })}
        >
          {"Đang kiểm tra dịch vụ tìm vị trí…"}
        </p>
      ) : ctx.configurationError || !ctx.configuration?.available ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-b9243b48": "",
          })}
        >
          {display(
            ctx.configurationError ||
              "Tìm vị trí tự động hiện chưa được bật trên hệ thống. Bạn vẫn có thể đặt ghim thủ công.",
          )}{" "}
          <button
            {...mergeProps({
              type: "button",
              className: "check-service",
              disabled: ctx.disabled,
              onClick: ($event) => {
                return ctx.checkConfiguration?.($event);
              },
              "data-sp-b9243b48": "",
            })}
          >
            {"Kiểm tra lại"}
          </button>
        </p>
      ) : (
        <label
          {...mergeProps({
            className: "search-consent",
            "data-sp-b9243b48": "",
          })}
        >
          <input
            {...mergeProps(
              {
                type: "checkbox",
                disabled: ctx.disabled || ctx.busy,
                "data-sp-b9243b48": "",
              },
              modelProps(
                ctx.consent,
                ($value) => {
                  ctx.consent = $value;
                },
                {
                  kind: "checkbox",
                  value: "on",
                  number: false,
                  multiple: false,
                },
              ),
            )}
          />
          {"Tôi đồng ý gửi địa chỉ này tới "}
          {display(ctx.providerName)}
          {" để tìm vị trí."}
        </label>
      )}
      {ctx.configuration?.available && ctx.address?.trim() ? (
        <p
          {...mergeProps({
            className: "search-query",
            "data-sp-b9243b48": "",
          })}
        >
          {"Địa chỉ dùng để tìm: "}
          {display(ctx.query)}
        </p>
      ) : null}
      {ctx.configuration?.available ? (
        <p
          {...mergeProps({
            className: "search-scope",
            "data-sp-b9243b48": "",
          })}
        >
          {"Giới hạn tìm kiếm: "}
          {display(ctx.searchScope)}
          {". Kết quả ngoài phạm vi sẽ không được hiển thị."}
        </p>
      ) : null}
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-b9243b48": "",
          })}
        >
          {"Đang tìm các vị trí phù hợp…"}
        </p>
      ) : null}
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "search-error",
            "data-sp-b9243b48": "",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.error ? (
        <button
          {...mergeProps({
            type: "button",
            disabled: !ctx.canSearch,
            onClick: ($event) => {
              return ctx.search?.($event);
            },
            "data-sp-b9243b48": "",
          })}
        >
          {display(
            ctx.retryRemaining
              ? "Thử lại sau " + ctx.retryRemaining + " giây"
              : "Thử lại tìm vị trí",
          )}
        </button>
      ) : null}
      {ctx.status ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-b9243b48": "",
          })}
        >
          {display(ctx.status)}
        </p>
      ) : null}
      {ctx.candidates.length ? (
        <fieldset
          {...mergeProps({
            className: "search-results",
            "data-sp-b9243b48": "",
          })}
        >
          <legend
            {...mergeProps({
              "data-sp-b9243b48": "",
            })}
          >
            {"Các vị trí đề xuất"}
          </legend>
          {renderList(ctx.candidates, (candidate) => (
            <label
              key={candidate.id}
              {...mergeProps({
                className: ["search-result", {
                  chosen: ctx.selected === candidate.id,
                }],
                
                "data-sp-b9243b48": "",
              })}
            >
              <input
                {...mergeProps({
                  type: "radio",
                  name: "geocoding-result",
                  checked: ctx.selected === candidate.id,
                  disabled: ctx.disabled,
                  onChange: ($event) => {
                    ctx.preview(candidate);
                  },
                  "data-sp-b9243b48": "",
                })}
              />
              <span
                {...mergeProps({
                  "data-sp-b9243b48": "",
                })}
              >
                <strong
                  {...mergeProps({
                    "data-sp-b9243b48": "",
                  })}
                >
                  {display(candidate.formattedAddress)}
                </strong>
                <small
                  {...mergeProps({
                    "data-sp-b9243b48": "",
                  })}
                >
                  {display(ctx.accuracyLabel(candidate))}
                </small>
                <small
                  {...mergeProps({
                    "data-sp-b9243b48": "",
                  })}
                >
                  {display(candidate.attribution)}
                </small>
              </span>
            </label>
          ))}
        </fieldset>
      ) : null}
      {ctx.candidates.some((candidate) => candidate.provider === "GEOAPIFY") ? (
        <p
          {...mergeProps({
            className: "source-links",
            "data-sp-b9243b48": "",
          })}
        >
          <a
            {...mergeProps({
              href: "https://www.geoapify.com/",
              target: "_blank",
              rel: "noopener noreferrer",
              "data-sp-b9243b48": "",
            })}
          >
            {"Powered by Geoapify"}
          </a>
          {" · "}
          <a
            {...mergeProps({
              href: "https://www.openstreetmap.org/copyright",
              target: "_blank",
              rel: "noopener noreferrer",
              "data-sp-b9243b48": "",
            })}
          >
            {"© OpenStreetMap contributors"}
          </a>
        </p>
      ) : null}
      {ctx.candidates.some((candidate) => candidate.provider === "GOOGLE") ? (
        <p
          {...mergeProps({
            className: "source-links",
            "data-sp-b9243b48": "",
          })}
        >
          {
            "Google Maps · Gợi ý chỉ hiển thị trên Google; không sao chép vào bản nháp hoặc bản đồ OSM."
          }
        </p>
      ) : null}
    </div>,
  ]);
});
