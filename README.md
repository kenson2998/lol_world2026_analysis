# LoL Worlds 2026 分析

英雄聯盟 2026 世界賽（Swiss Stage）的單頁報表：16 強選手單排英雄統計、賽事結果與 BP、水晶球 Pick'Em 題目、市場預測與英雄對位。

開啟 [`data/worlds2026_analysis.html`](data/worlds2026_analysis.html)（下載後用瀏覽器開）即可直接看，不需要伺服器。

## 分頁

- **世界賽戰況**：各輪賽果、BP 點線圖（禁用紅框斜線）、每局兩隊各路傷害、目前戰績、選手數據（含搶到／被搶重擊）、英雄出場與勝率
- **水晶球預測**：Pick'Em 18 題目前前三名、市場預測準確度、下一輪賠率、冠軍與晉級機率
- **英雄對位**：同路線英雄對位的勝率、15 分經濟差／補兵差、傷害差
- **選手單排**：16 強先發選手韓服／美服單雙排英雄使用率與勝率

## 更新流程

```sh
# 一輪（或半輪）打完後，資料整理成 JSON 再匯入
python3 -I scripts/worlds_round_update.py data/worlds.json collected.json <round_index>
python3 -I scripts/worlds_player_stats.py data <gol.gg cache dir>
python3 -I scripts/build_report.py data data/rosters.json   # 產生 data/worlds2026_analysis.html（設定 EXPORT_DIR 會另存一份 worlds2026_MMDD.html）
node scripts/smoke_test.js data/worlds2026_soloq.html
```

## 資料來源

賽果與 BP：gol.gg、Liquipedia；選手數據：gol.gg；賠率：Polymarket、Kalshi；模型：Outdrafted；英雄名稱與圖示：Riot Data Dragon；選手頭像：LoL Esports。賠率會變動，僅供參考。
