# SETUP：給負責配置的 Claude 看的步驟

這份是寫給**你，Claude** 的，不是給使用者的。使用者請你把 second-brain-kit 這套工作方式裝好。他不一定懂技術：事情由你做，他只回答幾個問題、並批准會改系統的步驟。照順序做；每一步做完就跑它的 **檢查**，過了才往下。檢查沒過，先找出原因修好再重跑，不可以跳過，也不可以對使用者說某一步完成了、而你其實沒檢查過。

名詞：
- `KIT`：這個檔案所在位置往上一層的資料夾（裡面有 `.claude-plugin/plugin.json`）。
- `SBK_HOME`：`~/.claude/sbk`（執行用的資料夾：帳本、鬧鐘、路由、收件匣、紀錄、各個 task.md）。
- `VAULT`：使用者選的筆記資料夾（預設 `~/second-brain`）。
- Windows 上路徑用斜線或加引號。Python 用 3 版（`python3`、`python` 或 `py`，哪個能跑用哪個）。

工作規則：要改 `~/.claude/settings.json`、`~/.claude/CLAUDE.md`、系統排程、或使用者任何既有檔案之前，先問。不覆蓋既有檔案，先給他看差異、得到同意。這裡沒有任何東西會被推上遠端或寄給別人。

---

## 步驟 00：取得套件（`KIT` 已經在電腦上就跳過）

使用者可能只貼了這一句：「Install the Claude Code plugin from https://github.com/0Smallcat0/second-brain-kit and set me up by its docs/SETUP.md.」如果這台電腦上還沒有 `KIT`（裡面有 `.claude-plugin/plugin.json` 的資料夾）：
1. 先問一次：「同意我從 github.com/0Smallcat0/second-brain-kit 加入 second-brain-kit 外掛嗎？這會改你的 Claude Code 外掛清單。」同意後執行 `claude plugin marketplace add 0Smallcat0/second-brain-kit`，再執行 `claude plugin install second-brain-kit@second-brain-kit`（就是 `/plugin marketplace add ...` 和 `/plugin install ...` 的命令列版本）。
2. 如果這裡跑不了 `claude` 指令、或安裝失敗，就把 `https://github.com/0Smallcat0/second-brain-kit` clone 到一個新資料夾（例如 `~/second-brain-kit-src`），拿它當 `KIT`；hook 改走步驟 4 的手動安裝。
3. 從 `KIT` 重新讀一次 `docs/zh-TW/SETUP.md`（就是這份），接著做步驟 0。

**檢查：** `KIT/.claude-plugin/plugin.json` 存在，而且 `claude plugin list` 看得到 second-brain-kit（clone 路線則是資料夾存在，並且你說了用的是這條路線）。

---

## 步驟 0：環境檢查與提問

1. 執行 `python --version`、`git --version`、`claude --version`。需要 Python 3.8 以上和 git。缺哪個，就明確告訴使用者要裝什麼（只有他能裝），然後在這裡停下。
2. 用**一則訊息**問下面這些問題，等他回答。每個工具預設都是「沒有」：一個 Claude 帳號就夠。
   1. 你有**第二個 Claude 帳號**嗎？（自己另外付費的第二個訂閱，或你被允許使用的家人／朋友方案）
   2. 你有 **ChatGPT** 嗎？要不要用 **Codex CLI**？
   3. 你有用 **Gemini** 嗎？（網頁、Antigravity、或 API 金鑰）
   4. 你有 **Google Colab**、或有 **GPU** 的電腦可以跑重的工作嗎？
   5. 你有用 **OpenRouter**（免費模型）嗎？
   6. 筆記庫要放哪裡？（建議 `~/second-brain`）
   7. 筆記和回覆用哪種語言？
   8. 你最常用 Claude 處理的**兩個領域**是什麼？（例如讀書和打工）它們會變成最先開的兩個主題對話。
3. 建立 `SBK_HOME`，寫 `SBK_HOME/config.json`：
   `{"vault": "<VAULT 絕對路徑>", "language": "<語言>", "tools": {"second_claude": false, "codex": false, "gemini": false, "colab_gpu": false, "openrouter": false}, "modes": {}}`，使用者說有的工具才填 `true`。

