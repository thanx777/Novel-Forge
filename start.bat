@echo off
echo ==========================================
echo       Start OmniAgent Hub
echo ==========================================

echo [1/2] Starting Backend Server (FastAPI)...
start "Backend Server" cmd /c "cd backend && uvicorn main:app --reload"

echo [2/2] Starting Frontend Server (React)...
start "Frontend Server" cmd /c "cd frontend && npm run dev"

echo.
echo All services started!
echo Please wait a few seconds, then open in browser: http://localhost:5173
echo.
pause