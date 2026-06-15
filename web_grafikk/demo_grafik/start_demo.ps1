$port = 8000
Write-Host ""
Write-Host "========================================"
Write-Host "  Demo: http://localhost:$port"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""
python -m http.server $port --bind 127.0.0.1
