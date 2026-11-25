# second-brain-kit

給 Claude 一個筆記資料夾、一份記著還沒做完的事的追蹤表和安全檢查，讓它換了對話也記得你的事，並且從你的糾正中學習。**不用會寫程式**：在 Claude 桌面版 App 的 **Code** 分頁或終端機裡都能用。[English](README.md)

## 你會得到什麼

![裝好之後你得到什麼：你只跟一個 Claude 對話說話；安全檢查在旁邊看著；它有筆記資料夾、記著還沒做完的事的追蹤表，以及記你糾正過什麼的筆記](docs/diagrams/readme/a-what-you-get.zh.png)

換了新對話也找得回你的筆記、沒做完的事有人幫你記、Claude 會學你喜歡的做法。

## 三步驟安裝

![三步驟安裝：打開 Claude Code、貼上一句話、回答 6 個問題](docs/diagrams/readme/b-install.zh.png)

大約 15～30 分鐘，大部分時間是 Claude 自己在做；你回答 6 個問題、按幾次同意。

第 2 步要貼的那一句：

```
請從 https://github.com/0Smallcat0/second-brain-kit 安裝 second-brain-kit，照 docs/SETUP.md 幫我設定，用繁體中文跟我說話。我只有一個 Claude 帳號。
```

想自己打指令？在 Claude Code 2.1.275 以上：`/plugin install second-brain-kit --marketplace 0Smallcat0/second-brain-kit`，再輸入 `/sbk-setup`。其他方式：[安裝細節](docs/zh-TW/安裝.md)。

## 基本款還是完整款

![基本款：一個對話，管筆記和追蹤表。完整款：入口對話、每件事一個對話、系統維護和提醒](docs/diagrams/readme/c-basic-vs-full.zh.png)

| | 基本款 | 完整款 |
|---|---|---|
| 對話 | 一個，在你的筆記資料夾裡 | 你說話的入口、每件事一個對話、系統維護對話 |
| 提醒 | 沒有 | 每週檢視、期限、你自己加的 |
| 外部資源 | 不用 | 只用你安裝時勾的 |
| 適合 | 剛開始用；同時幾件事 | 好幾件事常被搞混、常忘記期限 |

基本款一定會裝；完整款每一項之後各自再開。每一項並排比較：[進階功能.md](docs/zh-TW/進階功能.md#基本款和完整款)。

## 它怎麼學

![它怎麼學：你糾正它、Claude 記一行、每週整理、你說好、下個對話照著做](docs/diagrams/readme/d-how-it-learns.zh.png)

你每次糾正它或說它做對了，Claude 就記一行。你沒說好之前，什麼都不會變成偏好。

## 每天怎麼用

用你平常的說法講就好：

- 「把這個記進我的筆記。」
- 「我還有什麼沒做完？」
- 「記住：我喜歡這樣做。」

## 費用與方案

- **費用：** 這套工具免費，和一般對話一樣用你的 Claude 方案。
- **需要的方案：** 有 Claude Code 的付費方案（Pro、Max、Ultra、Team、Enterprise）或 Console 帳號，另外要有 [Python 3](https://www.python.org/downloads/)（免費）。免費的 claude.ai 方案和網頁聊天用不了。
## 安全與資料

- **有風險的事先問你：** 要推上遠端、刪掉整個資料夾、丟掉 git 裡的工作、跳過 git 檢查、改受保護的規則檔，或把一張筆記砍到剩一小部分之前。
- **全部留在你的電腦上：** 筆記是你選的資料夾裡的一般文字檔，這套工具不上傳任何東西（Claude 本身照常是線上服務）。
- **git 的修改紀錄不是備份：** 請不時把筆記資料夾複製到另一顆硬碟或你信任的雲端硬碟。

## 更多

[使用指南](docs/zh-TW/指南.md) · [安全與資料](docs/zh-TW/安全與資料.md) · [常見問題與費用](docs/zh-TW/常見問題.md) · [安裝細節與手動安裝](docs/zh-TW/安裝.md) · [運作原理](docs/zh-TW/運作原理.md) · [完整款](docs/zh-TW/進階功能.md) · [踩過的坑](docs/zh-TW/踩過的坑.md)

## 授權

MIT，見 [LICENSE](LICENSE)。使用者自己做的，不是 Anthropic 官方的外掛。
