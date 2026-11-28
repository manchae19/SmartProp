import { afterPaint } from "../../shared/lib/ui.js";
import { createStateStore, stateKey, combineStateStores } from "../../shared/state/createStateStore.js";
import { useRef, useEffect, useSyncExternalStore } from "react";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api, session, errorText } from '../auth/api.js';
import { validateFiles } from './property.js';
import { postSteps, typeCodes, validatePost, fieldIssue, isPublisher, addressSignature, locationSignature, validCoordinates, buildPostPayload, payloadFromManaged, samePayload } from './postForm.js';
import { ADVANCED_DRAFT_DEFAULTS } from '../prediction/advancedValuation.js';
// Exported so a test can assert that every advanced valuation field is listed here;
// reset() relies on Object.assign, which only overwrites keys that already exist.
export const initialDraft = () => ({
  transactionType: 'Bán',
  rentUnit: 'PER_MONTH',
  propertyType: 'Nhà phố',
  district: '',
  city: 'Da Nang',
  ward: '',
  valuationLocation: '',
  title: '',
  area: '',
  price: '',
  bedrooms: '',
  bathrooms: '',
  address: '',
  latitude: '',
  longitude: '',
  confirmedLocation: '',
  description: '',
  contactName: '',
  phone: '',
  contact: '',
  floor: '',
  block: '',
  direction: '',
  selectedAmenities: [],
  // Advanced valuation-only fields; the defaults live with the valuation logic so a
  // property switch clears them instead of carrying the previous listing's values.
  ...ADVANCED_DRAFT_DEFAULTS,
  accepted: false
});
const cleanState = () => ({
  busy: false,
  error: '',
  notice: '',
  issues: [],
  loaded: false,
  loadError: false,
  conflict: false,
  complete: false,
  localSaved: false,
  localSaveError: false,
  lostFiles: 0,
  savedAt: null,
  uncertainCreate: null,
  uncertainUpload: null
});
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const uncertain = e => !e.status || e.status >= 500 || e.status === 408;
function restoredDraft(value) {
  const restored = initialDraft();
  if (!value || typeof value !== 'object') return restored;
  for (const name of Object.keys(restored)) {
    const item = value[name];
    if (name === 'accepted') restored[name] = item === true;else if (name === 'selectedAmenities') restored[name] = Array.isArray(item) ? item.filter(v => typeof v === 'string') : [];else if (typeof item === 'string' || typeof item === 'number') restored[name] = String(item);
  }
  return restored;
}

