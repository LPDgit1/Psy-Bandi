Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
  .\.venv\Scripts\python.exe -m app.scripts.import_real --remove-demo --probe-local-sources
}
finally {
  Pop-Location
}

