"""AI Company v0.4 phase 2: authenticated owner dashboard and decision records."""
import hmac
import math
import os
from datetime import datetime
from urllib.parse import quote
import requests
import uuid
import streamlit as st

st.set_page_config(page_title='AI Company | Owner Console', page_icon='🏢', layout='wide')


def require_login():
    secret = os.getenv('OWNER_DASHBOARD_PASSWORD', '')
    if len(secret) < 16:
        st.error('OWNER_DASHBOARD_PASSWORD（16文字以上）が未設定です。')
        st.stop()
    if not st.session_state.get('authenticated'):
        st.title('AI Company | Owner Console')
        with st.form('login'):
            pw = st.text_input('オーナーパスワード', type='password')
            submitted = st.form_submit_button('ログイン')
        if submitted:
            if hmac.compare_digest(pw.encode(), secret.encode()):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error('パスワードが違います。')
        st.stop()


def fetch(table, columns='*', limit=20):
    base = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not base.startswith('https://') or not base.endswith('.supabase.co') or not key:
        raise RuntimeError('SUPABASE_URL または SUPABASE_SERVICE_ROLE_KEY が未設定です。')
    res = requests.get(
        f'{base}/rest/v1/{quote(table, safe="")}',
        params={'select': columns, 'order': 'created_at.desc', 'limit': str(limit)},
        headers={'apikey': key, 'Authorization': f'Bearer {key}'}, timeout=15)
    res.raise_for_status()
    return res.json()


def create_decision(title, description, decision, comment):
    base = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not base.startswith('https://') or not base.endswith('.supabase.co') or not key:
        raise RuntimeError('Supabase接続設定を確認してください。')
    payload = {
        'id': str(uuid.uuid4()),
        'proposal_title': title,
        'proposal_description': description,
        'decision': decision,
        'owner_comment': comment or None,
        'decided_at': datetime.now().astimezone().isoformat(),
    }
    response = requests.post(
        f'{base}/rest/v1/owner_decisions', json=payload,
        headers={'apikey': key, 'Authorization': f'Bearer {key}',
                 'Prefer': 'return=representation'}, timeout=15)
    response.raise_for_status()
    return response.json()



def update_request_decision(request_id, decision, comment):
    base = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not base.startswith('https://') or not base.endswith('.supabase.co') or not key:
        raise RuntimeError('Supabase接続設定を確認してください。')
    headers = {'apikey': key, 'Authorization': f'Bearer {key}', 'Prefer': 'return=representation'}
    response = requests.patch(
        f'{base}/rest/v1/approval_requests',
        params={'id': f'eq.{request_id}', 'status': 'eq.pending'},
        json={'status': decision, 'owner_comment': comment or None,
              'decided_at': datetime.now().astimezone().isoformat()},
        headers=headers, timeout=15)
    response.raise_for_status()
    if len(response.json()) != 1:
        raise RuntimeError('すでに判断済み、または申請が見つかりません。画面を更新してください。')


require_login()
with st.sidebar:
    st.title('🏢 AI Company')
    page = st.radio('メニュー', ['概要', '経営会議・市場調査', '財務シミュレーション', '調査品質チェック', 'オーナー判断', 'AI承認申請', '経営会議を開催'])
    if st.button('ログアウト'):
        st.session_state.authenticated = False
        st.rerun()
    st.caption('v0.6 / 会議開催は明示操作のみ・外部実行なし')

