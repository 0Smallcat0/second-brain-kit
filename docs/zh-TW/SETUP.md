# SETUP：給負責安裝的 Claude 的步驟

這份是寫給**你（Claude）**看的，不是給使用者看的。使用者請你幫他安裝 second-brain-kit，他可能完全不懂技術：事情由你做，他只要回答四個簡單問題、確認你建議裝哪些，並對會動到他電腦設定的地方說同意或不同意。安裝的問題和步驟只寫在這裡（`/sbk-setup` 指令和 `setup-second-brain` 技能都指到這份）；英文版 `docs/SETUP.md` 是同樣的步驟。

**要裝哪些由你逐項建議、使用者確認**（步驟 0 第 4 點）：主要看他對「你用 Claude 最常卡在哪？」的回答；他同意你看這台電腦上的 Claude 對話紀錄時，紀錄的數字當佐證。他不同意、或這台電腦沒有紀錄（新使用者），就只照回答；回答沒說到哪一項就裝基本款。每一項用一句話說建議和理由，他可以改。
- **基本款**：一個在筆記資料夾裡工作的主對話；只放使用者用得到的區的筆記資料夾；一份工作清單（帳本，由你使用，使用者不用打指令）；安全檢查；簡短的通用原則。
- **加開的項目**（主題對話、提醒、和其他 AI 工具分工）：逐項建議，他確認的才在步驟 5b 照[進階功能.md](進階功能.md)開。有加開任何一項，設定檔裡記成 `full`（完整款）。

其他的一律先關著。裝好之後，每週的檢查（`level_check.py`）會量看看還有哪一項用得到；用得到時由你問使用者一個要不要的問題。

下面用到的代號：
- `KIT`：裡面有 `.claude-plugin/plugin.json`、且寫著 `"name": "second-brain-kit"` 的那個資料夾。用外掛（plugin，Claude Code 的擴充套件）安裝時就是 `${CLAUDE_PLUGIN_ROOT}`（外掛的 hook 和指令裡才有這個值；在這個對話裡請到 `~/.claude/plugins` 底下的外掛快取找那個檔案）。手動 clone 時就是 clone 下來的資料夾。
- `SBK_HOME`：`~/.claude/sbk`（工作清單、紀錄、套件設定放這裡）。
- `VAULT`：使用者選的筆記資料夾（預設 `~/second-brain`）。
- `SURFACE`：使用者怎麼開 Claude：`app`（Claude 桌面版 App 的 **Code** 分頁）或 `terminal`（在終端機視窗輸入 `claude`）。步驟 0.2 決定；步驟 5、6、7 依它分開做。
- 路徑：Windows 上用正斜線或加引號。Python：`python3`、`python`、`py` 哪個能跑 Python 3 就用哪個。

做事規則：
- 會改到 `~/.claude/settings.json`、`~/.claude/CLAUDE.md`、系統排程、或使用者原有檔案的，先問。不覆寫已有的檔案；先給他看差異，他說好才改。
- 不推上任何 git 遠端、不寄任何訊息、不把筆記交給其他 AI 工具。但不要跟使用者說「完全離線」：Claude 本身就是線上服務。
- 可以挽回的小選擇自己決定（資料夾名稱、測試名稱、暫用的 git 身分），在報告裡說選了什麼。只問只有使用者知道、或要他授權的事。
- 每一步最後都有**檢查**。跑過、通過了才往下；沒過就查原因、修好、再跑一次。沒檢查過的步驟不能說做完。
- 每一步回報時只用這五個詞之一：**完成**／**沒開啟**（使用者不要的選項）／**不適用**（這台電腦用不到）／**要你做**（只有使用者能做，寫清楚做什麼）／**沒驗證**（無法檢查，寫原因）。

---

## 步驟 00：取得套件（這台電腦已經有 `KIT` 就跳過）

