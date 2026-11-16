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


require_login()
with st.sidebar:
    st.title('🏢 AI Company')
    page = st.radio('メニュー', ['概要', '経営会議・市場調査', '財務シミュレーション', '調査品質チェック', 'オーナー判断'])
    if st.button('ログアウト'):
        st.session_state.authenticated = False
        st.rerun()
    st.caption('v0.4 Phase 2 / 判断記録のみ・自動実行なし')

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

else:
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
            if not proposal.strip():
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
