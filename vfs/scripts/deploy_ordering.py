"""Opttwo Ordering（回收商前台）— 部署入口。

環境變數（.env）：
  AIGO_EMAIL      - AI GO 登入 email
  AIGO_PASSWORD   - AI GO 登入密碼
  ORDERING_APP_ID - Ordering App 的 UUID（向平台方索取）

用法：
  set -a && source .env && set +a
  python3 vfs/scripts/deploy_ordering.py
  python3 vfs/scripts/deploy_ordering.py --no-publish
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from deploy_lib import require_env, login, ensure_references, read_vfs, upload_vfs, verify_compile, publish_app
from db_ordering import REFS

VFS_DIR = os.path.join(os.path.dirname(__file__), "..", "ordering")


def main():
    no_publish = "--no-publish" in sys.argv
    print("=== Opttwo Ordering Custom App 部署 ===")

    email    = require_env("AIGO_EMAIL")
    password = require_env("AIGO_PASSWORD")
    app_id   = require_env("ORDERING_APP_ID")

    print("\n[1/4] 登入...")
    token = login(email, password)
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("\n[2/4] 設定 DB References...")
    ensure_references(h, app_id, REFS)

    print("\n[3/4] 讀取並上傳 VFS...")
    upload_vfs(h, app_id, read_vfs(VFS_DIR))

    print("\n[4/4] 編譯驗證...")
    verify_compile(h, app_id)

    if no_publish:
        print("\n⏭️  略過發布（--no-publish）")
    else:
        print("\n[發布]...")
        publish_app(h, app_id)
        print("\n✅ Ordering 部署完成")


if __name__ == "__main__":
    main()
