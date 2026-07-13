Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
  if (-not (Test-Path ".venv")) {
    python -m venv .venv
  }

  .\.venv\Scripts\pip install -r requirements.txt
  .\.venv\Scripts\python -m app.scripts.seed
  .\.venv\Scripts\uvicorn app.main:app --reload
}
finally {
  Pop-Location
}

