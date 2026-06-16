import os
import sys
import urllib.parse
import urllib.request


def build_healthcheck_url(app_url):
    parsed = urllib.parse.urlparse(app_url)
    query = urllib.parse.parse_qs(parsed.query)
    query["health"] = ["1"]
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(query, doseq=True))
    )


def main():
    app_url = os.environ.get("STREAMLIT_APP_URL", "").strip()
    if not app_url:
        print("STREAMLIT_APP_URL is not set.")
        return 1

    healthcheck_url = build_healthcheck_url(app_url)
    request = urllib.request.Request(
        healthcheck_url,
        headers={"User-Agent": "housing-app-keepalive/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"Pinged {healthcheck_url} -> HTTP {response.status}")
            return 0 if response.status < 500 else 1
    except Exception as exc:
        print(f"Keepalive ping failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