st.title(page)
if page in ('概要', '経営会議・市場調査', '調査品質チェック'):
    try:
        meetings = fetch('meetings', 'id,title,content,status,created_at', 30)
    except Exception as exc:
        st.error(f'Supabaseの読み取りに失敗しました: {exc}')
        st.stop()
    if page == '概要':
        c1, c2, c3 = st.columns(3)
        c1.metric('取得した議事録', len(meetings))
        c2.metric('市場調査', sum('市場調査' in (m.get('title') or '') for m in meetings))
        c3.metric('事業化', '未承認')
        st.info('事業化・公開・支出・契約は未承認です。この画面から実行できません。')
        if meetings:
            st.subheader('最新のレポート')
            st.write(meetings[0].get('title', ''))
            st.caption(meetings[0].get('created_at', ''))
            st.markdown(meetings[0].get('content') or '本文なし')
    elif page == '経営会議・市場調査':
        if not meetings:
            st.info('レポートはありません。')
        else:
            chosen = st.selectbox('レポートを選択', range(len(meetings)),
                format_func=lambda i: (meetings[i].get('title') or meetings[i]['id']))
            m = meetings[chosen]
            st.caption(f"ID: {m['id']} | {m.get('created_at', '')} | {m.get('status', '')}")
            st.markdown(m.get('content') or '本文なし')
    else:
        if not meetings:
            st.info('評価対象がありません。')
        else:
            chosen = st.selectbox('レポートを選択', range(len(meetings)),
                format_func=lambda i: (meetings[i].get('title') or meetings[i]['id']))
            content = meetings[chosen].get('content') or ''
            checks = {
                'URLが含まれる': 'https://' in content,
                '未検証事項が明示されている': ('未検証' in content or '未確認' in content),
                '反証または撤退条件がある': ('反証' in content or '撤退' in content),
                '価格・費用に言及している': ('円' in content or '料金' in content),
            }
            for name, ok in checks.items():
                st.write(('✅ ' if ok else '⚠️ ') + name)
            st.warning('これは文字列の有無を確認する簡易チェックです。URLの実在性・出典の妥当性・数値の正確性は検証していません。')
elif page == '財務シミュレーション':
    st.caption('固定費・決済手数料のみを考慮した簡易試算。初期費用・人件費・税金・返金等は別途考慮が必要です。')
    profit = st.number_input('月間目標利益（円）', min_value=0, value=100000, step=10000)
    fixed = st.number_input('月額固定費（円）', min_value=0, value=3000, step=1000)
    fee = st.number_input('売上に対する決済手数料（%）', min_value=0.0, max_value=99.0, value=5.0, step=0.5)
    rows = []
    for price in (500, 980, 1980):
        net = price * (1 - fee / 100)
        count = math.ceil((profit + fixed) / net)
        rows.append({'月額料金（円）': price, '必要会員数（人）': count, '月間売上（円）': price * count,
                     '概算月間利益（円）': round(price * count * (1 - fee / 100) - fixed)})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.code('必要会員数 = ceil((目標月利益 + 月額固定費) / (会費 × (1 − 決済手数料率)))')

elif page == 'オーナー判断':
    st.info('ここでの承認は判断の記録のみです。AIへの指示、Web公開、購入、契約、外部送信は実行されません。')
    try:
        meetings = fetch('meetings', 'id,title,content,status,created_at', 30)
        decisions = fetch('owner_decisions', 'id,proposal_title,proposal_description,decision,owner_comment,created_at,decided_at', 100)
    except Exception as exc:
        st.error(f'Supabaseの読み取りに失敗しました: {exc}')
        st.stop()
    st.subheader('提案に対する判断を記録')
    if not meetings:
        st.warning('対象となるレポートがありません。')
    else:
        chosen = st.selectbox('対象レポート', range(len(meetings)),
            format_func=lambda i: (meetings[i].get('title') or meetings[i]['id']))
        selected = meetings[chosen]
        with st.expander('レポートの内容を確認'):
            st.markdown(selected.get('content') or '本文なし')
        with st.form('owner_decision_form', clear_on_submit=False):
            proposal = st.text_input('判断対象の提案名', value='ニッチ特化型メルマガ事業')
            decision = st.radio('判断', ['needs_research', 'approved', 'rejected'],
                format_func=lambda x: {'needs_research': '再調査', 'approved': '承認（記録のみ）', 'rejected': '却下'}[x])
            comment = st.text_area('判断理由・追加指示（任意）', height=100)
            confirm = st.checkbox('これは判断の記録のみで、外部への実行を許可する操作ではないことを確認しました')
            submitted = st.form_submit_button('判断を保存')
        if submitted:
            if not confirm:
                st.error('確認チェックを入れてください。')
            elif not proposal.strip():
                st.error('提案名を入力してください。')
            else:
                try:
                    create_decision(proposal.strip(), f"source_meeting_id={selected['id']}", decision, comment.strip())
                    st.success('オーナー判断を保存しました。外部処理は実行していません。')
                    st.rerun()
                except Exception as exc:
                    st.error(f'判断の保存に失敗しました: {exc}')
    st.subheader('判断履歴')
    if not decisions:
        st.caption('判断履歴はまだありません。')
    else:
        st.dataframe([{
            '日時': d.get('decided_at') or d.get('created_at'),
            '提案': d.get('proposal_title'),
            '判断': {'approved': '承認', 'rejected': '却下', 'needs_research': '再調査', 'pending': '保留'}.get(d.get('decision'), d.get('decision')),
            'コメント': d.get('owner_comment') or '',
            '関連情報': d.get('proposal_description') or ''
        } for d in decisions], use_container_width=True, hide_index=True)


