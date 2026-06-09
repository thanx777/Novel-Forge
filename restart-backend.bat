@echo off
setlocal enabledelayedexpansion
title OmniAgent Hub - Restart

echo ============================================
echo   Restart OmniAgent Hub
echo ============================================

:: ---- Step 1: Kill old processes ----
echo [1/2] Stopping old processes...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo   Kill backend PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    echo   Kill frontend PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo   Waiting for ports to release...
ping -n 3 127.0.0.1 >nul

:: ---- Step 2: Start services ----
echo [2/2] Starting services...

set "ROOT=%~dp0"

start "Backend-8000" cmd /c "cd /d "%ROOT%backend" && echo Backend running on http://127.0.0.1:8000 && python main.py && pause"

start "Frontend-5173" cmd /c "cd /d "%ROOT%frontend" && echo Frontend running on http://localhost:5173 && npm run dev && pause"

echo ============================================
echo   Backend : http://127.0.0.1:8000
echo   Frontend: http://localhost:5173
echo ============================================
echo   Close the two popup windows to stop services
pause
