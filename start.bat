@echo off
rem Starts the RL Event Scheduler: backend (FastAPI :8000) + frontend (Vite :5173)
setlocal
cd /d "%~dp0"

echo [1/3] Checking dependencies...
if not exist "frontend\node_modules" (
    echo   Installing frontend dependencies...
    pushd frontend
    call npm install --no-fund --no-audit
    popd
)

echo [2/3] Starting backend on http://localhost:8000 ...
start "RL Scheduler - Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --port 8000"

echo [3/3] Starting frontend on http://localhost:5173 ...
start "RL Scheduler - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

rem Give both servers a moment, then open the dashboard
timeout /t 5 /nobreak >nul
start "" http://localhost:5173

echo.
echo Dashboard:  http://localhost:5173
echo API docs:   http://localhost:8000/docs
echo Close the two server windows to stop.
endlocal
