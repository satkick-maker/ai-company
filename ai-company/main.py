"""AI Company v0.3: owner-approved, one-shot web research. No external publishing."""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from openai import OpenAI

MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
MAX_OUTPUT_TOKENS = 1800
ROLES = {'CSO': 'AG-02', 'CMO': 'AG-04', 'CFO': 'AG-05', 'COO': 'AG-01'}


def sb(table, payload):
    base = os.environ['SUPABASE_URL'].strip().rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY'].strip()
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise RuntimeError('SUPABASE_URLにはhttps://...supabase.co のProject URLだけを設定してください')
    req = Request(f'{base}/rest/v1/{table}', data=json.dumps(payload, ensure_ascii=False).encode(), headers={
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation',
    }, method='POST')
    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if not isinstance(result, list) or not result:
                raise RuntimeError(f'{table}: 保存結果が空です')
            return result[0]
    except HTTPError as exc:
        raise RuntimeError(f'{table}: HTTP {exc.code}: {exc.read().decode(errors="replace")[:700]}') from exc


def ask(client, role, task, web=False):
    args = dict(model=MODEL, instructions=(
        f'あなたはAI Companyの{role}。オーナーは市場調査だけを承認し、事業化は保留している。'
        '初期予算10万円、6か月後に月利益10万円が目標。オンライン事業のみ。'
        '事実と仮説を厳密に区別し、Web調査した事実には元URLと確認日を添える。'
        '実際に確認できなかった数値・市場規模・料金・需要を創作しない。'
        '外部公開、投稿、送信、購入、契約、登録などの実行は禁止。'
        '日本語で具体的に、根拠の弱さと反証可能な検証条件も示す。'
    ), input=task, max_output_tokens=MAX_OUTPUT_TOKENS)
    if web:
        args['tools'] = [{'type': 'web_search_preview'}]
        args['tool_choice'] = 'required'
    response = client.responses.create(**args)
    text = response.output_text.strip()
    if not text:
        raise RuntimeError(f'{role}: 応答が空です')
    used_web = any(getattr(item, 'type', None) == 'web_search_call' for item in response.output)
    if web and not used_web:
        raise RuntimeError(f'{role}: Web検索の実行を確認できないため中止しました')
    usage = getattr(response, 'usage', None)
    return text, getattr(usage, 'input_tokens', None), getattr(usage, 'output_tokens', None)


def main():
    if os.getenv('RUN_RESEARCH') != '1':
        print('安全停止: RUN_RESEARCH=1 の場合だけ市場調査を1回実行します。', flush=True)
        return
    for k in ('OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'):
        if not os.getenv(k):
            raise RuntimeError(f'{k} が未設定です')
    # A one-shot token in a persistent DB prevents restart loops from repeating paid calls.
    # The operator must create a unique run token for each explicitly approved run.
    token = os.getenv('RESEARCH_RUN_ID', '').strip()
    if not token or len(token) > 80 or not all(c.isalnum() or c in '-_' for c in token):
        raise RuntimeError('RESEARCH_RUN_ID に一意な英数字・ハイフン・アンダースコアの実行IDを設定してください')
    # Use a PostgreSQL unique index on approvals.action, created by setup_v03.sql.
    # Reserve run before any chargeable API call. A failed run remains reserved intentionally.
    sb('approvals', {'action': f'research_run:{token}', 'status': 'approved', 'decided_at': datetime.now(timezone.utc).isoformat()})
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=120, max_retries=1)
    print('CSO: Webで競合・需要を調査中...', flush=True)
    cso, a, b = ask(client, 'CSO', 'ニッチ特化メルマガ（ニュースレター）事業の競合例を3件、無料/有料の違い、公式価格・機能・日付付きURLを調べる。日本向け候補ニッチ3分野の需要を示す代理指標と反証も探す。未確認事項は未確認と書く。', web=True)
    print('CMO: 集客経路を調査中...', flush=True)
    cmo, c, d = ask(client, 'CMO', f'以下の競合調査を踏まえ、メルマガ登録獲得の具体的経路、各経路の利用規約や実行上の注意、2週間の無料検証計画を提案。根拠URLを調査。\n{cso[:7000]}', web=True)
    print('CFO: 収益モデルを評価中...', flush=True)
    cfo, e, f = ask(client, 'CFO', f'月利益10万円に必要な有料会員数を月額500/980/1980円の3ケースで計算。手数料は未確認なら仮定を明示し、配信サービスの料金は公式情報をWeb調査してURLを記す。初期費用は原則0円で検証、撤退基準を提案。\n{cso[:5000]}', web=True)
    print('COO: 市場調査報告を統合中...', flush=True)
    coo, g, h = ask(client, 'COO', f'市場調査の結果からメルマガ案を継続調査/ピボット/中止のいずれかで提案。根拠URL、競合、未検証事項、14日間の無料調査計画、次にオーナー承認が必要な事項を明示。事業開始は承認されていない。\nCSO:\n{cso[:6000]}\nCMO:\n{cmo[:6000]}\nCFO:\n{cfo[:6000]}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    title = f'AI市場調査 {stamp} UTC / run {token}'
    report = '\n\n'.join([f'# {title}', f'## CSO\n{cso}', f'## CMO\n{cmo}', f'## CFO\n{cfo}', f'## COO\n{coo}'])
    Path('outputs').mkdir(exist_ok=True)
    p = Path('outputs') / f'research_{stamp}.md'
    p.write_text(report, encoding='utf-8')
    print('Supabase: 市場調査レポートを保存中...', flush=True)
    meeting = sb('meetings', {'title': title, 'content': report, 'status': 'completed'})
    sb('business_ideas', {'meeting_id': meeting['id'], 'name': 'ニッチ特化型メルマガ（市場調査のみ）', 'description': coo, 'status': 'research_only'})
    for role, inp, out in [('CSO', a, b), ('CMO', c, d), ('CFO', e, f), ('COO', g, h)]:
        sb('execution_logs', {'agent_id': ROLES[role], 'message': f'{title} | {role} | input_tokens={inp} output_tokens={out}'})
    print(f'完了: {p}', flush=True)
    print(f'Supabase meetings.id: {meeting["id"]}', flush=True)
    print('注意: Web検索の費用を含む実料金はOpenAI Platformで確認してください。', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'エラー: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
