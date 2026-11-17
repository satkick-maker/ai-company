"""One-shot COO approval-request drafting from the latest market research; no execution."""
import json
import os
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from openai import OpenAI


def api(method, table, payload=None, params=''):
    base = os.environ['SUPABASE_URL'].strip().rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY'].strip()
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc.endswith('.supabase.co') or parsed.path not in ('','/'):
        raise ValueError('SUPABASE_URLが不正です')
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {'apikey':key, 'Authorization':f'Bearer {key}', 'Content-Type':'application/json', 'Prefer':'return=representation'}
    req = Request(f'{base}/rest/v1/{table}{params}', data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except HTTPError as e:
        raise RuntimeError(f'Supabase {e.code}: {e.read().decode(errors="replace")[:500]}') from e


def main():
    if os.getenv('RUN_PROPOSALS') != '1':
        print('安全停止: RUN_PROPOSALS=1 の場合だけ申請案を1件生成します。')
        return
    for name in ('OPENAI_API_KEY','SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY','SOURCE_MEETING_ID'):
        if not os.getenv(name):
            raise RuntimeError(f'{name}が未設定です')
    meeting_id = os.environ['SOURCE_MEETING_ID'].strip()
    import uuid
    uuid.UUID(meeting_id)
    meetings = api('GET','meetings',params=f'?select=id,title,content&id=eq.{meeting_id}&limit=1')
    if len(meetings) != 1:
        raise RuntimeError('指定した議事録が見つかりません')
    existing = api('GET','approval_requests',params=f'?select=id&source_meeting_id=eq.{meeting_id}&request_type=eq.research&limit=1')
    if existing:
        print('安全停止: この議事録の調査申請は作成済みです。')
        return
    print('COO: 承認申請案を作成中...', flush=True)
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=120, max_retries=1)
    response = client.responses.create(
        model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
        instructions=('あなたはAI CompanyのCOO。オーナーは事業化・公開・支出・契約を承認していない。'
            '市場調査レポートから、追加の内部調査の承認申請を1件だけ作成する。'
            '外部公開・登録・契約・広告出稿・購入・外部送信を提案しない。'
            '出力は日本語のJSONオブジェクトのみ。title,descriptionの2文字列キー。'
            'descriptionには調査目的、具体的な調査項目、成果物、出典検証方法、費用はAPI従量課金が別途発生することを明記。'),
        input=(meetings[0].get('content') or '')[:15000],
        max_output_tokens=1000)
    raw = response.output_text.strip()
    if raw.startswith('```'):
        raw = raw.strip('`').removeprefix('json').strip()
    obj = json.loads(raw)
    title = obj['title'].strip()
    description = obj['description'].strip()
    if not (5 <= len(title) <= 120 and 20 <= len(description) <= 4000):
        raise RuntimeError('AI申請内容が不正です')
    # A unique DB constraint ensures retries cannot create duplicate requests.
    created = api('POST','approval_requests',{
        'source_meeting_id':meeting_id, 'request_type':'research', 'requested_by':'COO',
        'title':title, 'description':description,
        'estimated_cost_yen':0, 'external_action':False, 'status':'pending'})
    print(f'申請保存完了: {created[0]["id"]} | {title}')
    print('承認しても業務は自動実行されません。')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'エラー: {exc}', file=sys.stderr)
        sys.exit(1)