if page == 'AI承認申請':
    st.info('AI社員が作成した申請を確認し、判断を記録します。承認しても業務は実行されません。')
    try:
        requests_data = fetch('approval_requests', 'id,source_meeting_id,request_type,requested_by,title,description,estimated_cost_yen,external_action,status,owner_comment,created_at,decided_at', 100)
    except Exception as exc:
        st.error(f'承認申請の取得に失敗しました。setup_v05.sqlの実行を確認してください: {exc}')
        st.stop()
    pending = [r for r in requests_data if r.get('status') == 'pending']
    st.metric('承認待ち', len(pending))
    if not pending:
        st.caption('承認待ちの申請はありません。申請生成プログラムは明示的に実行するまで動きません。')
    for r in pending:
        with st.expander(f"{r['title']} | {r.get('requested_by','COO')}"):
            st.write(r.get('description') or '')
            st.write(f"想定追加費用: {r.get('estimated_cost_yen',0)}円（API従量料金は別途）")
            st.write(f"外部操作: {'あり（実行不可）' if r.get('external_action') else 'なし'}")
            with st.form('request_' + r['id']):
                decision = st.radio('判断', ['needs_research','approved','rejected'],
                    format_func=lambda v: {'needs_research':'再調査','approved':'承認（記録のみ）','rejected':'却下'}[v], key='choice_'+r['id'])
                comment = st.text_area('判断理由', key='comment_'+r['id'])
                confirm = st.checkbox('判断の記録のみであり、自動実行されないことを確認しました', key='confirm_'+r['id'])
                submit = st.form_submit_button('判断を保存')
            if submit:
                if not confirm:
                    st.error('確認チェックを入れてください。')
                else:
                    try:
                        update_request_decision(r['id'], decision, comment)
                        st.success('判断を保存しました。外部処理は実行していません。')
                        st.rerun()
                    except Exception as exc:
                        st.error(f'保存失敗: {exc}')
    st.subheader('申請履歴')
    if requests_data:
        st.dataframe([{'申請日時':r.get('created_at'), '提案':r.get('title'),
            '申請者':r.get('requested_by'), '状態':r.get('status'),
            '判断理由':r.get('owner_comment') or ''} for r in requests_data],
            hide_index=True, use_container_width=True)