**檢查：** `python -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude/sbk/config.json')))['tools'])"` 印出的工具答案，和他回答的一致。

## 步驟 1：安裝命令列工具

1. 建立 `SBK_HOME/{bin,hooks,managers,inbox,logs,state,entry}`。
2. 把 `KIT/entry/` 的 `ledger.py`、`send.py`、`alarm.py`、`status.py`、`worker.ps1`、`worker.sh` 複製到 `SBK_HOME/bin/`。（一律複製，不要依賴外掛快取的路徑：外掛更新時它會變。更新後要再複製一次。）

**檢查：** `python SBK_HOME/bin/ledger.py add "setup check"` 印出 `L0001`；接著 `python SBK_HOME/bin/ledger.py done L0001 --evidence "setup step 1 check ran"` 印出 `L0001 done`；`ledger.py list` 印出 `nothing open`。

## 步驟 2：原則（`CLAUDE.md`）

1. 讀 `KIT/templates/CLAUDE.md`。使用者的語言不是繁體中文時，忠實翻譯（保持結構和意思，維持在 100 行內）。
2. `~/.claude/CLAUDE.md` 不存在就用這份內容建立。已存在就先給使用者看你要加什麼，同意後附加在 `<!-- sbk:begin -->` 和 `<!-- sbk:end -->` 兩行之間。不刪、不調動他原本的文字。

**檢查：** 檔案裡有兩個標記；兩個標記之間少於 100 行。

## 步驟 3：筆記庫

1. 依 `KIT/templates/筆記格式.md` 第 1 節建立 `VAULT` 的區和類別資料夾（使用者想要的話才翻譯資料夾名稱；`NN-NN`／`NN` 的編號要保留）。
2. 複製進庫，並把 `{{date}}` 換成今天（`YYYY-MM-DD`）：
   - `templates/AGENTS.md` → `VAULT/AGENTS.md`；另外 `VAULT/CLAUDE.md` 內容只有一行：`@AGENTS.md`
   - `templates/筆記格式.md` → `VAULT/00-09 系統與索引/01 規則/01-01 筆記格式.md`
   - `templates/todo-for-me.md` → `VAULT/00-09 系統與索引/02 收件匣/02-02 我要做的事.md`
   - 收件匣筆記 `VAULT/00-09 系統與索引/02 收件匣/02-01 收件匣.md`：frontmatter 要合法（`type: log`、`status: active`、一句 summary、今天的日期、`origin: agent-drafted`），內文一行「還沒歸位的東西先放這裡。」
   - `templates/sbk-protect.txt` → `VAULT/.sbk-protect`；空檔案 `VAULT/.sbk-vault`
   - `KIT/scripts/{vault_lint.py,gen_jdex.py,check_overwrite.py,pre-commit}` → `VAULT/scripts/`；macOS／Linux 要 `chmod +x VAULT/scripts/pre-commit`。
3. 使用者要別的語言就翻譯複製進去的中文筆記（欄位名稱與值，例如 `type: skill`，要原樣保留，lint 依賴它們）。
4. `python VAULT/scripts/gen_jdex.py --root VAULT` 產生索引。
5. 在 `VAULT` 執行 `git init`；`git config user.name` 是空的就問使用者名字和 email，只設在這個庫。`git config core.hooksPath scripts`。依檔名 add，做第一個提交 "Initial vault"。
6. 選擇性（得到同意才做）：用五個簡短問題訪問使用者（念什麼或做什麼、目前的目標、喜歡怎樣的回覆、AI 哪裡最讓他煩），用他的原話存成 `VAULT/10-19 自己與生活/11 .../11-01 關於我.md`，`type: profile`、`origin: user`。不要編造事實。

**檢查：** `python VAULT/scripts/vault_lint.py --root VAULT` 結尾是 `RESULT: PASS`；第一個提交存在（`git -C VAULT log --oneline`）；pre-commit 真的會擋：在暫時分支裡把一張筆記大半刪掉再暫存、提交，確認提交被拒絕（然後還原）。沒有被拒絕就先修好 `core.hooksPath` 再往下。