使用者可能只貼了 README 的那句話（「請從 https://github.com/0Smallcat0/second-brain-kit 安裝 second-brain-kit，照 docs/zh-TW/SETUP.md 幫我設定……」）。那句話本身就是要你安裝，不用再問一次。
1. 執行 `claude plugin marketplace add 0Smallcat0/second-brain-kit`，再執行 `claude plugin install second-brain-kit@second-brain-kit`（就是 `/plugin marketplace add ...`、`/plugin install ...` 的命令列版本）。
2. 這裡跑不了 `claude` 指令（只用桌面版 App 的人可能沒有，App 不需要它）、或安裝失敗：把 `https://github.com/0Smallcat0/second-brain-kit` clone 到一個新資料夾（例如 `~/second-brain-kit-src`），用它當 `KIT`。hook 之後走步驟 4 的手動做法。
3. 找到 `KIT`（見上面代號），從那裡讀這份檔案再繼續。

**檢查：** `KIT/.claude-plugin/plugin.json` 存在且寫著 `second-brain-kit`；`claude plugin list` 列出 second-brain-kit（走 clone 的話，記下你用的是 clone）。

## 步驟 0：檢查電腦、問四件事、逐項建議要裝哪些

1. 執行 `python --version`（或 `python3`／`py`）和 `git --version`；需要 Python 3.8 以上和 git。用終端機的人還要 `claude --version` 跑得起來；用 App 的人不用（桌面版 App 內建 Claude Code，也沒有 `claude -p`）。
   缺哪個就提議幫他裝（「我幫你裝 Python 好嗎？」），他同意就裝：Windows 用 `winget install -e --id Python.Python.3.12`／`winget install -e --id Git.Git`；macOS 用 `xcode-select --install`（會裝好 git 和 python3），有 Homebrew 的話也可以 `brew install python git`；Linux 用套件管理員。要輸入管理員密碼、或要在安裝視窗按按鈕的部分算**要你做**：告訴使用者是哪個視窗、哪個指令，然後繼續。
2. 先決定 `SURFACE`。讀環境變數 `CLAUDE_CODE_ENTRYPOINT`（`echo $CLAUDE_CODE_ENTRYPOINT`；PowerShell 用 `$env:CLAUDE_CODE_ENTRYPOINT`）：`claude-desktop` 或 `claude-desktop-3p` → `app`；`cli` → `terminal`。這些是 Anthropic 監控說明頁列出的「對話怎麼啟動的」值；這個變數本身官方沒寫，只當線索。其他值（`claude-vscode`、`sdk-cli`……）或沒有：看不出來，就在下面第 1 題後面加一句「你平常是用 Claude 桌面版 App（Code 分頁），還是在終端機視窗裡用？」，照他的回答。使用者的回答永遠大過這個變數。
   然後用**一則訊息**、白話問這四題，然後等他回答：
   1. 「筆記要放在哪裡？我建議 `~/second-brain`（直接說好就用這個）。」
   2. 「筆記和回覆要用哪種語言？」
   3. 「你用 Claude 最常卡在哪？例如同時好幾件事會搞混、常忘記期限、要一直重講背景、還是都還好？（如果你也有 ChatGPT、Gemini 這類其他 AI 的帳號，順便說一聲；沒有就不用提，一個 Claude 帳號就夠了。）」
   4. 「我可以看這台電腦上你的 Claude 對話紀錄來幫你判斷嗎？安裝時只數近兩週有幾個專案資料夾在用、有沒有對話長到被自動濃縮兩次以上；之後大約每週只看在筆記資料夾裡的對話，數你請我提醒、說事情搞混了幾次。只在這台電腦上數，不上傳、不改任何東西。不要也完全沒關係。」
   這裡和之後的安裝過程都不要再問別的。不算多問的只有：變數看不出來時問「App 還是終端機」，要改他電腦設定前問同意，以及第 4 點建議開主題對話時順便問要分哪幾件事。不做個人資料訪談、不逐一列工具問、不問「要基本款還是完整款？」。
