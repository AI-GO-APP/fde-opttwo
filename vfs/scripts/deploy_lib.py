"""共用部署函式（login / ensure_references / read_vfs / upload_vfs / verify_compile / publish_app）。
照 AIGO 平台慣例，沿用 fde-sc1984 的 deploy_lib（同一套部署 API）。
"""
import json, sys, os, urllib.request, urllib.error

API_BASE = "https://ai-go.app/api/v1"


def _req(method, url, headers, data=None, timeout=30):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def require_env(key):
    val = os.environ.get(key, "").strip()
    if not val:
        sys.exit(f"❌ 環境變數 {key} 未設定")
    return val


def login(email, password):
    status, body = _req("POST", f"{API_BASE}/auth/login",
                        {"Content-Type": "application/json"},
                        {"email": email, "password": password})
    if status != 200:
        sys.exit(f"❌ 登入失敗：{status} {body}")
    token = body.get("access_token", "")
    if not token:
        sys.exit("❌ 登入回應未包含 access_token")
    return token


def ensure_references(h, app_id, refs):
    status, body = _req("GET", f"{API_BASE}/refs/apps/{app_id}", h)
    existing = {x["table_name"]: x for x in (body if status == 200 else [])}
    for t in refs:
        tn = t["table_name"]
        if tn in existing:
            s2, _ = _req("PATCH", f"{API_BASE}/refs/{existing[tn]['id']}", h,
                         {"columns": t["columns"], "permissions": t["permissions"]})
        else:
            s2, _ = _req("POST", f"{API_BASE}/refs/apps/{app_id}", h, t)
        print(f"  [{tn}] {s2}")


_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", ".cache"}
_SKIP_FILES = {"package-lock.json", "yarn.lock", ".DS_Store"}

def read_vfs(vfs_dir):
    vfs = {}
    for root, dirs, files in os.walk(vfs_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname in _SKIP_FILES:
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, vfs_dir).replace(os.sep, "/")
            with open(full, "r", encoding="utf-8") as f:
                vfs[rel] = f.read()
    return vfs


def upload_vfs(h, app_id, vfs):
    print(f"  檔案數: {len(vfs)}")
    status, body = _req("PUT", f"{API_BASE}/builder/apps/{app_id}/source", h,
                        {"vfs_state": vfs}, timeout=60)
    print(f"  上傳: {status}")
    if status != 200:
        sys.exit(f"❌ 上傳失敗：{body}")


def verify_compile(h, app_id):
    """編譯一次抓 TS/JSX 錯誤；compile 200 但 success=false 也視為失敗。"""
    s, b = _req("GET", f"{API_BASE}/builder/apps/{app_id}", h)
    if s != 200:
        sys.exit(f"❌ 取得 app slug 失敗：{s}")
    slug = (b or {}).get("slug") or app_id
    s2, body = _req("POST", f"{API_BASE}/compile/compile/{slug}?dev=true", h, {}, timeout=120)
    success = bool((body or {}).get("success"))
    print(f"  編譯驗證: {s2} success={success}")
    if not success:
        err = (body or {}).get("error") or body
        sys.exit(f"❌ 編譯失敗：\n{err}")


def publish_app(h, app_id):
    status, body = _req("POST", f"{API_BASE}/builder/apps/{app_id}/publish", h,
                        {"published_assets": {}}, timeout=120)
    print(f"  發布: {status}")
    if status not in (200, 201):
        sys.exit(f"❌ 發布失敗：{body}")


def run_dev(h, app_id, action_name, params=None):
    """執行未發布的 action（use_dev=true），用於開發期測試，不影響 production。"""
    url = f"{API_BASE}/actions/apps/{app_id}/execute-by-name?action_name={action_name}&use_dev=true"
    status, body = _req("POST", url, h, {"params": params or {}})
    if status != 200:
        sys.exit(f"❌ dev 執行失敗：{status} {body}")
    return body