## 步驟 4：防呆 hook

用外掛安裝時，`KIT/hooks/hooks.json` 已經生效；用 `/hooks` 確認列得出 second-brain-kit 的 Stop、PreToolUse、UserPromptSubmit、SessionStart。手動 clone 的情況：把 `KIT/hooks/*.py` 和 `run.sh` 複製到 `SBK_HOME/hooks/`，（因為要改 settings，先得到使用者同意）再把 `KIT/templates/settings.hooks.example.json` 的 `hooks` 區塊合併進 `~/.claude/settings.json`，把 `__KIT__` 換成 `SBK_HOME/hooks` 的路徑。要「合併」，不要取代：他已有的 hook 全部保留。

每個 hook 做什麼（各用一句話告訴使用者）：

| Hook | 作用 | 預設模式 |
|---|---|---|
| `stop_evidence` | 改完東西說「完成」卻沒看過結果：要求補證據，只擋一次 | block once |
| `requests_reinject` | 壓縮後把使用者自己的訊息原文放回來 | warn |
| `read_whole` | 拒絕對庫裡筆記用 `head`／`tail`／`sed -n`；要整張讀 | deny |
| `vault_guard` | git push、`--no-verify`、破壞性 git、大量刪除、改受保護檔案前先問 | ask |
| `usage_warn` | 週用量超過 80% 時提醒一次（不擋） | warn |
| `inbox_notice` | 讓主題對話看到入口交來的事 | warn |

不用改程式就能調模式：`SBK_HOME/config.json` → `"modes": {"stop_evidence": "log"}`（值：off、log、warn、ask、deny、block）。每次判斷也會寫進 `SBK_HOME/logs/<hook>.log`。

**信任之前先重播。** 找使用者最近的對話紀錄（`~/.claude/projects/*/*.jsonl`，最新五份），各跑一次 `python KIT/hooks/stop_evidence.py --replay <檔案>`。被標記的輪次超過約四分之一，代表這個檢查對這位使用者太吵：設成 `"stop_evidence": "log"`，告訴使用者，並安排一週後檢討 `logs/stop_evidence.log`。接著跑 `python KIT/scripts/selftest.py`。

**檢查：** `selftest.py` 印出 `0 failed`；至少對一份對話紀錄跑過重播（或寫明還沒有任何紀錄）。

## 步驟 5：入口與兩個主題對話

1. `SBK_HOME/entry/CLAUDE.md` ← `templates/entry-CLAUDE.md`，`{{vault}}` 換掉。
2. 步驟 0 的兩個領域，各取一個簡短的英文小寫 id（例如 `study`、`work`），建立 `SBK_HOME/managers/<id>/`，把 `templates/manager-CLAUDE.md` 放進去當 `CLAUDE.md`（`{{manager}}`、`{{vault}}`、`{{scope}}` 用使用者的話填一句領域說明），把 `templates/task.md` 放進去當 `task.md`（填 `{{topic}}`）。
3. `SBK_HOME/routes.md` ← `templates/routes.md`：表格填兩個 id，各 5–10 個使用者真的會說的關鍵字。`SBK_HOME/alarms.md` ← `templates/alarms.md`。只有使用者有額外工具時才建 `SBK_HOME/channels.md`（步驟 7）。
4. 告訴使用者怎麼啟動（也寫進 `SBK_HOME/START-HERE.md`）：
   - 入口：`cd ~/.claude/sbk/entry` 然後 `claude --add-dir "<VAULT>" -n entry`
   - 主題：`cd ~/.claude/sbk/managers/<id>` 然後 `claude --add-dir "<VAULT>" -n <id>`
   - 所有新需求都丟給入口。之後想加主題對話，就複製一個 manager 資料夾、在 `routes.md` 加一列；先用兩個，某個主題一直擠到另一個時才加。