3. 建立 `SBK_HOME`。如果 `SBK_HOME/config.json` 不存在，把 `KIT/templates/config.json` 複製過去，填上 `vault`（絕對路徑）、`language`、`uses`（第 3 題的原話）、`other_tools`（只填他說他**有帳號**的工具；沒提就留空）、`read_history`（第 4 題：同意 `true`，不同意 `false`）。如果已經存在（修復或第二次安裝），保留裡面所有的值，只補模板有、檔案缺的欄位。
4. **逐項建議要裝哪些，他確認。**
   - 第 4 題同意：執行 `python KIT/scripts/level_check.py --install`。它只在這台電腦上數兩件事：`~/.claude/projects` 裡近 14 天有在用的專案資料夾有幾個，以及有沒有哪個對話被自動摘要（compact）兩次以上。對話內容不讀，也不改任何東西。輸出有 `"partial": true` 表示數了 30 秒就停：照它數到的算。
   - 第 4 題不同意：不執行，也不看 `~/.claude/projects`。同意了但 `active_projects_14d` 是 0（新使用者，沒有紀錄）也一樣：只照他的回答。
   - 每一項主要看第 3 題的回答；紀錄的數字只當佐證，回答沒說到的不靠數字硬開：
     - **主題對話**（進階功能 A1，一件事一個對話）：他說同時好幾件事會搞混；或他回答「不確定」，而紀錄顯示近兩週 3 個以上專案資料夾在用、且 `session_compacted_2plus_14d` 是 1。
     - **提醒**（A2）：他說常忘記期限，或想被提醒。
     - **和其他 AI 工具分工**（A5）：只有他說他有那個工具的帳號才建議；只提到名字不算。
     - 他說「要一直重講背景」：基本款本來就在處理（筆記換了對話也找得回來、工作清單、長對話被濃縮後把他的原話放回去），不另外開；他同時也說好幾件事會搞混，就照主題對話那條。
     - 「都還好」、沒回答、或回答沒說到上面任何一項：**基本款**，不加開。
   硬碟空間、作業系統、git 提交次數決定的是某一項*能不能*跑，不是需不需要，不能當理由。
   - 用**一則訊息**、他的語言，每一項一行：建議開或先不開，加一句附數字的理由；最後問「這樣可以嗎？想加或拿掉哪一項直接說。」建議開主題對話時，同一則訊息問「要分成哪幾件事、各開一個對話？（二到四件）」。例如：
     「我建議這樣裝：
     - 基本款：一定裝（筆記、工作清單、安全檢查）。
     - 提醒：開。你說常忘記期限。
     - 主題對話：先不開。你說事情不會搞混；這台電腦近兩週只有 1 個專案資料夾在用。
     - 和其他 AI 分工：先不開。你沒有提到其他 AI 的帳號。
     這樣可以嗎？想加或拿掉哪一項直接說。」
     等他回答。他確認的就是決定；他之後改主意也照他的。
   - 把 `level`（有加開任何一項是 `full`，否則 `basic`）和 `level_reason`（那幾行，併成一行）寫進 `SBK_HOME/config.json`。你建議了、他卻不要的項目，執行 `python KIT/scripts/level_check.py --decline <代號>`（`multi_session`、`alarms`、`multi_tool` 中對應的），每週檢查四週內就不會再問。

**檢查：** `python -c "import json,os;c=json.load(open(os.path.expanduser('~/.claude/sbk/config.json'),encoding='utf-8'));print(c['level'],c['read_history'],c['vault'],c['modes'])"` 印出 `basic` 或 `full`（和他確認的一樣）、`True` 或 `False`（和第 4 題一樣）、筆記資料夾路徑、模板裡的模式（修復時是他原本的模式）。

## 步驟 1：工作清單的工具

1. 建立 `SBK_HOME/bin` 和 `SBK_HOME/logs`。
2. 把 `KIT/entry/ledger.py`、`status.py`、`send.py`、`alarm.py` 和 `KIT/scripts/level_check.py` 複製到 `SBK_HOME/bin/`（`status.py` 會用到 `ledger.py`、`send.py`；`/sbk-status` 和每週檢查會跑 `level_check.py`）。把 `KIT/templates/task.md` 複製成 `SBK_HOME/task-template.md`。一律用複製的，不要直接指到外掛快取：更新時那個路徑會變。

