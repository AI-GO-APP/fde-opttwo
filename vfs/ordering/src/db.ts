// Opttwo Ordering（回收商前台）— SDK。__IS_EXTERNAL__ 由平台注入為 true，
// runAction 走 /ext/actions/run/...；寫入一律走 action，不直接對 x_opt_* proxy。
// 內容與 admin/src/db.ts 相同（共用慣例）。

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

async function _fetchPage(table: string, limit: number, offset: number): Promise<any[]> {
  const p = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return _r(await fetch(`${API_BASE}/ext/proxy/${table}?${p}`, { headers: _h(), credentials: 'include' }));
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

// Server-Side Action（回收商所有寫入操作的唯一入口）
export async function runAction(actionName: string, params: Record<string, any> = {}): Promise<any> {
  const resp = await fetch(`${API_BASE}/ext/actions/run/${actionName}`, {
    method: 'POST', headers: _h(), credentials: 'include', body: JSON.stringify({ params }),
  });
  if (!resp.ok) {
    const b = await resp.json().catch(() => ({}));
    throw new Error(b.detail || 'Action Error (' + resp.status + ')');
  }
  const result = await resp.json();
  if (result?.status === 'error') throw new Error(result?.error || result?.message || 'Action Error');
  return result?.result ?? result?.data ?? result;
}
