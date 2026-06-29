// Opttwo Custom App — Proxy / Custom-Object / Action SDK
// 沿用 AIGO 平台慣例（fde-sc1984 的 db.ts 精簡版）。
// 平台在 runtime 注入：__API_BASE__ / __APP_ID__ / __APP_TOKEN__ / __IS_EXTERNAL__

const API_BASE = (window as any).__API_BASE__ || '/api/v1';
const APP_ID = (window as any).__APP_ID__ || '';

function _h(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  const t = (window as any).__APP_TOKEN__ || '';
  if (t) h['Authorization'] = 'Bearer ' + t;
  return h;
}

async function _r(resp: Response): Promise<any> {
  if (!resp.ok) {
    const b = await resp.json().catch(() => ({}));
    throw new Error(b.detail || 'API Error (' + resp.status + ')');
  }
  return resp.json();
}

const PAGE_MAX = 500;

// ── Odoo 實體表 proxy（受 AppDataReference 授權）──
async function _fetchPage(table: string, limit: number, offset: number): Promise<any[]> {
  const p = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return _r(await fetch(`${API_BASE}/proxy/${APP_ID}/${table}?${p}`, { headers: _h(), credentials: 'include' }));
}

export async function query(table: string, opts?: { limit?: number; offset?: number }): Promise<any[]> {
  if (opts?.limit !== undefined && opts.limit <= PAGE_MAX) return _fetchPage(table, opts.limit, opts.offset || 0);
  let all: any[] = [], offset = 0;
  while (true) {
    const page = await _fetchPage(table, PAGE_MAX, offset);
    if (!Array.isArray(page) || page.length === 0) break;
    all = all.concat(page);
    if (page.length < PAGE_MAX) break;
    offset += PAGE_MAX;
  }
  return all;
}

export async function insert(table: string, data: Record<string, any>): Promise<any> {
  return _r(await fetch(`${API_BASE}/proxy/${APP_ID}/${table}`, {
    method: 'POST', headers: _h(), credentials: 'include', body: JSON.stringify({ data }),
  }));
}

export async function update(table: string, id: string, data: Record<string, any>): Promise<any> {
  return _r(await fetch(`${API_BASE}/proxy/${APP_ID}/${table}/${id}`, {
    method: 'PATCH', headers: _h(), credentials: 'include', body: JSON.stringify({ data }),
  }));
}

export async function deleteRow(table: string, id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/proxy/${APP_ID}/${table}/${id}`, {
    method: 'DELETE', headers: _h(), credentials: 'include',
  });
  if (!resp.ok) throw new Error('Delete failed (' + resp.status + ')');
}

// ── Custom Object（x_opt_*，runtime 以 api_slug 解析 UUID）──
let _customIds: Record<string, string> | null = null;
async function _cid(slug: string): Promise<string> {
  if (slug.length === 36 && slug.includes('-')) return slug;
  if (!_customIds) {
    const resp = await fetch(`${API_BASE}/data/objects`, { headers: _h(), credentials: 'include' });
    _customIds = {};
    if (resp.ok) for (const o of (await resp.json().catch(() => []))) if (o.api_slug && o.id) _customIds[o.api_slug] = o.id;
  }
  const uuid = _customIds[slug];
  if (!uuid) throw new Error(`Custom object "${slug}" not found`);
  return uuid;
}

export async function queryCustom(slug: string): Promise<any[]> {
  const uuid = await _cid(slug);
  const resp = await fetch(`${API_BASE}/data/objects/${uuid}/records`, { headers: _h(), credentials: 'include' });
  return resp.ok ? resp.json() : [];
}

// ── Server-Side Action（寫入、需身分過濾的讀取一律走這裡）──
export async function runAction(actionName: string, params: Record<string, any> = {}): Promise<any> {
  const isExternal = !!(window as any).__IS_EXTERNAL__;
  const url = isExternal
    ? `${API_BASE}/ext/actions/run/${actionName}`
    : `${API_BASE}/actions/apps/${APP_ID}/run/${actionName}`;
  const resp = await fetch(url, { method: 'POST', headers: _h(), credentials: 'include', body: JSON.stringify({ params }) });
  if (!resp.ok) {
    const b = await resp.json().catch(() => ({}));
    throw new Error(b.detail || 'Action Error (' + resp.status + ')');
  }
  const result = await resp.json();
  if (result?.status === 'error') throw new Error(result?.error || result?.message || 'Action Error');
  return result?.result ?? result?.data ?? result;
}