**檢查**（新的或已有的工作清單都適用）：
1. `python SBK_HOME/bin/ledger.py list`，記下輸出。
2. `python SBK_HOME/bin/ledger.py add "sbk setup check"` 會印出一個新編號；用它印出的編號（不要假設是 `L0001`）。
3. `python SBK_HOME/bin/ledger.py done <編號> --evidence "setup step 1: add, done and list ran"` 印出 `<編號> done`。
4. `ledger.py list` 的輸出和第 1 點完全一樣（舊項目沒被動到）；`ledger.py list --all` 顯示 `<編號>` 已完成。

## 步驟 2：通用原則放進 `~/.claude/CLAUDE.md`（要同意）

`KIT/templates/CLAUDE.md` 只放通用的安全與查證原則。它會放進使用者全域的 `~/.claude/CLAUDE.md`，影響這台電腦上所有的 Claude 對話，所以先問：「要不要把一小段通用原則（說做完前先看結果、刪東西或公開前先問）加進你所有專案的 Claude 設定？筆記庫的規則還是只放在筆記資料夾裡。」
1. 使用者的語言不是繁體中文的話，忠實翻譯模板（結構和意思不變，100 行以內）。
2. 這一段一律放在 `<!-- sbk:begin -->` 這一行和 `<!-- sbk:end -->` 這一行之間：
   - 檔案不存在：建立檔案，內容只有這一段（含標記）；
   - 檔案存在、沒有標記：先給使用者看這一段，他說好就加在檔案最後；不刪、不調換他原本的文字；
   - 已經有標記（第二次安裝）：先給他看差異，只換掉兩個標記中間的內容。不能多出第二段。
3. 他說不要也沒關係：這一步記**沒開啟**；筆記庫的規則一樣會從 `VAULT/AGENTS.md` 生效。

**檢查：** 檔案裡 `<!-- sbk:begin -->` 和 `<!-- sbk:end -->` 各剛好一個、begin 在前，中間不到 100 行（或這一步是**沒開啟**）。

## 步驟 3：筆記資料夾（`VAULT`）

1. 只建這些區的資料夾（名稱照 `KIT/templates/筆記格式.md` 第 1 節的表；`NN-NN` 編號保留；使用者要別的語言才翻譯文字部分）：
   - `00-09 系統與索引`，底下有 `00 索引`、`01 規則`、`02 收件匣`；
   - 步驟 0 的回答（或他同意看的紀錄）看得出他在做什麼，就建一兩個對應的區（讀書、作業 → `20-29 學習與讀書`；寫程式或自己的專案 → `40-49 專案`；工作 → `30-39 工作與打工`……）。看不出來就不多建，第一張筆記需要時再建；
   - `90-99 封存`。
   不建空的類別資料夾；第一張筆記需要時才建類別。
2. 複製到筆記資料夾，把 `{{date}}` 換成今天（`YYYY-MM-DD`）。檔案已經存在就保留，改成比對（修復）：
   - `templates/AGENTS.md` → `VAULT/AGENTS.md`；另建 `VAULT/CLAUDE.md`，內容只有一行：`@AGENTS.md`
   - `templates/筆記格式.md` → `VAULT/00-09 系統與索引/01 規則/01-01 筆記格式.md`
   - `templates/todo-for-me.md` → `VAULT/00-09 系統與索引/02 收件匣/02-02 我要做的事.md`
   - 一張收件匣筆記 `VAULT/00-09 系統與索引/02 收件匣/02-01 收件匣.md`，frontmatter（筆記開頭的欄位區）要正確（`type: log`、`status: active`、一句話摘要、今天日期、`origin: agent-drafted`），內文一行「還沒歸位的東西先放這裡。」
   - `templates/sbk-protect.txt` → `VAULT/.sbk-protect`；一個空檔 `VAULT/.sbk-vault`；`VAULT/.gitignore`，內容一行 `__pycache__/`（Python 會在 scripts 旁邊留下這個資料夾）
   - `KIT/scripts/{vault_lint.py,gen_jdex.py,check_overwrite.py,pre-commit}` → `VAULT/scripts/`；macOS／Linux 要 `chmod +x VAULT/scripts/pre-commit`。
