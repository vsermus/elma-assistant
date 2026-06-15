$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

# Copy .env from project root if exists
$envFile = Join-Path $RootDir ".env"
$localEnv = Join-Path $ScriptDir ".env"
if (Test-Path $envFile) {
    Copy-Item $envFile $localEnv -Force
}

# Install requirements if needed
$reqFile = Join-Path $ScriptDir "requirements.txt"
pip install -r $reqFile -q

# Run server
cd $ScriptDir
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
