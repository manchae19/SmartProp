import {useRef,useState,useEffect,useSyncExternalStore} from "react";
import {createStateStore} from "../state/createStateStore.js";
import {api,errorText} from "../../features/auth/api.js";
import {query} from "../../features/property/property.js";
export function useList(endpoint, filters = () => ({})) {
  const _sequenceRef = useRef(0);
  const [s] = useState(() => createStateStore({
    items: [],
    busy: false,
    error: "",
    notice: "",
    page: 0,
    totalElements: 0,
    totalPages: 0,
    async load(page = 0) {
      const run = ++_sequenceRef.current;
      s.edit(draftValue => draftValue["busy"] = true);
      s.edit(draftValue => draftValue["error"] = "");
      try {
        const result = await api((typeof endpoint === "function" ? endpoint() : endpoint) + "?" + query({
          ...filters(),
          page,
          size: 20
        }));
        if (run === _sequenceRef.current) s.edit(draftValue => Object.assign(draftValue, {
          items: result.items || [],
          page: result.page,
          totalElements: result.totalElements,
          totalPages: result.totalPages
        }));
      } catch (e) {
        if (run === _sequenceRef.current) s.edit(draftValue => draftValue["error"] = errorText(e));
      } finally {
        if (run === _sequenceRef.current) s.edit(draftValue => draftValue["busy"] = false);
      }
    },
    async run(fn) {
      if (s.getSnapshot().busy) return;
      s.edit(draftValue => draftValue["busy"] = true);
      s.edit(draftValue => draftValue["error"] = "");
      try {
        return await fn();
      } catch (e) {
        s.edit(draftValue => draftValue["error"] = errorText(e));
        return null;
      } finally {
        s.edit(draftValue => draftValue["busy"] = false);
      }
    }
  }));
  useSyncExternalStore(s.subscribe, s.getSnapshot);
  useEffect(() => {
    const result = (() => s.getSnapshot().load())();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...s.getSnapshot(),
    updateState: s.edit
  };
}