3. 使用者要別的語言，就翻譯複製過去的筆記（欄位名稱和 `type: skill` 這類值不能改，檢查程式靠它們）。
4. `python VAULT/scripts/gen_jdex.py --root VAULT` 產生索引。
5. Git，只在本機（記下每次修改的歷史，不推上任何地方）：
   - `VAULT/.git` 不存在就在 `VAULT` 執行 `git init`。
   - `git -C VAULT config user.name` 和 `git -C VAULT config user.email` **分開檢查**。哪個是空的就只替這個筆記資料夾設定（不加 `--global`）：名字用使用者給的，沒給就用 `second-brain`；email 用 `second-brain@localhost`。告訴使用者你設了什麼。
   - `git -C VAULT config core.hooksPath scripts`。
   - 第一次安裝：逐一指定檔名加入，提交 "Initial vault"。修復：只提交你新增或改過的檔案。

**檢查：**
1. `python VAULT/scripts/vault_lint.py --root VAULT` 最後是 `RESULT: PASS`。
2. `git -C VAULT log --oneline` 看得到那次提交；`git -C VAULT config core.hooksPath` 印出 `scripts`。
3. 防覆寫檢查真的會跑。用測試資料夾裡的假筆記測，絕不拿真的筆記測：
   1. 記下 `git -C VAULT rev-parse HEAD`。
   2. 建 `VAULT/.sbk-setup-test/test-note.md`，寫 20 行（`test line 1` 到 `test line 20`）；`git -C VAULT add .sbk-setup-test/test-note.md`；`git -C VAULT commit -m "sbk setup test (removed again)"`，這次必須成功。
   3. 把檔案改成只剩一行，`git add` 後再提交，這次必須被**拒絕**，並出現 `check_overwrite: commit refused`。
   4. 收拾：`git -C VAULT reset -q --soft <第 1 點記下的 HEAD>`、`git -C VAULT rm -r -q --cached .sbk-setup-test`，刪掉 `.sbk-setup-test` 資料夾。
   5. `git -C VAULT rev-parse HEAD` 和第 1 點相同，`.sbk-setup-test` 已不在，`git -C VAULT status --short` 看不到測試留下的東西。
   第 3 點沒被拒絕的話，修好 `core.hooksPath`（macOS／Linux 還有 `chmod`），再測一次。

## 步驟 4：安全檢查（hook）

hook 是 Claude Code 在特定時刻（執行指令前、Claude 說做完時）自動跑的小程式，不是另一個 AI。這套 hook 不會把對話卡死：hook 自己壞掉時會讓 Claude 繼續。

- **用外掛安裝：** `KIT/hooks/hooks.json` 從下一個對話開始生效。用 `claude plugin list` 確認 second-brain-kit 是啟用的。
- **用 clone 安裝：** 把 `KIT/hooks/*.py` 和 `run.sh` 複製到 `SBK_HOME/hooks/`；使用者同意後（會改設定），把 `KIT/templates/settings.hooks.example.json` 的 `hooks` 區塊合併進 `~/.claude/settings.json`，`__KIT__` 換成 `SBK_HOME/hooks` 的路徑。是合併不是取代：使用者原有的 hook 一個都不能少。

每個 hook 的模式都從 `SBK_HOME/config.json` 的 `modes` 讀（可用值：off、log、warn、ask、deny、block）。基本款就是模板裡那組；每個 hook 用一句白話告訴使用者：

| Hook | 使用者會感覺到什麼 | 基本款模式 |
|---|---|---|
| `vault_guard` | Claude 在 `git push`、跳過 git 檢查、丟掉 git 裡的修改、刪整個資料夾、改受保護的規則檔、把筆記砍到剩一小部分之前，會先問你 | ask |
| `read_whole` | 在筆記資料夾裡，Claude 會把筆記整張讀完，不只看前幾行（筆記資料夾以外不影響） | deny |
| `requests_reinject` | 長對話被自動摘要時，把你自己說過的話原文放回去；這台電腦的 `~/.claude/sbk/requests/` 會留一份 | warn |
| `stop_evidence` | Claude 改了東西、沒看結果就說「做完」時，記到 `~/.claude/sbk/logs/stop_evidence.log`；不會打斷 | log |
| `usage_warn` | 沒有作用（進階功能） | off |
| `inbox_notice` | 沒有作用（進階功能，給主題對話用） | off |
| `level_notice` | 最多一週一次、只在筆記資料夾裡的對話：你遇到的狀況顯示某一項進階功能用得到時（例如一週內請 Claude 提醒兩次；表在進階功能.md），Claude 會附上數字問你一個要不要的問題。你沒說好就什麼都不改；第 4 題你說不要的話，它不讀對話紀錄 | warn |

