# AI Company v0.1

5人の役割別AIエージェントがオンライン事業の候補を検討し、オーナーに提案する最小構成です。**自動で契約・購入・投稿・送信・販売はしません。** ライブWeb検索、共通DB、定期実行、管理画面は未実装です。

## ローカルで実行

Python 3.11以降を使用します。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='ご自身のAPIキー'
python main.py
```

実行後、`outputs/meeting_*.md` に経営会議の議事録が保存されます。`outputs/` はGit管理から除外しています。API利用には別途課金が発生します。実行前にOpenAI APIの利用上限・通知を設定してください。APIキーはGitHubに登録しないでください。

## Railway

このv0.1は**一度実行して終了するバッチ処理**です。RailwayではGitHubリポジトリを接続し、環境変数 `OPENAI_API_KEY` を登録して、Start Commandを `python main.py` に設定できます。ただしRailwayのコンテナ内の`outputs/`は永続保存を保証しません。まずローカル実行で動作を確認し、次の版でSupabaseへの永続保存と定期実行を追加してください。常時稼働するWebアプリではありません。
