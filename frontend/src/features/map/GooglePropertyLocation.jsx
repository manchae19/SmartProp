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
  ref,
  computed,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
} from "../../shared/state/store.js";
import { loadGoogleMaps, googleMapId, hasGoogleMapsKey } from "./googleMaps.js";
import { coordinatesFromPlace } from "./googleMapsLocation.js";
import { validCoordinates } from "../property/postForm.js";
import ManualLocationMap from "./ManualLocationMap.jsx";
import AutomaticLocationSearch from "./AutomaticLocationSearch.jsx";
import { candidateCanBeConfirmed, accuracyLabel } from "./geocoding.js";
import { locationPreviewRegion } from "./locationPreview.js";
import "./GooglePropertyLocation.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    address: {
      default: "",
    },
    city: {
      default: "",
    },
    district: {
      default: "",
    },
    ward: {
      default: "",
    },
    latitude: {
      default: "",
    },
    longitude: {
      default: "",
    },
    confirmed: Boolean,
    disabled: Boolean,
  });
  const emit = emitForProps(__props, ["select", "confirm", "invalidate"]);
  const searchHost = ref(null),
    mapHost = ref(null),
    ready = ref(false),
    loading = ref(false),
    selecting = ref(false),
    message = ref(""),
    suggestion = ref("");
  const automaticSearch = ref(null),
    automaticCandidate = ref(null),
    verifiedExact = ref(false),
    publicExact = ref(false);
  const osmCandidate = computed(() =>
    automaticCandidate.value?.provider === "GEOAPIFY"
      ? automaticCandidate.value
      : null,
  );
  const previewRegion = computed(() =>
    locationPreviewRegion(osmCandidate.value),
  );
  function clearAutomatic() {
    automaticCandidate.value = null;
    verifiedExact.value = false;
    publicExact.value = false;
  }
  function previewAutomatic(candidate) {
    revision++;
    selecting.value = false;
    suggestion.value = "";
    automaticCandidate.value = candidate;
    verifiedExact.value = false;
    publicExact.value = false;
    emit("invalidate");
    if (candidate.provider === "GOOGLE") {
      if (!ready.value) {
        message.value =
          "Cần cấu hình bản đồ Google để xem gợi ý Google. Kết quả này không được hiển thị trên OSM hoặc lưu vào tin.";
        return;
      }
      marker.position = {
        lat: candidate.latitude,
        lng: candidate.longitude,
      };
      marker.map = map;
      map.setCenter(marker.position);
      map.setZoom(candidate.locationLevel === "APPROXIMATE" ? 14 : 18);
      message.value =
        "Gợi ý Google chỉ để tham khảo trên Google; không sao chép vào tin. Chọn ghim thủ công độc lập nếu bạn biết vị trí thực tế.";
    } else
      message.value = candidateCanBeConfirmed(candidate)
        ? "Gợi ý cấp tòa nhà. Chỉ xác nhận nếu bạn đã đối chiếu đúng bất động sản; chưa xác minh căn hộ hoặc ranh giới."
        : "Kết quả chỉ gần đúng hoặc chưa khớp số nhà. Bấm bản đồ để đặt lại ghim đúng bất động sản.";
  }
  const canConfirm = computed(
    () =>
      !props.disabled &&
      !!String(props.address).trim() &&
      publicExact.value &&
      (automaticCandidate.value
        ? candidateCanBeConfirmed(automaticCandidate.value) &&
          verifiedExact.value
        : selected.value),
  );
  async function confirmPoint() {
    if (!canConfirm.value) return;
    if (automaticCandidate.value) {
      const point = automaticCandidate.value;
      automaticCandidate.value = null;
      emit("select", {
        latitude: point.latitude,
        longitude: point.longitude,
      });
      await nextTick();
    }
    emit("confirm");
  }
  const selected = computed(() =>
    validCoordinates(props.latitude, props.longitude),
  );
  let map,
    marker,
    autocomplete,
    disposed = false,
    revision = 0;
  const cleanup = [];
  function updateMarker() {
    if (!map || !marker) return;
    if (!selected.value) {
      if (!suggestion.value) marker.map = null;
      return;
    }
    const p = {
      lat: Number(props.latitude),
      lng: Number(props.longitude),
    };
    marker.position = p;
    marker.map = map;
  }
  function movePin(latitude, longitude) {
    if (props.disabled) return;
    revision++;
    selecting.value = false;
    suggestion.value = "";
    clearAutomatic();
    automaticSearch.value?.clearSelection();
    emit("select", {
      latitude,
      longitude,
    });
    message.value =
      "Đã chọn ghim. Kiểm tra đúng địa chỉ và bấm Xác nhận vị trí.";
  }
  function unavailable() {
    if (disposed) return;
    ready.value = false;
    suggestion.value = "";
    if (marker) marker.map = null;
    message.value =
      "Bản đồ Google chưa sẵn sàng. Bạn có thể đặt ghim trên bản đồ thủ công bên dưới.";
  }
  async function initialize() {
    if (loading.value || disposed) return;
    if (!hasGoogleMapsKey() && !globalThis.google?.maps?.importLibrary) return;
    loading.value = true;
    message.value = "";
    try {
      const maps = await loadGoogleMaps();
      const [{ Map: GoogleMap }, { AdvancedMarkerElement }] = await Promise.all(
        [maps.importLibrary("maps"), maps.importLibrary("marker")],
      );
      if (disposed) return;
      ready.value = true;
      await nextTick();
      if (disposed) return;
      const center = selected.value
        ? {
            lat: Number(props.latitude),
            lng: Number(props.longitude),
          }
        : {
            lat: 16.0544,
            lng: 108.2022,
          };
      map = new GoogleMap(mapHost.value, {
        center,
        zoom: selected.value ? 17 : 13,
        mapId: googleMapId(),
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        gestureHandling: "cooperative",
      });
      marker = new AdvancedMarkerElement({
        gmpDraggable: true,
        title: "Kéo ghim đến bất động sản rồi xác nhận vị trí",
      });
      const dragged = () => {
        const p = marker.position;
        if (p)
          movePin(
            typeof p.lat === "function" ? p.lat() : p.lat,
            typeof p.lng === "function" ? p.lng() : p.lng,
          );
      };
      if (marker.addEventListener) {
        marker.addEventListener("gmp-dragend", dragged);
        cleanup.push(() => marker.removeEventListener("gmp-dragend", dragged));
      }
      if (marker.addListener) {
        const listener = marker.addListener("dragend", dragged);
        cleanup.push(() => listener.remove());
      }
      const listener = map.addListener("click", (event) => {
        if (event.latLng) movePin(event.latLng.lat(), event.latLng.lng());
      });
      cleanup.push(() => listener.remove());
      updateMarker();
      try {
        const { PlaceAutocompleteElement } = await maps.importLibrary("places");
        if (disposed) return;
        autocomplete = new PlaceAutocompleteElement({
          includedRegionCodes: ["vn"],
          locationBias: {
            center: {
              lat: 16.0544,
              lng: 108.2022,
            },
            radius: 30000,
          },
        });
        autocomplete.placeholder =
          "Tìm địa chỉ để đưa bản đồ đến gần bất động sản";
        autocomplete.setAttribute("aria-label", "Tìm địa chỉ trên Google Maps");
        searchHost.value.replaceChildren(autocomplete);
        autocomplete.addEventListener("input", () => {
          revision++;
          selecting.value = false;
        });
        autocomplete.addEventListener(
          "gmp-error",
          () =>
            (message.value =
              "Dịch vụ tìm địa chỉ gặp lỗi. Kiểm tra kết nối, thử lại hoặc đặt ghim trực tiếp trên bản đồ."),
        );
        autocomplete.addEventListener("gmp-select", async (event) => {
          if (props.disabled) return;
          clearAutomatic();
          automaticSearch.value?.clearSelection();
          const current = ++revision;
          selecting.value = true;
          suggestion.value = "";
          message.value = "";
          emit("invalidate");
          try {
            if (!event.placePrediction)
              throw Object.assign(Error(), {
                notFound: true,
              });
            const place = event.placePrediction.toPlace();
            await place.fetchFields({
              fields: ["formattedAddress", "location", "viewport", "types"],
            });
            if (disposed || current !== revision) return;
            let point;
            try {
              point = coordinatesFromPlace(place);
            } catch {
              throw Object.assign(Error(), {
                notFound: true,
              });
            }
            // Places content is transient: display it on Google only, never serialize it into the draft.
            suggestion.value = place.formattedAddress;
            marker.position = {
              lat: point.latitude,
              lng: point.longitude,
            };
            marker.map = map;
            if (place.viewport) map.fitBounds(place.viewport);
            else {
              map.setCenter(marker.position);
              map.setZoom(17);
            }
            const precise = (place.types || []).some((t) =>
              ["street_address", "premise", "subpremise"].includes(t),
            );
            message.value = precise
              ? "Đã tìm được gợi ý. Bấm bản đồ hoặc kéo ghim đến đúng bất động sản, rồi xác nhận."
              : "Kết quả chỉ xác định đường hoặc khu vực. Hãy chỉnh ghim đến đúng bất động sản trước khi xác nhận.";
          } catch (e) {
            if (!disposed && current === revision)
              message.value = e.notFound
                ? "Không tìm thấy vị trí phù hợp cho địa chỉ này. Thử gợi ý khác hoặc đặt ghim trực tiếp."
                : "Không kết nối được dịch vụ tìm địa chỉ. Hãy thử lại hoặc đặt ghim trực tiếp trên bản đồ.";
          } finally {
            if (!disposed && current === revision) selecting.value = false;
          }
        });
      } catch {
        message.value =
          "Gợi ý địa chỉ chưa sẵn sàng. Bạn vẫn có thể bấm bản đồ hoặc kéo ghim để chọn vị trí.";
      }
    } catch {
      unavailable();
    } finally {
      if (!disposed) loading.value = false;
    }
  }
  watch(() => [props.latitude, props.longitude], updateMarker);
  watch(
    () => [props.address, props.city, props.district, props.ward],
    () => {
      revision++;
      clearAutomatic();
      suggestion.value = "";
      message.value = "Địa chỉ đã thay đổi. Hãy chọn và xác nhận lại ghim.";
      if (marker && !selected.value) marker.map = null;
    },
  );
  onMounted(() => {
    globalThis.addEventListener(
      "smartprop:google-maps-unavailable",
      unavailable,
    );
    initialize();
  });
  onBeforeUnmount(() => {
    disposed = true;
    revision++;
    globalThis.removeEventListener(
      "smartprop:google-maps-unavailable",
      unavailable,
    );
    cleanup.forEach((fn) => fn());
    if (marker) marker.map = null;
    searchHost.value?.replaceChildren();
  });
  return {
    ref,
    computed,
    onMounted,
    onBeforeUnmount,
    watch,
    nextTick,
    loadGoogleMaps,
    googleMapId,
    hasGoogleMapsKey,
    coordinatesFromPlace,
    validCoordinates,
    ManualLocationMap,
    AutomaticLocationSearch,
    candidateCanBeConfirmed,
    accuracyLabel,
    locationPreviewRegion,
    props,
    emit,
    searchHost,
    mapHost,
    ready,
    loading,
    selecting,
    message,
    suggestion,
    automaticSearch,
    automaticCandidate,
    verifiedExact,
    publicExact,
    osmCandidate,
    previewRegion,
    clearAutomatic,
    previewAutomatic,
    canConfirm,
    confirmPoint,
    selected,
    map,
    marker,
    autocomplete,
    disposed,
    revision,
    cleanup,
    updateMarker,
    movePin,
    unavailable,
    initialize,
  };
}
export default React.forwardRef(function GooglePropertyLocation(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        id: "post-location",
        tabIndex: "-1",
        className: "location-picker",
        "data-sp-71e0825b": "",
      })}
    >
      <p
        {...mergeProps({
          className: "location-guide",
          "data-sp-71e0825b": "",
        })}
      >
        {
          "Chọn đúng vị trí bất động sản rồi xác nhận. Bạn không cần nhập kinh độ hoặc vĩ độ."
        }
      </p>
      <AutomaticLocationSearch
        {...mergeProps({
          ref: bindRef(ctx, "automaticSearch"),
          address: ctx.address,
          city: ctx.city,
          district: ctx.district,
          ward: ctx.ward,
          disabled: ctx.disabled,
          onPreview: ($event) => {
            return ctx.previewAutomatic?.($event);
          },
          onClear: ($event) => {
            return ctx.clearAutomatic?.($event);
          },
          "data-sp-71e0825b": "",
        })}
      />
      <div
        {...mergeProps(
          {
            ref: bindRef(ctx, "searchHost"),
            className: "google-search",
            inert: ctx.disabled || undefined,
            "data-sp-71e0825b": "",
          },
          {
            style: {
              display: ctx.ready && !ctx.osmCandidate ? undefined : "none",
            },
          },
        )}
      />
      {ctx.ready && ctx.suggestion ? (
        <p
          {...mergeProps({
            className: "location-guide",
            "data-sp-71e0825b": "",
          })}
        >
          {"Gợi ý trên Google: "}
          {display(ctx.suggestion)}
          {". Giữ địa chỉ tin đăng do bạn nhập ở trên."}
        </p>
      ) : null}
      {ctx.loading || ctx.selecting ? (
        <p
          {...mergeProps({
            role: "status",
            className: "location-guide",
            "data-sp-71e0825b": "",
          })}
        >
          {display(
            ctx.loading ? "Đang tải bản đồ…" : "Đang tìm vị trí địa chỉ…",
          )}
        </p>
      ) : null}
      <div
        {...mergeProps(
          {
            ref: bindRef(ctx, "mapHost"),
            className: "google-map",
            "aria-label": "Bản đồ Google chọn vị trí",
            "data-sp-71e0825b": "",
          },
          {
            style: {
              display: ctx.ready && !ctx.osmCandidate ? undefined : "none",
            },
          },
        )}
      />
      {(!ctx.ready && !ctx.loading) || ctx.osmCandidate ? (
        <React.Fragment {...mergeProps({})}>
          <p
            {...mergeProps({
              className: "location-guide",
              "data-sp-71e0825b": "",
            })}
          >
            {display(
              ctx.osmCandidate
                ? "Ghim đề xuất chưa được xác nhận. " +
                    ctx.accuracyLabel(ctx.osmCandidate)
                : "Đặt ghim thủ công trên bản đồ dưới đây khi bạn biết vị trí thực tế.",
            )}
          </p>
          <ManualLocationMap
            {...mergeProps({
              latitude: ctx.osmCandidate?.latitude ?? ctx.latitude,
              longitude: ctx.osmCandidate?.longitude ?? ctx.longitude,
              precision: ctx.osmCandidate?.context?.precision || "",
              preview: !!ctx.osmCandidate,
              previewRegion: ctx.previewRegion,
              disabled: ctx.disabled,
              onSelect: ($event) => {
                ctx.movePin($event.latitude, $event.longitude);
              },
              "data-sp-71e0825b": "",
            })}
          />
        </React.Fragment>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
            className: "location-message",
            "data-sp-71e0825b": "",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
      {ctx.selected && !ctx.automaticCandidate ? (
        <p
          {...mergeProps({
            className: "location-guide",
            "data-sp-71e0825b": "",
          })}
        >
          {
            "Ghim do người đăng chọn; chưa được xác minh độc lập. Xác nhận vị trí không phải chứng nhận độ chính xác."
          }
        </p>
      ) : null}
      {!ctx.selected && !ctx.suggestion ? (
        <p
          {...mergeProps({
            className: "location-guide",
            "data-sp-71e0825b": "",
          })}
        >
          {
            "Chưa chọn vị trí. Tâm bản đồ đang xem không được lưu thành vị trí của tin."
          }
        </p>
      ) : null}
      {ctx.automaticCandidate &&
      ctx.candidateCanBeConfirmed(ctx.automaticCandidate) ? (
        <label
          {...mergeProps({
            className: "location-consent",
            "data-sp-71e0825b": "",
          })}
        >
          <input
            {...mergeProps(
              {
                type: "checkbox",
                disabled: ctx.disabled,
                "data-sp-71e0825b": "",
              },
              modelProps(
                ctx.verifiedExact,
                ($value) => {
                  ctx.verifiedExact = $value;
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
          {
            "Tôi đã kiểm tra đây là đúng vị trí bất động sản, không chỉ là tâm đường hoặc khu vực."
          }
        </label>
      ) : null}
      <label
        {...mergeProps({
          className: "location-consent",
          "data-sp-71e0825b": "",
        })}
      >
        <input
          {...mergeProps(
            {
              type: "checkbox",
              disabled: ctx.disabled,
              "data-sp-71e0825b": "",
            },
            modelProps(
              ctx.publicExact,
              ($value) => {
                ctx.publicExact = $value;
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
        {
          "Tôi đồng ý công khai ghim và địa chỉ này. Nếu chỉ muốn hiển thị vị trí tương đối, chưa lưu tin bằng chế độ hiện tại."
        }
      </label>
      <div
        {...mergeProps({
          className: ["confirm-location", {
            confirmed: ctx.confirmed,
          }],
          
          "data-sp-71e0825b": "",
        })}
      >
        <div
          {...mergeProps({
            "data-sp-71e0825b": "",
          })}
        >
          <strong
            {...mergeProps({
              "data-sp-71e0825b": "",
            })}
          >
            {display(
              ctx.confirmed
                ? "Đã xác nhận vị trí"
                : ctx.selected
                  ? "Ghim đã chọn · cần xác nhận"
                  : "Chưa xác nhận vị trí",
            )}
          </strong>
          <p
            {...mergeProps({
              "data-sp-71e0825b": "",
            })}
          >
            {display(
              ctx.address || "Nhập địa chỉ đầy đủ trước khi xác nhận ghim.",
            )}
          </p>
        </div>
        <button
          {...mergeProps({
            type: "button",
            disabled: !ctx.canConfirm,
            onClick: ($event) => {
              return ctx.confirmPoint?.($event);
            },
            "data-sp-71e0825b": "",
          })}
        >
          {display(ctx.confirmed ? "Xác nhận lại" : "Xác nhận vị trí")}
        </button>
      </div>
    </div>,
  ]);
});
