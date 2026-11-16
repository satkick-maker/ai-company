"""AI Company v0.1: five-role, human-approved business discovery."""
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from agents import Agent, Runner

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
RULES = """共通条件: 初期予算10万円以内、オンライン完結、6か月以内の月商10万円を目標とする（保証ではない）。
調査結果の出典を捏造しない。ライブWeb検索機能はないため、需要や競合に関する未検証の推測は仮説と明記する。
顧客への連絡、公開、契約、課金、広告出稿、購入、外部サービス操作を行わない。
日本語で簡潔かつ具体的に回答する。"""

def agent(name, role):
    return Agent(name=name, instructions=f"あなたはAI Companyの{role}。{RULES}", model=MODEL)

cso = agent("CSO", "戦略責任者。オンライン事業を10案考案し、対象顧客・課題・競争要因・検証方法を整理する")
cpo = agent("CPO", "商品責任者。候補事業のMVP、制作負荷、品質リスク、納品方法を検討する")
cmo = agent("CMO", "マーケティング責任者。顧客獲得チャネル、検証施策、獲得コストの仮説を評価する")
cfo = agent("CFO", "財務責任者。初期費用・月次費用・単価・必要販売数・損益分岐点を仮定付きで試算する")
coo = agent("COO", "執行責任者。各担当の意見を比較し、異論と未検証事項を残して上位3案と承認待ち事項を提示する")

async def ask(who, prompt):
    result = await Runner.run(who, prompt, max_turns=3)
    return result.final_output

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY を設定してください。")
    print("CSO: 事業候補を作成中...")
    strategy = await ask(cso, "事業候補を10件提案。評価基準と検証すべき仮説も記載。")
    print("CPO / CMO / CFO: 独立評価中...")
    evaluations = await asyncio.gather(
        ask(cpo, f"以下の10案を商品実現性の観点から評価。\n{strategy}"),
        ask(cmo, f"以下の10案を集客・販売の観点から評価。\n{strategy}"),
        ask(cfo, f"以下の10案を採算性の観点から評価。予算上限10万円。\n{strategy}"),
    )
    print("COO: 経営会議の結論を作成中...")
    summary = await ask(coo, "次の部門報告を統合して事業上位3案、比較表、優先順位、最初の7日間の検証計画、リスク、オーナー承認待ち事項を作成。実行はしない。\n" +
        "\n\n".join([f"CSO:\n{strategy}"] + [f"{name}:\n{report}" for name, report in zip(["CPO", "CMO", "CFO"], evaluations)]))
    content = "# AI Company v0.1 | 第1回経営会議\n\n" + "\n\n".join(
        [f"## {name}\n\n{body}" for name, body in [("CSO", strategy), ("CPO", evaluations[0]), ("CMO", evaluations[1]), ("CFO", evaluations[2]), ("COO 最終提案", summary)]]
    )
    folder = Path("outputs")
    folder.mkdir(exist_ok=True)
    path = folder / ("meeting_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".md")
    path.write_text(content, encoding="utf-8")
    print(f"完了: {path}")

if __name__ == "__main__":
    asyncio.run(main())