重播測試，只在步驟 0 第 4 題同意看紀錄時做（已經同意過，不再問一次）：對最新的五個 `~/.claude/projects/*/*.jsonl`（跳過這次安裝的對話）跑 `python KIT/hooks/stop_evidence.py --replay <檔案>`，用一句話告訴他會有幾輪被標出來。沒有舊對話就安靜跳過（**不適用**）。第 4 題他說不要，這一步就是**沒開啟**。不管結果如何這個檢查都維持 `log`；要它擋下是進階功能（A4）。

接著執行 `python KIT/scripts/selftest.py`。

**檢查：** `selftest.py` 印出 `0 failed`；步驟 0 檢查印出的模式是基本款那組（修復時是他原本的模式）；下面這行會印出含 `"permissionDecision": "ask"` 的內容：
`echo '{"tool_name":"Bash","tool_input":{"command":"git push"},"cwd":"VAULT"}' | python KIT/hooks/vault_guard.py`（`VAULT` 換成實際路徑）。

## 步驟 5：怎麼打開主對話

主對話就是在 `VAULT` 裡啟動的 Claude Code；在那裡它會讀 `VAULT/CLAUDE.md`，再載入 `AGENTS.md`（桌面版 App 和終端機讀的是同樣的檔案）。怎麼做看 `SURFACE`；不要假設使用者有桌面捷徑。

### `SURFACE` = app：不做捷徑檔

不要做 `.cmd`、`.command`、`.sh`。用使用者的語言告訴他下面這幾步，按鈕名稱照 App 自己的（出自 Anthropic 桌面版快速入門和桌面版說明頁，名稱是英文；中文介面若顯示不同，就請他照位置找），並在步驟 7 寫進 `VAULT/README.md`：
1. 打開 Claude（macOS：「應用程式」資料夾；Windows：開始選單；Linux：應用程式啟動器），點側邊欄上方的 **Code** 分頁。如果分頁只顯示圖示，把滑鼠移上去就會看到名稱。
2. 在輸入框下面那一排，點第一個控制項（環境選單），選 **Local** 群組最上面那一項；再點它旁邊的專案資料夾控制項，選 **Open folder…**，選 `<VAULT>`（寫出完整路徑）。
3. 像聊天一樣打字跟 Claude 說。下次要繼續，就在側邊欄點那個對話；側邊欄的 **+ New** 會開新對話，資料夾用同樣方式再選一次。點標題列上的對話標題可以改名（例如「第二大腦」），之後比較好找。
- 新對話如果把環境顯示在輸入框上面、不是下面，是舊版畫面：資料夾就在輸入框上面選，或更新 App（macOS **Claude > Check for Updates…**，Windows **Help > Check for Updates…**）。
- 官方文件沒有寫釘選或「最近的資料夾」功能，所以不要承諾有；側邊欄的對話列表就是回來的路。

**檢查：** `VAULT/CLAUDE.md` 裡有 `@AGENTS.md`，`VAULT/AGENTS.md` 存在（App 開啟那個資料夾時載入的就是它們）。在 App 裡真的開起資料夾，在使用者於步驟 7 做之前是**沒驗證**。

### `SURFACE` = terminal：捷徑，或兩行指令

做一個點兩下就能開的捷徑，用使用者的語言命名（例如「第二大腦」）。這是新檔案；同名檔案已經存在的話，先問再取代。
- **Windows：** `<桌面>\第二大腦.cmd`（用 `powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"` 找出真正的桌面，可能在 OneDrive 裡），存成不含 BOM 的 UTF-8：
  ```
  @echo off
  chcp 65001 >nul
  cd /d "C:\筆記資料夾的完整路徑"
  claude
  ```
- **macOS：** `~/Desktop/第二大腦.command`，再 `chmod +x`：
  ```
  #!/bin/sh
  cd "/筆記資料夾的完整路徑" || exit 1
  exec claude
  ```
