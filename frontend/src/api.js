const configuredBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
export const API_BASE_URL = configuredBase.replace(/\/+$/, '');

export class ApiError extends Error {
  constructor(status, body) {
    const details = Array.isArray(body?.detail)
      ? body.detail.map(item => `${(item.loc || []).at(-1) || 'request'}: ${item.msg}`).join(' ')
      : typeof body?.detail === 'string' ? body.detail
        : typeof body?.detail?.reason === 'string' ? body.detail.reason
          : body?.detail ? JSON.stringify(body.detail) : body?.error || 'The API request failed.';
    super(details);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export async function apiGet(path) {
  return request(path, { method: 'GET' });
}

export async function apiPost(path, payload) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: { Accept: 'application/json', ...options.headers } });
  } catch {
    throw new ApiError(0, { detail: `Packwise API is not reachable at ${API_BASE_URL}. Start the backend or check VITE_API_URL.` });
  }
  let body;
  try { body = await response.json(); } catch { body = { detail: `The API returned a non-JSON response (HTTP ${response.status}).` }; }
  if (!response.ok) throw new ApiError(response.status, body);
  return body;
}
