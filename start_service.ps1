$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw '未找到 .venv。请先执行：py -m venv .venv；然后 pip install -r requirements.txt'
}

Set-Location $projectRoot
& $python -m mock_server.app
