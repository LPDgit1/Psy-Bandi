Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
  .\.venv\Scripts\python -m app.scripts.seed
}
finally {
  Pop-Location
}

