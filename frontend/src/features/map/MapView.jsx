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
  watch,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { api } from "../auth/api.js";
import {
  usePublicListings,
  isPublicProperty,
} from "../property/usePublicListings.js";
import { useListingFilters } from "../property/useListingFilters.js";
import PropertyExplorer from "./PropertyExplorer.jsx";
import ListingFilters from "../property/ListingFilters.jsx";
import { LegacyState, LegacyPager } from "../../shared/lib/legacy.js";
import "./MapView.css";
function setup(__props) {
  const route = useRoute(),
    router = useRouter(),
    search = useListingFilters();
  const state = usePublicListings(() => search.filters.value, {
    endpoint: "/properties/map",
  });
  const selectedId = ref(null),
    requested = ref(null),
    selectionError = ref("");
  let sequence = 0;
  const mapItems = computed(() =>
    requested.value && !state.items.some((p) => p.id === requested.value.id)
      ? [...state.items, requested.value]
      : state.items,
  );
  async function loadRequested(id) {
    const run = ++sequence;
    selectionError.value = "";
    requested.value = null;
    selectedId.value = id ? String(id) : null;
    if (!id) {
      selectedId.value = state.items[0]?.id || null;
      return;
    }
    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        String(id),
      )
    ) {
      selectionError.value = "Mã tin trên bản đồ không hợp lệ.";
      return;
    }
    try {
      const p = await api("/properties/" + encodeURIComponent(id), {
        authenticated: false,
      });
      if (run !== sequence) return;
      if (!isPublicProperty(p)) throw Error();
      requested.value = p;
    } catch {
      if (run === sequence)
        selectionError.value =
          "Không tìm thấy tin công khai đang chọn; không thay bằng vị trí của tin khác.";
    }
  }
  watch(() => route.query.propertyId, loadRequested, {
    immediate: true,
  });
  watch(
    () => state.items,
    (items) => {
      if (
        !route.query.propertyId &&
        !items.some((p) => p.id === selectedId.value)
      )
        selectedId.value = items[0]?.id || null;
    },
  );
  function select(id) {
    router.replace({
      query: {
        ...route.query,
        propertyId: id,
      },
    });
  }
  onBeforeUnmount(() => sequence++);
  return {
    ref,
    computed,
    watch,
    onBeforeUnmount,
    useRoute,
    useRouter,
    api,
    usePublicListings,
    isPublicProperty,
    useListingFilters,
    PropertyExplorer,
    ListingFilters,
    LegacyState,
    LegacyPager,
    route,
    router,
    search,
    state,
    selectedId,
    requested,
    selectionError,
    sequence,
    mapItems,
    loadRequested,
    select,
  };
}
export default React.forwardRef(function MapView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="MapView"
      {...mergeProps({
        className: "map-v3",
        "data-sp-2646eeb9": "",
      })}
    >
      <div
        {...mergeProps({
          className: "map-page-width",
          "data-sp-2646eeb9": "",
        })}
      >
        <div
          {...mergeProps({
            className: "map-heading page-intro-banner",
            "data-sp-2646eeb9": "",
          })}
        >
          <p
            {...mergeProps({
              "data-sp-2646eeb9": "",
            })}
          >
            {"GIS EXPLORER"}
          </p>
          <h1
            {...mergeProps({
              "data-sp-2646eeb9": "",
            })}
          >
            {"Bản đồ bất động sản"}
          </h1>

        </div>
        <details
          {...mergeProps({
            className: "map-search-panel",
            "data-sp-2646eeb9": "",
          })}
        >
          <summary
            {...mergeProps({
              "data-sp-2646eeb9": "",
            })}
          >
            {"Bộ lọc tìm kiếm bất động sản"}
          </summary>
          <ListingFilters
            {...mergeProps({
              modelValue: ctx.search.filters.value,
              onUpdateModelValue: ($event) => {
                return ctx.search.set?.($event);
              },
              "data-sp-2646eeb9": "",
            })}
          />
        </details>
        <LegacyState
          {...mergeProps({
            state: ctx.state,
            "data-sp-2646eeb9": "",
          })}
        />
        {ctx.selectionError ? (
          <p
            {...mergeProps({
              role: "alert",
              className: "selection-error",
              "data-sp-2646eeb9": "",
            })}
          >
            {display(ctx.selectionError)}
          </p>
        ) : null}
        {ctx.requested &&
        !ctx.state.items.some((p) => p.id === ctx.requested.id) ? (
          <p
            {...mergeProps({
              className: "selection-info",
              "data-sp-2646eeb9": "",
            })}
          >
            {
              "Tin đang xem có thể nằm ngoài bộ lọc hiện tại."
            }
          </p>
        ) : null}
        <PropertyExplorer
          {...mergeProps({
            selectedId: ctx.selectedId,
            items: ctx.mapItems,
            onSelect: ($event) => {
              return ctx.select?.($event);
            },
            "data-sp-2646eeb9": "",
          })}
        />
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
            "data-sp-2646eeb9": "",
          })}
        />
      </div>
    </div>,
  ]);
});
