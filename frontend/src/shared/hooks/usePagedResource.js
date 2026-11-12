import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createPagedResource } from './pagedResource.js';
export function usePagedResource(request, endpoint, filters = () => ({}), summaryEndpoint = null, {
  size = 20,
  delay = 180,
  loadingDuringDelay = false
} = {}) {
  const latest = useRef({
    request,
    filters,
    endpoint
  });
  latest.current = {
    request,
    filters,
    endpoint
  };
  const [resource] = useState(() => createPagedResource((...args) => latest.current.request(...args), endpoint, () => latest.current.filters(), summaryEndpoint, {
    size
  }));
  const data = useSyncExternalStore(resource.subscribe, resource.getSnapshot);
  const key = JSON.stringify(filters());
  const initial = useRef(true);
  useEffect(() => {
    if (initial.current) {
      initial.current = false;
      return;
    }
    resource.getSnapshot().invalidate();
    if(loadingDuringDelay)resource.edit(state=>{state.error="";state.busy=true});
    const timer = setTimeout(() => resource.getSnapshot().load(0), delay);
    return () => clearTimeout(timer);
  }, [key, delay, loadingDuringDelay, resource]);
  useEffect(() => {
    resource.getSnapshot().reload();
    return () => resource.getSnapshot().dispose();
  }, [resource]);
  return {
    ...data,
    updateState: resource.edit
  };
}