// One editor for the existing posting routes. Injected dependencies also allow mock-only verification.
export function createPostEditor({
  request = api,
  getActor = () => session.getSnapshot().user,
  getStorage = () => globalThis.sessionStorage,
  urls = globalThis.URL,
  clock = () => Date.now()
} = {}) {
  const draft = createStateStore(initialDraft()),
    state = createStateStore(cleanState()),
    managed = createStateStore(null),
    images = createStateStore([]),
    coverKey = createStateStore(''),
    removed = createStateStore([]);
  let actor = '',
    slot = '',
    key = '',
    epoch = 0,
    hydrating = false,
    serial = 0;
  const getImageCount = () => images.getSnapshot().length;
  const getDirty = () => !!managed.getSnapshot() && (!samePayload(buildPostPayload(draft.getSnapshot()), payloadFromManaged(managed.getSnapshot())) || removed.getSnapshot().length > 0 || images.getSnapshot().some(e => !e.server) || JSON.stringify(images.getSnapshot().map(e => e.server?.id)) !== JSON.stringify(managed.getSnapshot().property.images.map(e => e.id)) || images.getSnapshot().find(e => e.key === coverKey.getSnapshot())?.server?.id !== managed.getSnapshot().property.images.find(e => e.cover)?.id);
  function permitted() {
    return isPublisher(getActor()) && String(getActor().id) === actor;
  }
  function assertRun(run) {
    if (run !== epoch || !permitted()) throw Object.assign(Error('Phiên đăng tin đã thay đổi.'), {
      stale: true
    });
  }
  function checkItem(value) {
    if (!value?.property || !uuid.test(value.property.id) || String(value.ownerId) !== actor) throw Error('Không thể sử dụng tin không thuộc tài khoản hiện tại.');
    return value;
  }
  async function call(run, p, o) {
    assertRun(run);
    const result = await request(p, o);
    assertRun(run);
    return result;
  }
  function release(entry) {
    if (entry.preview) {
      urls?.revokeObjectURL?.(entry.preview);
      entry.preview = '';
    }
  }
  function clearMemory() {
    images.getSnapshot().forEach(release);
    images.set([]);
    managed.set(null);
    coverKey.set('');
    removed.set([]);
    hydrating = true;
    draft.edit(draftValue => Object.assign(draftValue, initialDraft()));
    hydrating = false;
    state.edit(draftValue => Object.assign(draftValue, cleanState()));
  }
  function bindActor() {
    const next = isPublisher(getActor()) ? String(getActor().id) : '';
    if (next !== actor) {
      epoch++;
      key = '';
      slot = '';
      actor = next;
      clearMemory();
    }
  }
  function persist() {
    if (hydrating || !key || !permitted() || !state.getSnapshot().loaded) return;
    try {
      getStorage()?.setItem(key, JSON.stringify({
        actor,
        draft: {
          ...draft.getSnapshot()
        },
        managed: managed.getSnapshot(),
        order: images.getSnapshot().filter(e => e.server).map(e => e.server.id),
        coverId: images.getSnapshot().find(e => e.key === coverKey.getSnapshot())?.server?.id,
        removed: removed.getSnapshot(),
        pendingFileCount: images.getSnapshot().filter(e => !e.server).length + state.getSnapshot().lostFiles,
        uncertainCreate: state.getSnapshot().uncertainCreate,
        uncertainUpload: state.getSnapshot().uncertainUpload,
        savedAt: state.getSnapshot().savedAt,
        complete: state.getSnapshot().complete
      }));
      state.edit(draftValue => draftValue["localSaved"] = !!getStorage());
      state.edit(draftValue => draftValue["localSaveError"] = false);
    } catch {
      state.edit(draftValue => draftValue["localSaved"] = false);
      state.edit(draftValue => draftValue["localSaveError"] = true);
    }
  }
  function setManaged(value) {
    managed.set(checkItem(value));
    const byId = new Map(value.property.images.map(i => [i.id, i]));
    for (const entry of images.getSnapshot()) if (entry.server && byId.has(entry.server.id)) entry.server = byId.get(entry.server.id);
    persist();
  }
  function fill(value) {
    const p = value.property;
    hydrating = true;
    draft.edit(draftValue => Object.assign(draftValue, initialDraft(), {
      transactionType: p.transactionType === 'SALE' ? 'Bán' : 'Cho thuê',
      rentUnit: p.transactionType === 'RENT' ? p.priceUnit : 'PER_MONTH',
      propertyType: Object.keys(typeCodes).find(k => typeCodes[k] === p.propertyType) || '',
      title: p.title,
      price: String(p.priceExact ?? p.price),
      area: String(p.areaSqmExact ?? p.areaSqm),
      bedrooms: p.bedrooms ?? '',
      bathrooms: p.bathrooms ?? '',
      address: p.address || '',
      city: p.city || 'Da Nang',
      district: p.district || '',
      ward: p.ward || '',
      latitude: p.latitude,
      longitude: p.longitude,
      description: p.description || '',
      contactName: value.contactName || '',
      phone: value.contactPhone || '',
      contact: value.contactEmail || '',
      floor: p.floor || '',
      block: p.block || '',
      direction: p.direction || '',
      selectedAmenities: p.declaredAmenities || []
    }));
    draft.edit(draftValue => draftValue["confirmedLocation"] = validCoordinates(p.latitude, p.longitude) ? locationSignature(draft.getSnapshot()) : '');
    hydrating = false;
  }
  function serverImages(value) {
    images.getSnapshot().forEach(release);
    images.set(value.property.images.map(i => ({
      key: i.id,
      server: i
    })));
    coverKey.set(images.getSnapshot().find(e => e.server.cover)?.key || images.getSnapshot()[0]?.key || '');
    removed.set([]);
  }
  async function initialize(editId) {
    bindActor();
    if (!permitted()) return;
    const next = editId ? String(editId) : 'new';
    if (next !== 'new' && !uuid.test(next)) {
      state.edit(draftValue => draftValue["loadError"] = true);
      state.edit(draftValue => draftValue["error"] = 'Mã tin không hợp lệ.');
      return;
    }
    if (state.getSnapshot().loaded && (slot === next || managed.getSnapshot()?.property.id === next)) {
      if (slot !== next) {
        const oldKey = key;
        slot = next;
        key = 'smartprop:posting:v2:' + actor + ':' + slot;
        persist();
        try {
          getStorage()?.removeItem(oldKey);
        } catch {}
      }
      return;
    }
    persist();
    epoch++;
    const run = epoch;
    clearMemory();
    slot = next;
    key = 'smartprop:posting:v2:' + actor + ':' + slot;
    hydrating = true;
    draft.edit(draftValue => draftValue["contactName"] = getActor().fullName || '');
    draft.edit(draftValue => draftValue["phone"] = getActor().phone || '');
    draft.edit(draftValue => draftValue["contact"] = getActor().email || '');
    hydrating = false;
    let saved;
    try {
      saved = JSON.parse(getStorage()?.getItem(key) || 'null');
    } catch {}
    if (saved && String(saved.actor) === actor) {
      hydrating = true;
      draft.edit(draftValue => Object.assign(draftValue, restoredDraft(saved.draft)));
      hydrating = false;
      if (saved.managed && String(saved.managed.ownerId) === actor && uuid.test(saved.managed.property?.id || '') && Array.isArray(saved.managed.property.images)) managed.set(saved.managed);
      state.edit(draftValue => draftValue["uncertainCreate"] = saved.uncertainCreate || null);
      state.edit(draftValue => draftValue["uncertainUpload"] = saved.uncertainUpload || null);
      state.edit(draftValue => draftValue["lostFiles"] = Number(saved.pendingFileCount) || 0);
      state.edit(draftValue => draftValue["savedAt"] = saved.savedAt || null);
      state.edit(draftValue => draftValue["complete"] = !!saved.complete);
    }
    state.edit(draftValue => draftValue["busy"] = true);
    try {
      const id = next === 'new' ? managed.getSnapshot()?.property.id : next;
      if (id) {
        const fresh = checkItem(await call(run, '/users/me/properties/' + id));
        const previous = managed.getSnapshot();
        managed.set(fresh);
        if (!saved || !previous) {
          fill(fresh);
          serverImages(fresh);
          state.edit(draftValue => draftValue["complete"] = false);
        } else {
          serverImages(fresh);
          const byId = new Map(images.getSnapshot().map(e => [e.server.id, e]));
          removed.set((Array.isArray(saved.removed) ? saved.removed : []).filter(id => byId.has(id)));
          images.set((Array.isArray(saved.order) ? saved.order : []).filter(id => byId.has(id) && !removed.getSnapshot().includes(id)).map(id => byId.get(id)));
          for (const [id, e] of byId) if (!images.getSnapshot().includes(e) && !removed.getSnapshot().includes(id)) images.edit(draftValue => draftValue.push(e));
          coverKey.set(images.getSnapshot().find(e => e.server.id === saved.coverId)?.key || images.getSnapshot().find(e => e.server.cover)?.key || images.getSnapshot()[0]?.key || '');
          if (previous.property.contentVersion !== fresh.property.contentVersion) {
            state.edit(draftValue => draftValue["conflict"] = true);
            state.edit(draftValue => draftValue["error"] = 'Tin trên máy chủ đã thay đổi. Nội dung bạn nhập được giữ; hãy đối chiếu phiên bản mới trước khi lưu.');
          }
          if (!['PENDING', 'PUBLISHED'].includes(fresh.property.status)) state.edit(draftValue => draftValue["complete"] = false);
        }
      }
      assertRun(run);
      state.edit(draftValue => draftValue["loaded"] = true);
      if (state.getSnapshot().lostFiles) state.edit(draftValue => draftValue["notice"] = 'Đã khôi phục nội dung trên trình duyệt; ' + state.getSnapshot().lostFiles + ' ảnh chưa tải cần chọn lại.');
      persist();
    } catch (e) {
      if (!e.stale) {
        state.edit(draftValue => draftValue["loadError"] = true);
        state.edit(draftValue => draftValue["error"] = errorText(e));
      }
    } finally {
      if (run === epoch) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  (() => {
    let _previousValue = (() => addressSignature(draft.getSnapshot()))();
    const _onChange = () => {
      const _nextValue = (() => addressSignature(draft.getSnapshot()))();
      if (stateKey(_nextValue) === stateKey(_previousValue)) return;
      const previousValue = _previousValue;
      _previousValue = _nextValue;
      (() => {
        if (hydrating) return;
        draft.edit(draftValue => draftValue["latitude"] = '');
        draft.edit(draftValue => draftValue["longitude"] = '');
        draft.edit(draftValue => draftValue["confirmedLocation"] = '');
        persist();
      })(_nextValue, previousValue, () => undefined);
    };
    draft.subscribe(_onChange);
  })();
  (() => {
    let _previousValue2 = draft.getSnapshot();
    const _onChange2 = () => {
      const _nextValue2 = draft.getSnapshot();
      if (stateKey(_nextValue2) === stateKey(_previousValue2)) return;
      const previousValue = _previousValue2;
      _previousValue2 = _nextValue2;
      (() => {
        if (!hydrating) {
          persist();
          if (state.getSnapshot().issues.length) {
            const fields = new Set(state.getSnapshot().issues.map(i => i.field));
            state.edit(draftValue => draftValue["issues"] = validatePost(draft.getSnapshot(), {
              imageCount: getImageCount(),
              requireImages: false
            }).filter(i => fields.has(i.field)));
          }
        }
      })(_nextValue2, previousValue, () => undefined);
    };
    draft.subscribe(_onChange2);
  })();
  function selectLocation(point) {
    if (state.getSnapshot().busy || !validCoordinates(point.latitude, point.longitude)) return;
    draft.edit(draftValue => draftValue["latitude"] = Number(point.latitude));
    draft.edit(draftValue => draftValue["longitude"] = Number(point.longitude));
    draft.edit(draftValue => draftValue["confirmedLocation"] = '');
    persist();
  }
  function clearLocation() {
    if (state.getSnapshot().busy) return;
    draft.edit(draftValue => draftValue["latitude"] = '');
    draft.edit(draftValue => draftValue["longitude"] = '');
    draft.edit(draftValue => draftValue["confirmedLocation"] = '');
    persist();
  }
  function confirmLocation() {
    if (state.getSnapshot().busy || !String(draft.getSnapshot().address).trim() || !validCoordinates(draft.getSnapshot().latitude, draft.getSnapshot().longitude)) return false;
    draft.edit(draftValue => draftValue["confirmedLocation"] = locationSignature(draft.getSnapshot()));
    state.edit(draftValue => draftValue["notice"] = 'Đã xác nhận ghim cho địa chỉ hiện tại.');
    persist();
    return true;
  }
  async function chooseFiles(list) {
    if (state.getSnapshot().busy) return;
    state.edit(draftValue => draftValue["busy"] = true);
    state.edit(draftValue => draftValue["error"] = '');
    const run = epoch;
    try {
      const chosen = Array.from(list);
      validateFiles(chosen);
      if (chosen.length + images.getSnapshot().length > 30) throw Error('Tối đa 30 ảnh/tin.');
      for (const file of chosen) if (typeof globalThis.createImageBitmap === 'function') {
        const bitmap = await createImageBitmap(file);
        const good = bitmap.width <= 12000 && bitmap.height <= 12000 && bitmap.width * bitmap.height <= 40000000;
        bitmap.close();
        if (!good) throw Error('Ảnh tối đa 12000 px mỗi chiều và 40 triệu pixel.');
      }
      assertRun(run);
      for (const file of chosen) {
        const entry = {
          key: 'local-' + ++serial,
          file,
          preview: urls?.createObjectURL?.(file) || ''
        };
        images.edit(draftValue => draftValue.push(entry));
        if (!coverKey.getSnapshot()) coverKey.set(entry.key);
      }
      state.edit(draftValue => draftValue["notice"] = 'Ảnh mới được giữ trong tab này; bấm Lưu nháp để tải lên tài khoản.');
      state.edit(draftValue => draftValue["lostFiles"] = 0);
      persist();
    } catch (e) {
      if (!e.stale) {
        state.edit(draftValue => draftValue["error"] = e.message || 'Không đọc được ảnh. Hãy chọn JPEG/PNG hợp lệ.');
        state.edit(draftValue => draftValue["issues"] = [fieldIssue('images', state.getSnapshot().error)]);
      }
    } finally {
      if (run === epoch) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  function removeImage(keyValue) {
    if (state.getSnapshot().busy) return;
    const i = images.getSnapshot().findIndex(e => e.key === keyValue);
    if (i < 0) return;
    const [entry] = images.edit(draftValue => draftValue.splice(i, 1));
    if (entry.server) removed.edit(draftValue => draftValue.push(entry.server.id));
    release(entry);
    if (coverKey.getSnapshot() === entry.key) coverKey.set(images.getSnapshot()[0]?.key || '');
    persist();
  }
  function moveImage(keyValue, offset) {
    if (state.getSnapshot().busy) return;
    const i = images.getSnapshot().findIndex(e => e.key === keyValue),
      j = i + offset;
    if (i < 0 || j < 0 || j >= images.getSnapshot().length) return;
    [images.getSnapshot()[i], images.getSnapshot()[j]] = [images.getSnapshot()[j], images.getSnapshot()[i]];
    persist();
  }
  function chooseCover(keyValue) {
    if (!state.getSnapshot().busy && images.getSnapshot().some(e => e.key === keyValue)) {
      coverKey.set(keyValue);
      persist();
    }
  }
  async function mine(run) {
    const items = [];
    for (let page = 0; page < 50; page++) {
      const result = await call(run, '/users/me/properties?size=100&page=' + page);
      items.push(...result.items);
      if (page + 1 >= result.totalPages) return items;
    }
    throw Error('Danh sách quá lớn để đối chiếu an toàn. Vui lòng kiểm tra Tin đăng của tôi.');
  }
  async function resolveCreate(run) {
    const pending = state.getSnapshot().uncertainCreate;
    if (!pending) return null;
    const matches = (await mine(run)).filter(i => String(i.ownerId) === actor && !pending.beforeIds.includes(i.property.id) && samePayload(pending.body, payloadFromManaged(i)));
    if (matches.length !== 1) throw Error('Chưa xác định được kết quả tạo nháp. Nội dung vẫn được giữ. Kiểm tra Tin đăng của tôi rồi bấm “Đối chiếu kết quả”; hệ thống chưa tạo thêm tin để tránh trùng.');
    const value = checkItem(matches[0]);
    setManaged(value);
    state.edit(draftValue => draftValue["uncertainCreate"] = null);
    persist();
    return value;
  }
  async function current(run) {
    return checkItem(await call(run, '/users/me/properties/' + managed.getSnapshot().property.id));
  }
  async function mutate(run, p, options, accept) {
    try {
      return checkItem(await call(run, p, options));
    } catch (e) {
      if (!uncertain(e)) throw e;
      try {
        const fresh = await current(run);
        if (await accept(fresh)) return fresh;
        if (fresh.property.contentVersion !== managed.getSnapshot().property.contentVersion) state.edit(draftValue => draftValue["conflict"] = true);
      } catch (check) {
        if (check.stale) throw check;
      }
      throw e;
    }
  }
  async function digest(blob) {
    return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', await blob.arrayBuffer())), v => v.toString(16).padStart(2, '0')).join('');
  }
  async function resolveUpload(run) {
    const pending = state.getSnapshot().uncertainUpload;
    if (!pending) return;
    const fresh = await current(run);
    const candidates = fresh.property.images.filter(i => !pending.beforeIds.includes(i.id));
    const found = [];
    for (const image of candidates) {
      const blob = await call(run, image.url.replace(/^\/api\/v1/, ''), {
        responseType: 'blob'
      });
      if ((await digest(blob)) === pending.hash) found.push(image);
    }
    if (found.length !== 1) throw Error('Chưa xác nhận được ảnh tải lên. Hãy đối chiếu kết quả hoặc kiểm tra tin trên tài khoản; ảnh trong form được giữ và chưa tải lặp.');
    const entry = images.getSnapshot().find(e => e.key === pending.key);
    if (entry) {
      entry.server = found[0];
      entry.file = null;
      release(entry);
    } else if (!images.getSnapshot().some(e => e.server?.id === found[0].id)) {
      images.edit(draftValue => draftValue.push({
        key: found[0].id,
        server: found[0]
      }));
      state.edit(draftValue => draftValue["lostFiles"] = Math.max(0, state.getSnapshot().lostFiles - 1));
    }
    setManaged(fresh);
    state.edit(draftValue => draftValue["uncertainUpload"] = null);
    persist();
  }
  async function save(submit = false) {
    if (state.getSnapshot().busy || state.getSnapshot().complete) return false;
    if (!permitted() || !state.getSnapshot().loaded || state.getSnapshot().loadError) {
      state.edit(draftValue => draftValue["error"] = 'Không có quyền hoặc chưa tải được tin. Nội dung form được giữ.');
      return false;
    }
    state.edit(draftValue => draftValue["issues"] = validatePost(draft.getSnapshot(), {
      imageCount: getImageCount(),
      requireImages: submit
    }));
    if (submit && !draft.getSnapshot().accepted) state.edit(draftValue => draftValue["issues"].push(fieldIssue('consent', 'Xác nhận quyền đăng và tính chính xác của thông tin trước khi gửi duyệt.')));
    if (state.getSnapshot().issues.length) {
      state.edit(draftValue => draftValue["notice"] = 'Nội dung được giữ trên trình duyệt; chưa lưu nháp tài khoản.');
      return false;
    }
    if (state.getSnapshot().conflict) {
      state.edit(draftValue => draftValue["error"] = 'Hãy đối chiếu phiên bản máy chủ trước khi lưu lại.');
      return false;
    }
    state.edit(draftValue => draftValue["busy"] = true);
    state.edit(draftValue => draftValue["error"] = '');
    state.edit(draftValue => draftValue["notice"] = '');
    const run = epoch,
      body = buildPostPayload(draft.getSnapshot());
    try {
      if (state.getSnapshot().uncertainCreate) await resolveCreate(run);
      if (state.getSnapshot().uncertainUpload) await resolveUpload(run);
      if (!managed.getSnapshot()) {
        const before = await mine(run);
        state.edit(draftValue => draftValue["uncertainCreate"] = {
          body,
          beforeIds: before.map(i => i.property.id)
        });
        persist();
        try {
          setManaged(await call(run, '/properties', {
            method: 'POST',
            body
          }));
          state.edit(draftValue => draftValue["uncertainCreate"] = null);
          persist();
        } catch (e) {
          if (e.stale) throw e;
          if (!uncertain(e)) {
            state.edit(draftValue => draftValue["uncertainCreate"] = null);
            persist();
            throw e;
          }
          await resolveCreate(run);
        }
      } else if (!samePayload(body, payloadFromManaged(managed.getSnapshot())) || !submit && managed.getSnapshot().property.status !== 'DRAFT') {
        const p = managed.getSnapshot().property;
        setManaged(await mutate(run, '/properties/' + p.id + '?expectedVersion=' + p.contentVersion, {
          method: 'PATCH',
          body
        }, fresh => fresh.property.status === 'DRAFT' && samePayload(body, payloadFromManaged(fresh))));
      }
      while (removed.getSnapshot().length) {
        const id = removed.getSnapshot()[0],
          p = managed.getSnapshot().property;
        if (p.images.some(i => i.id === id)) setManaged(await mutate(run, '/properties/' + p.id + '/images/' + id + '?expectedVersion=' + p.contentVersion, {
          method: 'DELETE'
        }, fresh => !fresh.property.images.some(i => i.id === id)));
        removed.edit(draftValue => draftValue.shift());
        persist();
      }
      for (const entry of images.getSnapshot().filter(e => !e.server)) {
        const p = managed.getSnapshot().property,
          hash = await digest(entry.file);
        assertRun(run);
        const data = new FormData();
        data.append('file', entry.file);
        state.edit(draftValue => draftValue["uncertainUpload"] = {
          key: entry.key,
          hash,
          beforeIds: p.images.map(i => i.id)
        });
        persist();
        try {
          const result = checkItem(await call(run, '/properties/' + p.id + '/images?expectedVersion=' + p.contentVersion, {
            method: 'POST',
            body: data
          }));
          const fresh = result.property.images.filter(i => !p.images.some(old => old.id === i.id));
          if (fresh.length !== 1) throw Error('Không xác định được ảnh vừa tải.');
          entry.server = fresh[0];
          entry.file = null;
          release(entry);
          setManaged(result);
          state.edit(draftValue => draftValue["uncertainUpload"] = null);
          persist();
        } catch (e) {
          if (e.stale) throw e;
          if (!uncertain(e)) {
            state.edit(draftValue => draftValue["uncertainUpload"] = null);
            persist();
            throw e;
          }
          await resolveUpload(run);
        }
      }
      const ids = images.getSnapshot().map(e => e.server.id);
      if (ids.length && JSON.stringify(ids) !== JSON.stringify(managed.getSnapshot().property.images.map(i => i.id))) {
        const p = managed.getSnapshot().property;
        setManaged(await mutate(run, '/properties/' + p.id + '/images/order', {
          method: 'PUT',
          body: {
            expectedVersion: p.contentVersion,
            imageIds: ids
          }
        }, fresh => JSON.stringify(fresh.property.images.map(i => i.id)) === JSON.stringify(ids)));
      }
      const cover = images.getSnapshot().find(e => e.key === coverKey.getSnapshot())?.server;
      if (cover && !managed.getSnapshot().property.images.find(i => i.id === cover.id)?.cover) {
        const p = managed.getSnapshot().property;
        setManaged(await mutate(run, '/properties/' + p.id + '/images/' + cover.id, {
          method: 'PATCH',
          body: {
            expectedVersion: p.contentVersion,
            cover: true
          }
        }, fresh => fresh.property.images.some(i => i.id === cover.id && i.cover)));
      }
      if (submit) {
        const p = managed.getSnapshot().property;
        if (!['PENDING', 'PUBLISHED'].includes(p.status)) setManaged(await mutate(run, '/properties/' + p.id + '/submit', {
          method: 'POST',
          body: {
            expectedVersion: p.contentVersion
          }
        }, fresh => ['PENDING', 'PUBLISHED'].includes(fresh.property.status)));
        state.edit(draftValue => draftValue["complete"] = true);
        state.edit(draftValue => draftValue["notice"] = 'Đã gửi tin để quản trị viên kiểm duyệt.');
      } else state.edit(draftValue => draftValue["notice"] = 'Đã lưu đầy đủ nội dung và ảnh hiện tại vào nháp tài khoản.');
      assertRun(run);
      state.edit(draftValue => draftValue["savedAt"] = clock());
      persist();
      return true;
    } catch (e) {
      if (!e.stale) {
        if (e.status === 409) state.edit(draftValue => draftValue["conflict"] = true);
        state.edit(draftValue => draftValue["error"] = errorText(e));
        if (e.fields) state.edit(draftValue => draftValue["issues"] = Object.entries(e.fields).map(([field, message]) => fieldIssue(field, message)));
        persist();
      }
      return false;
    } finally {
      if (run === epoch) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  async function checkResult() {
    if (state.getSnapshot().busy || !permitted()) return;
    state.edit(draftValue => draftValue["busy"] = true);
    state.edit(draftValue => draftValue["error"] = '');
    const run = epoch;
    try {
      if (state.getSnapshot().uncertainCreate) await resolveCreate(run);
      if (state.getSnapshot().uncertainUpload) await resolveUpload(run);
      state.edit(draftValue => draftValue["notice"] = 'Đã đối chiếu kết quả. Kiểm tra lại thông tin rồi bấm Lưu nháp hoặc Gửi duyệt.');
    } catch (e) {
      if (!e.stale) state.edit(draftValue => draftValue["error"] = errorText(e));
    } finally {
      if (run === epoch) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  async function reviewVersion() {
    if (state.getSnapshot().busy || !managed.getSnapshot()) return;
    state.edit(draftValue => draftValue["busy"] = true);
    const run = epoch;
    try {
      const fresh = await current(run);
      const old = managed.getSnapshot().property.images.map(i => i.id),
        next = fresh.property.images.map(i => i.id);
      if (JSON.stringify(old) !== JSON.stringify(next)) {
        state.edit(draftValue => draftValue["error"] = 'Ảnh trên máy chủ đã thay đổi. Hãy mở tin tài khoản để đối chiếu; nội dung form vẫn được giữ.');
        return;
      }
      setManaged(fresh);
      state.edit(draftValue => draftValue["conflict"] = false);
      state.edit(draftValue => draftValue["error"] = '');
      state.edit(draftValue => draftValue["notice"] = 'Đã lấy phiên bản mới, giữ nội dung bạn nhập. Kiểm tra lại trước khi lưu đè thay đổi của tin.');
    } catch (e) {
      if (!e.stale) state.edit(draftValue => draftValue["error"] = errorText(e));
    } finally {
      if (run === epoch) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  function reset() {
    if (state.getSnapshot().busy) return;
    try {
      if (key) getStorage()?.removeItem(key);
    } catch {}
    epoch++;
    key = '';
    slot = '';
    clearMemory();
  }
  function editAgain() {
    state.edit(draftValue => draftValue["complete"] = false);
    draft.edit(draftValue => draftValue["accepted"] = false);
    persist();
  }
  return combineStateStores([draft, state, managed, images, coverKey, removed], () => ({
    draft: draft.getSnapshot(),
    state: state.getSnapshot(),
    managed: managed.getSnapshot(),
    images: images.getSnapshot(),
    coverKey: coverKey.getSnapshot(),
    imageCount: getImageCount(),
    dirty: getDirty(),
    bindActor,
    initialize,
    persist,
    selectLocation,
    clearLocation,
    confirmLocation,
    chooseFiles,
    removeImage,
    moveImage,
    chooseCover,
    save,
    checkResult,
    reviewVersion,
    reset,
    editAgain,
    updateDraft: draft.edit,
    updateDraftValue: draft.set,
    updateState: state.edit,
    updateStateValue: state.set,
    updateManaged: managed.edit,
    updateManagedValue: managed.set,
    updateImages: images.edit,
    updateImagesValue: images.set,
    updateCoverKey: coverKey.edit,
    updateCoverKeyValue: coverKey.set
  }));
}
const editor = createPostEditor();
(() => {
  let _previousValue3 = (() => [session.getSnapshot().user?.id, session.getSnapshot().user?.role, session.getSnapshot().user?.status])();
  const _onChange3 = () => {
    const _nextValue3 = (() => [session.getSnapshot().user?.id, session.getSnapshot().user?.role, session.getSnapshot().user?.status])();
    if (stateKey(_nextValue3) === stateKey(_previousValue3)) return;
    const previousValue = _previousValue3;
    _previousValue3 = _nextValue3;
    (() => editor.getSnapshot().bindActor())(_nextValue3, previousValue, () => undefined);
  };
  session.subscribe(_onChange3);
})();
function usePostEditor() {
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  useSyncExternalStore(editor.subscribe, editor.getSnapshot);
  const router = useAppNavigation(),
    route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _watched = (() => [_routeLatest.current.query.edit, session.getSnapshot().user?.id])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (() => editor.getSnapshot().initialize(_routeLatest.current.query.edit))(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  async function focusIssue() {
    await afterPaint();
    if (_routeLatest.current.hash.startsWith('#post-')) document.getElementById(_routeLatest.current.hash.slice(1))?.focus({
      preventScroll: true
    });
  }
  const _watched2 = (() => _routeLatest.current.hash)();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    _initialized2.current = true;
    const result = focusIssue(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  async function goStep(step, field) {
    if (editor.getSnapshot().state.busy) return;
    const target = postSteps[step - 1];
    if (target) {
      await _routerLatest.current.push({
        path: target.path,
        query: _routeLatest.current.query,
        hash: field ? '#post-' + field : ''
      });
      await focusIssue();
    }
  }
  async function goNext() {
    const current = postSteps.find(s => s.path === _routeLatest.current.path)?.step || 1;
    editor.getSnapshot().updateState(draftValue => draftValue["issues"] = validatePost(editor.getSnapshot().draft, {
      steps: Array.from({
        length: current
      }, (_, i) => i + 1),
      imageCount: editor.getSnapshot().imageCount
    }));
    if (editor.getSnapshot().state.issues.length) {
      const first = editor.getSnapshot().state.issues[0];
      await goStep(first.step, first.field);
    } else await goStep(Math.min(current + 1, 3));
  }
  async function saveDraft(submit = false) {
    const success = await editor.getSnapshot().save(submit);
    if (editor.getSnapshot().managed && _routeLatest.current.query.edit !== editor.getSnapshot().managed.property.id) await _routerLatest.current.replace({
      path: _routeLatest.current.path,
      query: {
        ..._routeLatest.current.query,
        edit: editor.getSnapshot().managed.property.id
      },
      hash: _routeLatest.current.hash
    });
    if (editor.getSnapshot().state.issues.length) {
      const first = editor.getSnapshot().state.issues[0];
      await goStep(first.step, first.field);
    }
    return success;
  }
  async function startNew() {
    editor.getSnapshot().reset();
    await _routerLatest.current.replace('/post');
    await editor.getSnapshot().initialize();
  }
  return {
    ...editor.getSnapshot(),
    goStep,
    goNext,
    saveDraft,
    startNew
  };
}
export { usePostEditor };