**檢查：** `python SBK_HOME/bin/send.py <id> "setup check"` 印出 `L0001 -> <id>`（或下一個編號）；`SBK_HOME/inbox/<id>.md` 有那一行；`SBK_HOME/bin/status.py` 看得到；然後關掉測試項目：`ledger.py drop L000N --evidence "setup test item"`，並把 inbox 那行勾成 `[x]`。

## 步驟 6：鬧鐘

1. 用一句話說明：一張小提醒表，提醒會落在帳本或某個主題的收件匣；預設一列是每週日 20:00 的每週檢討。保持精簡，每一列都必須帶出一個動作。
2. 執行器需要系統排程每 5 分鐘叫一次。這會改系統，所以先問（「同意我加一個每 5 分鐘執行 `alarm.py --tick` 的排程嗎？」）。同意後：
   - Windows：`schtasks /Create /SC MINUTE /MO 5 /TN sbk-alarm /TR "\"<pythonw.exe 路徑>\" \"%USERPROFILE%\.claude\sbk\bin\alarm.py\" --tick"`（用 `pythonw.exe` 才不會閃出視窗）
   - macOS／Linux：`crontab -e` 加 `*/5 * * * * python3 "$HOME/.claude/sbk/bin/alarm.py" --tick`
   他說不同意，鬧鐘就不會自動響；`alarm.py --fire A01` 仍可手動觸發。

**檢查：** `python SBK_HOME/bin/alarm.py --list` 看得到預設那列；`schtasks /Query /TN sbk-alarm`（或 `crontab -l`）看得到排程；`alarm.py --tick --now <下一個週日 20:01>` 會寫一筆帳本項目（接著附證據把這個測試項目 drop 掉，並刪除 `SBK_HOME/state/alarms.json`，讓正式執行從乾淨狀態開始）。

## 步驟 7：額外工具（只做使用者說「有」的）

全部都回答「沒有」就跳過這一步，並在最後報告寫明。有的話，每個工具都讀 `docs/MULTI-TOOL.md` 對應章節（那是參考資料：合用的才拿），然後：
1. 用 `templates/channels.md` 建立 `SBK_HOME/channels.md`，每個工具一列。
2. 第二個 Claude 帳號：請使用者把 `CLAUDE_CONFIG_DIR` 設成那個帳號專用的新資料夾，執行一次 `/login`（給他對應他作業系統的完整指令）；接著用 `entry/worker.ps1 -DryRun` 或 `SBK_DRYRUN=1 worker.sh` 測試，讀它印出的指令。
3. Codex／Gemini／Colab／OpenRouter：確認工具能啟動（版本指令或一行小工作）。
4. 每個工具各跑一個最小的真實工作，結果是一個檔案，並打開那個檔案看。

**檢查：** 每個啟用的工具在 `channels.md` 有一列，而且有一個你打開看過的結果檔。使用者沒選的工具，哪裡都不會出現。

## 步驟 8：最後驗證與交接

1. `python KIT/scripts/selftest.py` → `0 failed`；`vault_lint.py` → PASS；`status.py` 能跑。
2. 寫 `SBK_HOME/START-HERE.md`（用使用者的語言，30 行內）：兩個啟動指令、`status.py`、`ledger.py add/list/done --evidence`、怎麼加主題對話或鬧鐘、怎麼切換 hook 模式、紀錄在哪。
3. 給使用者的最後訊息：短，用他的語言。裝了什麼、在哪；每個 hook 實際上會怎麼影響他（被擋時才不會嚇到）；哪些**沒做**以及為什麼；哪些只有他能做（如果有）。每一步寫完成／沒完成。

## 更新與移除

- 更新：更新外掛（或 `git pull` 這個套件），再做一次步驟 1（複製工具）；手動安裝的話連步驟 4 的複製也再做一次。不要動使用者的筆記、`task.md`、帳本、路由、鬧鐘。
- 移除：拿掉 `CLAUDE.md` 的標記區塊、移除 hook 項目（或外掛）、刪掉排程。要刪 `SBK_HOME` 或筆記庫之前先問；那是使用者的資料。
