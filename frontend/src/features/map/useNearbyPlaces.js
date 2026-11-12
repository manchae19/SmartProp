import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { requestNearby } from './nearbyRequest.js';
import { nearbyPath } from './nearbyExplorer.js';
export function useNearbyPlaces(getProperty, getRadius, getGroups, enabled = () => true) {
  const [data] = useState(() => createStateStore(null)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore('')),
    [retryAt] = useState(() => createStateStore(0));
  useSyncExternalStore(retryAt.subscribe, retryAt.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(data.subscribe, data.getSnapshot);
  const _sequenceRef = useRef(0),
    _timerRef = useRef(undefined),
    _controllerRef = useRef(undefined);
  async function load() {
    const run = ++_sequenceRef.current;
    clearTimeout(_timerRef.current);
    _controllerRef.current?.abort();
    _controllerRef.current = new AbortController();
    data.set(null);
    error.set('');
    busy.set(false);
    const path = enabled() && nearbyPath(getProperty()?.id, getRadius(), getGroups());
    if (!path) return;
    if (Date.now() < retryAt.getSnapshot()) {
      error.set('Vui lòng chờ một lát trước khi thử lại.');
      return;
    }
    busy.set(true);
    try {
      const result = await requestNearby(path, {
        base: import.meta.env?.VITE_API_BASE_URL || '/api/v1',
        signal: _controllerRef.current.signal
      });
      if (run === _sequenceRef.current && result.propertyId === getProperty()?.id) data.set(result);
    } catch (e) {
      if (run !== _sequenceRef.current || e.name === 'AbortError') return;
      error.set({
        NEARBY_TIMEOUT: 'Tìm tiện ích quá thời gian. Bạn có thể thử lại.',
        NEARBY_NOT_CONFIGURED: 'Nguồn tiện ích chưa được cấu hình trên máy chủ.',
        NEARBY_QUOTA_EXCEEDED: 'Nguồn tiện ích đang giới hạn truy cập. Vui lòng thử lại sau.',
        NEARBY_PROVIDER_AUTH: 'Máy chủ chưa có quyền truy cập nguồn tiện ích.',
        RATE_LIMITED: 'Bạn đang thao tác quá nhanh. Vui lòng chờ rồi thử lại.'
      }[e.code] || (e.status === 404 ? 'Tin đăng không còn công khai.' : 'Chưa tải được tiện ích. Vui lòng thử lại.'));
      if (e.status === 429) retryAt.set(Date.now() + Math.min(3600, Math.max(1, e.retryAfter || 10)) * 1000);
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  const _watched = (() => [getProperty()?.id, getProperty()?.latitude, getProperty()?.longitude, getRadius(), [...getGroups()].sort().join(','), enabled()])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (() => {
      ++_sequenceRef.current;
      _controllerRef.current?.abort();
      clearTimeout(_timerRef.current);
      data.set(null);
      error.set('');
      busy.set(false);
      _timerRef.current = setTimeout(load, 650);
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    ++_sequenceRef.current;
    clearTimeout(_timerRef.current);
    _controllerRef.current?.abort();
  })(), []);
  return {
    data: data.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    retry: load,
    updateData: data.edit,
    updateDataValue: data.set,
    updateBusy: busy.edit,
    updateBusyValue: busy.set,
    updateError: error.edit,
    updateErrorValue: error.set
  };
}
