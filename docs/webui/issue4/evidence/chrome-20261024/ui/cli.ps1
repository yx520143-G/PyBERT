param([Parameter(ValueFromRemainingArguments=$true)][string[]]$BrowserArgs) & "C:/Users/yx/AppData/Roaming/Python/Python312/Scripts/uv.exe" run -- npx.cmd --package @playwright/cli playwright-cli -s=pybert4-resources @BrowserArgs

