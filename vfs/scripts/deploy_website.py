"""Deploy the Opt two website review app to AIGO."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from deploy_lib import login, publish_app, read_vfs, require_env, upload_vfs, verify_compile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    email = require_env("AIGO_EMAIL")
    password = require_env("AIGO_PASSWORD")
    app_id = require_env("WEBSITE_APP_ID")

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "website"))
    token = login(email, password)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("=== Deploy website review app ===")
    vfs = read_vfs(root)
    vfs = {
        path: content
        for path, content in vfs.items()
        if (
            not path.endswith(".html")
            and not path.startswith("src/assets/")
            and path not in {"src/livelyHtml.ts", "src/calmHtml.ts"}
            and path != "src/App.tsx"
            and not path.startswith("src/components/")
        )
    }
    upload_vfs(headers, app_id, vfs)
    verify_compile(headers, app_id)

    if "--no-publish" in sys.argv:
      print("Skip publish (--no-publish)")
      return

    publish_app(headers, app_id)
    print("Done")


if __name__ == "__main__":
    main()
