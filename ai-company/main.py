"""AI Company v0.2: one-shot five-agent strategy meeting with Supabase persistence."""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI

MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
MAX_OUTPUT_TOKENS = int(os.getenv('MAX_OUTPUT_TOKENS', '1300'))
URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')


def supabase(table, payload):
    endpoint = f'{URL}/rest/v1/{table}'
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = Request(endpoint, data=data, headers={
        'apikey': KEY, 'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation'
    }, method='POST')
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))[0]
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Supabase {table}: HTTP {exc.code}: {detail[:800]}') from exc


def ask(client, role, task):
    response = client.responses.create(
        model=MODEL,
        instructions=(
            f'あなたはAI企業の{role}。初期資金10万円、6か月後に月利益10万円を目標とする。'
            'オンライン事業のみ。外部の市場データは閲覧できないため、未検証の仮説と事実を区別する。'
            '支出、公開、契約、外部アクションは一切行わず提案だけする。'
            '日本語で具体的かつ簡潔に答える。'
        ),
        input=task,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    output = response.output_text.strip()
    if not output:
        raise RuntimeError(f'{role}: 空の応答です。モデルや出力上限を確認してください。')
    usage = getattr(response, 'usage', None)
    return output, {
        'input_tokens': getattr(usage, 'input_tokens', None),
        'output_tokens': getattr(usage, 'output_tokens', None),
    }


def main():
    for name in ('OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'):
        if not os.getenv(name):
            raise RuntimeError(f'{name} をRailway Variablesに設定してください。')
    if not URL.startswith('https://'):
        raise RuntimeError('SUPABASE_URL は https:// から始まるProject URLを指定してください。')
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=90, max_retries=2)
    print('CSO: 事業候補を作成中...', flush=True)
    cso, u1 = ask(client, 'CSO', '低予算で試せるオンライン事業候補を3件。対象顧客、提供価値、収益モデル、初期検証方法、最大リスクを記述。')
    print('CPO / CMO / CFO: 順次評価中...', flush=True)
    cpo, u2 = ask(client, 'CPO', f'次の候補を開発難易度、最小実用製品、2週間の実装計画で評価。\n{cso}')
    cmo, u3 = ask(client, 'CMO', f'次の候補を集客方法、顧客獲得検証、差別化で評価。実際の調査済みと偽らないこと。\n{cso}')
    cfo, u4 = ask(client, 'CFO', f'次の候補を10万円以内の予算配分、粗利仮説、損益分岐、撤退条件で評価。\n{cso}')
    print('COO: 経営会議の結論を作成中...', flush=True)
    coo, u5 = ask(client, 'COO', f'以下を統合して最優先の事業案を1件提案。根拠、未検証事項、最初の7日間、オーナー承認が必要な事項を示す。\nCSO:\n{cso}\nCPO:\n{cpo}\nCMO:\n{cmo}\nCFO:\n{cfo}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    title = f'AI経営会議 {stamp} UTC'
    content = '\n\n'.join([f'# {title}', f'## CSO\n{cso}', f'## CPO\n{cpo}', f'## CMO\n{cmo}', f'## CFO\n{cfo}', f'## COO（最終提案）\n{coo}'])
    outdir = Path('outputs')
    outdir.mkdir(exist_ok=True)
    path = outdir / f'meeting_{stamp}.md'
    path.write_text(content, encoding='utf-8')
    print('Supabase: 経営会議を保存中...', flush=True)
    meeting = supabase('meetings', {'title': title, 'content': content, 'status': 'completed'})
    # The selected idea remains a proposal; no publication, spending or contracts.
    supabase('business_ideas', {
        'meeting_id': meeting['id'], 'name': 'COO推奨事業案（議事録参照）',
        'description': coo, 'status': 'proposed'
    })
    for role, usage in zip(('CSO','CPO','CMO','CFO','COO'), (u1,u2,u3,u4,u5)):
        supabase('execution_logs', {
            'agent_id': {'COO':'AG-01','CSO':'AG-02','CPO':'AG-03','CMO':'AG-04','CFO':'AG-05'}[role],
            'message': f'{title} | {role} 完了 | input_tokens={usage["input_tokens"]} output_tokens={usage["output_tokens"]}'
        })
    print(f'完了: {path}', flush=True)
    print(f'Supabase meetings.id: {meeting["id"]}', flush=True)
    print('※API費用の実額は未計算です。OpenAI Platformで確認してください。', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, HTTPError, URLError, Exception) as exc:
        print(f'エラー: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
