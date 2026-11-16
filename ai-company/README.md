# AI Company v0.2

Railway上で5人のAIエージェントによる経営会議を**1回**実行し、Supabaseに議事録・推奨案・実行履歴を保存する最小版です。Web検索や外部サービスの操作はしません。CPO/CMO/CFOは**順次**評価します。オーナー承認機能、Web画面、定期実行、費用の実額計算は未実装です。

## 必要なRailway Variables

- `OPENAI_API_KEY`（OpenAI API秘密鍵）
- `OPENAI_MODEL`（任意、初期値 `gpt-4.1-mini`）
- `SUPABASE_URL`（Project URL）
- `SUPABASE_SERVICE_ROLE_KEY`（サーバー専用Secret keyまたはLegacy service_role）
- `MAX_OUTPUT_TOKENS`（任意、初期値1300）

鍵はGitHubに保存しないでください。

## 前提SQL

Supabaseに `agents`, `meetings`, `business_ideas`, `tasks`, `approvals`, `execution_logs` の6テーブルが存在し、`agents` に `AG-01`〜`AG-05` が登録されていること。以前の初期SQLに対応しています。

## GitHubへの反映

既存のRailway Root Directoryが `/ai-company` の場合、GitHubの **`ai-company/` フォルダ内**にこのZIPの `main.py`, `requirements.txt`, `.gitignore`, `README.md` を配置してください。GitHubのルートに置くとRailwayは読み込みません。既存の `main.py` は上書きします。既存のプログラムの内容は未確認のため、この版は既存v0.1への差分ではなく**独立した置換版**です。

RailwayのStart Commandは `python main.py`。設定変更後に再デプロイ。これはワンショット実行なので、正常終了しても常時稼働のWebサービスにはなりません。RailwayのUI上の状態表示よりDeploy Logsの `Supabase meetings.id:` とSupabase Table Editorの実データを確認してください。自動再起動が有効なサービスでは繰り返し実行される可能性があるため、意図しない再起動や再デプロイに注意してください。

## 確認

Supabase > Table Editor > `meetings` に1行、`business_ideas` に1行、`execution_logs` に5行が追加されます。エラー時には途中まで書き込まれる場合があります。実行のたびにAPI費用が発生します。

## 制約

- AIの市場評価は**未検証の仮説**です。Web検索機能はありません。
- `business_ideas.name` は暫定名で、詳細な事業案は `description` と議事録にあります。
- `execution_logs.cost_usd` は未記録です（実費を推定しないため）。
- データベース書き込みはトランザクションではありません。途中失敗時は一部のみ保存されます。
- Secret keyはサーバーからのみ使用。公開フロントエンドに渡さないでください。
