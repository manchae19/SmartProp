import { api } from '../auth/api.js';
const path = '/users/me/valuation-history';
export function createHistoryClient(request = api) {
  return {
    list: (page = 0) => request(`${path}?page=${page}&size=10`),
    save: (input, key) => request(path, {
      method: 'POST',
      body: input,
      headers: {
        'Idempotency-Key': key
      }
    }),
    remove: id => request(`${path}/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    })
  };
}