if page == '経営会議を開催':
    st.info('この画面からAI社員5名の会議を1回開催します。API従量料金が発生します。Web検索、投稿、購入、契約、外部送信は行いません。')
    st.warning('処理中はブラウザを閉じたり再読み込みしたりしないでください。会議は数分かかる場合があります。')
    try:
        recent_meetings = fetch('meetings', 'id,title,content,status,created_at', 10)
        prior_requests = fetch('approval_requests', 'id,title,description,status,owner_comment,created_at', 20)
    except Exception as exc:
        st.error(f'履歴取得に失敗しました: {exc}')
        st.stop()
    with st.form('new_meeting_form'):
        agenda = st.text_area('議題', value='ニッチ特化型メルマガ事業の14日間無料登録獲得テストについて、オーナーの再調査指示を踏まえ、外部公開前の実施計画を具体化する。', height=110)
        use_feedback = st.checkbox('直近のオーナー判断・追加指示を会議に含める', value=True)
        consent = st.checkbox('API従量料金が発生すること、会議は内部検討のみで外部操作しないことを確認しました')
        start = st.form_submit_button('経営会議を1回開催', type='primary')
    if start:
        if not consent:
            st.error('費用と実行範囲の確認にチェックしてください。')
        elif not agenda.strip() or len(agenda) > 1500:
            st.error('議題は1〜1500文字で入力してください。')
        elif not os.getenv('OPENAI_API_KEY'):
            st.error('DashboardサービスのVariablesにOPENAI_API_KEYを設定してください。')
        else:
            import json
            from openai import OpenAI
            api_base = os.environ['SUPABASE_URL'].strip().rstrip('/')
            api_key = os.environ['SUPABASE_SERVICE_ROLE_KEY'].strip()
            headers = {'apikey': api_key, 'Authorization': f'Bearer {api_key}', 'Prefer': 'return=representation'}
            run_id = str(uuid.uuid4())
            payload = {'id': run_id, 'agenda': agenda.strip(), 'status': 'running'}
            try:
                claim = requests.post(f'{api_base}/rest/v1/meeting_runs', headers=headers, json=payload, timeout=20)
                claim.raise_for_status()
            except Exception as exc:
                st.error(f'会議開始記録を保存できませんでした。APIは呼び出していません: {exc}')
                st.stop()
            try:
                feedback = ''
                if use_feedback:
                    relevant = [r for r in prior_requests if r.get('owner_comment') and r.get('status') != 'pending'][:5]
                    feedback = '\n'.join(f"申請: {r['title']} / 判断: {r['status']} / オーナー指示: {r['owner_comment']}" for r in relevant)
                client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=90, max_retries=0)
                model = os.getenv('MEETING_MODEL', 'gpt-4.1-mini')
                policy = ('あなたはAI Companyの社内AI社員。日本語で簡潔かつ具体的に答える。'
                          '初期予算10万円、6か月後に月利益10万円を目標とするオンライン事業。'
                          'この会議は内部検討のみ。公開、SNS投稿、送信、購入、契約、広告出稿、ユーザー募集、実際の調査実行は禁止。'
                          'Web検索は使えない。最新情報・出典・数値は確認できなければ未確認と明示する。'
                          '仮説と事実を分け、費用上限と承認が必要な操作を明記する。')
                roles = [
                    ('CSO','市場・競合・ターゲット・検証仮説'),
                    ('CPO','提供価値・商品仕様・登録体験'),
                    ('CMO','集客計画・測定方法・外部公開の承認境界'),
                    ('CFO','予算・採算・KPI・撤退条件'),
                    ('COO','全員の意見を統合し、矛盾点、次の社内作業、オーナー承認が必要な事項を整理')]
                outputs = {}
                with st.spinner('AI社員5名が順番に検討しています。完了までお待ちください…'):
                    for role, responsibility in roles:
                        context = '\n'.join(f'{k}: {v[:2400]}' for k,v in outputs.items())
                        prompt = f'議題: {agenda.strip()}\nオーナーの過去の指示:\n{feedback[:6000] or "なし"}\n他のAI社員の意見:\n{context[:10000] or "なし"}\n担当: {responsibility}\n担当者としての見解を示してください。'
                        resp = client.responses.create(model=model, instructions=policy + f' あなたの役職は{role}。', input=prompt, max_output_tokens=1100)
                        answer = (resp.output_text or '').strip()
                        if not answer:
                            raise RuntimeError(f'{role}の応答が空でした')
                        outputs[role] = answer
                stamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')
                title = f'AI経営会議 {stamp} / {agenda.strip()[:60]}'
                report = '# ' + title + '\n\n## 議題\n' + agenda.strip() + '\n\n## 参照したオーナー指示\n' + (feedback or 'なし') + '\n\n' + '\n\n'.join(f'## {role}\n{value}' for role,value in outputs.items())
                saved = requests.post(f'{api_base}/rest/v1/meetings', headers=headers, json={'title':title,'content':report,'status':'completed'}, timeout=20)
                saved.raise_for_status()
                data = saved.json()
                meeting_id = data[0]['id']
                finished = requests.patch(f'{api_base}/rest/v1/meeting_runs', params={'id':f'eq.{run_id}'}, headers=headers, json={'status':'completed','meeting_id':meeting_id,'finished_at':datetime.now().astimezone().isoformat()}, timeout=20)
                finished.raise_for_status()
                st.success('経営会議が完了し、議事録を保存しました。')
                st.markdown(report)
            except Exception as exc:
                try:
                    requests.patch(f'{api_base}/rest/v1/meeting_runs', params={'id':f'eq.{run_id}'}, headers=headers, json={'status':'failed','error_message':str(exc)[:500], 'finished_at':datetime.now().astimezone().isoformat()}, timeout=15)
                except Exception:
                    pass
                st.error(f'会議処理に失敗しました。API呼び出し分の料金が発生している可能性があります: {exc}')
    st.subheader('最近の会議実行')
    try:
        runs = fetch('meeting_runs', 'id,agenda,status,meeting_id,error_message,created_at,finished_at', 15)
        st.dataframe([{'日時':r.get('created_at'),'議題':r.get('agenda'),'状態':r.get('status'),'議事録ID':r.get('meeting_id') or '', 'エラー':r.get('error_message') or ''} for r in runs], hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f'会議実行履歴を取得できません: {exc}')
