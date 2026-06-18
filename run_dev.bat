@echo off
set "PROJECT_ROOT=%~dp0"
set "NODE_PATH=%PROJECT_ROOT%node-bin\node-v20.18.0-win-x64"

echo Starting Backend...
start "Backend Server" cmd /k "cd /d "%PROJECT_ROOT%backend" && venv\Scripts\activate && uvicorn app.main:app --reload"

echo Starting Frontend...
start "Frontend Server" cmd /k "set PATH=%NODE_PATH%;%%PATH%% && cd /d "%PROJECT_ROOT%" && npm run dev"

echo Development Environment Ready