- **Linux：** 同一段內容存成 `~/Desktop/second-brain.sh`（沒有桌面資料夾就放 `~/second-brain.sh`），`chmod +x`。
也告訴使用者不用捷徑的方法：開終端機，`cd "<VAULT>"`，輸入 `claude`；`claude --continue` 會回到在那裡的上一段對話。

**檢查：** 捷徑檔存在、裡面有筆記資料夾的路徑；而且從那個資料夾跑得起 Claude Code：Windows `cmd /c "cd /d "<VAULT>" && claude --version"`，macOS／Linux `sh -c 'cd "<VAULT>" && claude --version'` 印出版本。點兩下開捷徑本身在使用者於步驟 7 做之前都是**沒驗證**。

## 步驟 5b：開啟他確認要加開的項目

沒有加開任何一項：**不適用**。有的話，依 A1、A2、A5 的順序，照[進階功能.md](進階功能.md)開他在步驟 0 確認的每一項。安裝時的規則：
- A1：主題就是他在步驟 0 說要分開的那幾件事（二到四個）；沒說清楚的歸到一個 `general` 主題。不要再問 A1 的「哪兩件事要各有自己的對話？」。
- A2：要不要加系統排程的那一題是問同意，照樣要問；他說不要的話，只有排程是**沒開啟**。
- A5：只接他說有帳號的工具。

每一項各自用狀態詞回報，各自跑進階功能.md 裡的檢查。

## 步驟 6：端到端測試：新對話找得到這次存的東西

技術檢查都過，不代表第二大腦真的能用。用測試資料證明一次，再把測試資料清掉。
1. 取一個代號，例如 `SBKTEST-` 加六個隨機字母。
2. 存一張測試筆記 `VAULT/00-09 系統與索引/02 收件匣/02-99 SBK 安裝測試.md`，frontmatter 要正確（`type: log`、`status: active`、`summary: setup test note, deleted after the test`、今天日期、`origin: agent-drafted`），內文一行：`Setup test <代號>.` 不要提交。
3. 記下 `ledger.py list` 的輸出。加一個測試項目：`python SBK_HOME/bin/ledger.py add "Setup test <代號>: add the line resumed by a new session to the note 02-99 SBK 安裝測試"`，記下印出的編號。
4. 在筆記資料夾開一個完全不知道這次對話的**新**對話：
   先 `cd "<VAULT>"`，再
   `claude -p "Setup test. Follow this folder's AGENTS.md: find the open work-list item that mentions <代號>, open the note it names, add the line 'resumed by a new session' at the end, close the item with evidence. Do not commit. Reply with the note path and the item id." --allowedTools "Read,Grep,Glob,Edit,Bash(python:*)"`
   這裡跑不了 `claude -p` 的話（用 App 的人常常沒有 `claude` 指令，App 也沒有 `-p`），請使用者在筆記資料夾另開一個對話：App 就點側邊欄 **+ New**，再照步驟 5 選 **Open folder…** `<VAULT>`；終端機就打開步驟 5 的捷徑，或在另一個視窗 `cd "<VAULT>"` 再輸入 `claude`；然後說「繼續安裝測試那個項目」，等它回完再告訴你；這段時間這個對話保持開著。
5. 收拾：刪掉測試筆記；再跑一次 `gen_jdex.py` 和 `vault_lint.py`；測試項目保持已關閉（關閉的項目不會顯示）。

**檢查：** 收拾前，筆記最後一行是 `resumed by a new session`，`ledger.py list --all` 顯示測試編號已完成、證據是新對話寫的；收拾後，筆記不在了，lint 最後是 `RESULT: PASS`，`git -C VAULT status --short` 看不到測試檔，`ledger.py list` 的輸出和第 3 點完全一樣。新對話沒找到項目的話，看它回了什麼，修好原因（通常是 `VAULT/CLAUDE.md` 或 `AGENTS.md` 裡工作清單的路徑），再測一次。

## 步驟 7：最後檢查、交接、兩分鐘上手

