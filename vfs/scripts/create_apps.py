"""建立 Opttwo 的兩個 Custom App（盤商後台 admin + 回收商前台 ordering），
並把回傳的 UUID 自動寫回專案根目錄的 .env。

平台建立 app 需帶 template_slug（必填，tenant-specific）。因此分兩步：

  步驟 1：列出可用模板，挑出「空白/自建」模板的 slug
    set -a && source .env && set +a
    python3 vfs/scripts/create_apps.py --list

  步驟 2：把下面 ADMIN_TEMPLATE_SLUG / ORDERING_TEMPLATE_SLUG 填好後，建立兩個 app
    python3 vfs/scripts/create_apps.py

access_mode 由模板決定；盤商後台要 internal、回收商前台要 external（或 self_built，
兩者都支援外部使用者 LINE 登入）。挑模板時依此選對 access_mode。
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from deploy_lib import require_env, login, _req, API_BASE

# Windows 終端常是 cp950，輸出 emoji/中文會 UnicodeEncodeError；強制 utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── 步驟 2 前先填這兩個（用 --list 查到的 slug）──
ADMIN_TEMPLATE_SLUG = "starter-internal"     # 盤商後台（internal 空白起始模板）
ORDERING_TEMPLATE_SLUG = "starter-external"  # 回收商前台（external 空白起始模板）

# app 名稱與子網域（子網域選填、需全小寫英數與連字號；可改）
# 子網域留空（選填）→ 之後在 Builder 補設
ADMIN_NAME, ADMIN_SUBDOMAIN = "Opttwo 盤商後台", ""
ORDERING_NAME, ORDERING_SUBDOMAIN = "Opttwo 回收商前台", ""

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


def list_templates(h):
    status, body = _req("GET", f"{API_BASE}/templates", h)
    if status != 200:
        sys.exit(f"❌ 取得模板列表失敗：{status} {body}")
    rows = body if isinstance(body, list) else (body or {}).get("items", [])
    print(f"\n可用模板（{len(rows)}）：")
    print(f"  {'slug':<28} {'access_mode':<12} name")
    print("  " + "-" * 60)
    for t in rows:
        print(f"  {str(t.get('slug','')):<28} {str(t.get('access_mode','')):<12} {t.get('name','')}")
    print("\n→ 把適合的 slug 填進腳本上方 ADMIN_TEMPLATE_SLUG / ORDERING_TEMPLATE_SLUG，再不帶 --list 跑一次。")


def _existing_apps(h):
    s, b = _req("GET", f"{API_BASE}/builder/apps", h)
    rows = b if isinstance(b, list) else (b or {}).get("items", [])
    return {a.get("name"): a for a in (rows if s == 200 else [])}


def create_app(h, name, subdomain, template_slug, existing):
    # 冪等：同名 app 已存在就沿用，不重複建
    if name in existing:
        a = existing[name]
        print(f"↩️  「{name}」已存在，沿用 app_id={a.get('id')} access_mode={a.get('access_mode')}")
        return a.get("id")
    payload = {"name": name, "template_slug": template_slug}
    if subdomain:
        payload["subdomain"] = subdomain
    status, body = _req("POST", f"{API_BASE}/builder/apps", h, payload)
    if status not in (200, 201):
        sys.exit(f"❌ 建立 app「{name}」失敗：{status} {body}")
    app_id = (body or {}).get("id")
    print(f"✅ 已建立「{name}」 app_id={app_id} slug={(body or {}).get('slug')} access_mode={(body or {}).get('access_mode')}")
    return app_id


def write_env(admin_id, ordering_id):
    if not os.path.exists(ENV_PATH):
        print(f"⚠️ 找不到 {ENV_PATH}，請手動填入 app_id")
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for ln in lines:
        if re.match(r"^\s*ADMIN_APP_ID\s*=", ln):
            out.append(f"ADMIN_APP_ID={admin_id}")
        elif re.match(r"^\s*ORDERING_APP_ID\s*=", ln):
            out.append(f"ORDERING_APP_ID={ordering_id}")
        else:
            out.append(ln)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"✅ 已把兩個 app_id 寫回 {os.path.abspath(ENV_PATH)}")


def main():
    token = login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD"))
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if "--list" in sys.argv:
        list_templates(h)
        return

    if not ADMIN_TEMPLATE_SLUG or not ORDERING_TEMPLATE_SLUG:
        sys.exit("❌ 請先用 --list 查模板，並填好 ADMIN_TEMPLATE_SLUG / ORDERING_TEMPLATE_SLUG")

    print("=== 建立兩個 Custom App（冪等）===")
    existing = _existing_apps(h)
    admin_id = create_app(h, ADMIN_NAME, ADMIN_SUBDOMAIN, ADMIN_TEMPLATE_SLUG, existing)
    ordering_id = create_app(h, ORDERING_NAME, ORDERING_SUBDOMAIN, ORDERING_TEMPLATE_SLUG, existing)
    write_env(admin_id, ordering_id)
    print("\n✅ 完成。接著可跑 create_reloop_objects.py 與 deploy_*.py")


if __name__ == "__main__":
    main()
