
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = os.environ["SUPABASE_URL"].strip().strip('"').strip("'").rstrip("/")
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
endpoint = f"{url}/rest/v1/meetings?select=id&limit=1"

# APIキーを表示しない
print("接続先:", endpoint, flush=True)

req = Request(
    endpoint,
    headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
    },
    method="GET",
)

try:
    with urlopen(req, timeout=20) as response:
        print("HTTP:", response.status)
        print("Supabase接続成功")
        print(response.read().decode("utf-8")[:500])
except HTTPError as e:
    print("HTTP:", e.code)
    print("エラー:", e.read().decode("utf-8")[:1000])
except URLError as e:
    print("接続エラー:", e.reason)