1. `python KIT/scripts/selftest.py` → `0 failed`；`vault_lint.py` → `RESULT: PASS`；`python SBK_HOME/bin/status.py` 跑得起來。
2. 寫入口說明頁 `VAULT/README.md`（檢查程式允許筆記資料夾最上層有這個檔名），用使用者的語言、30 行以內、給使用者看（不是給 Claude）。只寫怎麼開始、怎麼讓 Claude 記住、怎麼看還有什麼沒做完、怎麼請它修：
   - 怎麼開始，照 `SURFACE`：App——步驟 5 那幾步（Code 分頁、**Open folder…**、下次點側邊欄那個對話）；終端機——捷徑的名稱和位置，或 `cd` 到筆記資料夾輸入 `claude`。完整款：新的需求交給入口對話；要某個主題動工就打開它的對話；
   - 四句範例：「記住：……」「找我之前記的……」「還有什麼沒做完？」「接著上次的……繼續」；
   - 「哪裡卡卡的就跟 Claude 說，例如：『做完檢查太嚴了，調鬆一點』」；
   - 東西放在哪：筆記在這個資料夾；工作清單和紀錄在 `~/.claude/sbk/`；本機 git 記下修改的歷史，但**不是**硬碟的備份：要不時把這個資料夾複製到另一顆硬碟或你信任的雲端硬碟；
   - 「Claude 大約每週會看一次還有沒有哪一項用得到（主題對話、提醒、其他 AI 工具），會先問你。你也可以直接說，例如：幫我開主題對話。」
3. 最後一則訊息，簡短、用使用者的語言：
   - 第一行：裝了哪些（基本款＋他確認加開的項目）、各為什麼（步驟 0 第 4 點那幾行，併成一行）；
   - 每一步一行，附狀態詞（完成／沒開啟／不適用／要你做／沒驗證）；
   - 每個安全檢查實際上會對他做什麼；
   - 你沒做的事和原因；只有他能做的事寫成編號清單（有的話）；
   - **兩分鐘上手**：（1）App：在 Claude App 側邊欄點筆記資料夾那個對話（或 **+ New**，再 **Open folder…** `<VAULT>`）；終端機：關掉這個視窗，點兩下捷徑（或 `cd` 到筆記資料夾輸入 `claude`）；（2）說「記住：我這週要讀完第三章」，Claude 會存起來；（3）說「還有什麼沒做完？」，Claude 會列出工作清單；（4）說「找我之前說的第三章」，Claude 會找到那張筆記。每天就是這樣用。

**檢查：** `VAULT/README.md` 存在、lint 仍然通過；最後一則訊息第一行是裝了哪些那一句，步驟 00 到 7（含 5b）每一步都有狀態詞。

---

## 更新、修復、移除

- **修復或第二次安裝：** 照順序重跑每一步。每一步都保留已有的東西：設定值、筆記、工作清單（`ledger.md`）、`task.md`、`requests/`、`logs/`，以及進階功能的 `routes.md`、`alarms.md`、`state/alarms.json`，一律不刪、不重設。只補缺的；套件裡改過的檔案先給使用者看，才取代任何東西。
- **更新：** 更新外掛（`claude plugin update second-brain-kit@second-brain-kit`）或在 clone 資料夾 `git pull`；再重做步驟 1 的複製，clone 安裝的話再重做步驟 4 的複製。不動使用者的筆記和工作清單。
- **移除：** 刪掉 `~/.claude/CLAUDE.md` 裡兩個 `sbk` 標記中間的段落，移除外掛（或刪掉 `settings.json` 裡的 hook 項目），有做捷徑的話刪掉（只有終端機使用者有），進階功能還要刪系統排程。筆記資料夾和 `SBK_HOME`（工作清單、紀錄）預設保留；要刪之前先問：那裡面是使用者的資料。最後告訴他保留了什麼、在哪裡。

## 進階功能

安裝時只開步驟 0 第 4 點他確認的那幾項。之後使用者要更多功能，或每週檢查（`level_check.py`，由 `level_notice` 這個 hook 和 `/sbk-status` 執行）量到[進階功能.md](進階功能.md)〈Claude 什麼時候會提議〉表裡的情況、而且使用者說好時，照那份的 A1–A5 做。
