"""AI Company v0.4 phase 1: authenticated, read-only owner dashboard."""
import hmac
import math
import os
from datetime import datetime
from urllib.parse import quote
import requests
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


require_login()
with st.sidebar:
    st.title('🏢 AI Company')
    page = st.radio('メニュー', ['概要', '経営会議・市場調査', '財務シミュレーション', '調査品質チェック'])
    if st.button('ログアウト'):
        st.session_state.authenticated = False
        st.rerun()
    st.caption('v0.4 Phase 1 / 閲覧専用')

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
else:
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
