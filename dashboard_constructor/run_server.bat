@echo off
chcp 65001 > nul
echo Starting Dashboard Constructor Server...
pip install fastapi uvicorn
python "server\main.py"
pause
