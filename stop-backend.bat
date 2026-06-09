@echo off
setlocal enabledelayedexpansion
title OmniAgent Hub - Stop

echo ============================================
echo   Stop OmniAgent Hub
echo ============================================

echo Looking for backend (port 8000)...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    set /a FOUND+=1
    echo   Killing PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
if !FOUND! equ 0 echo   Not running

echo Looking for frontend (port 5173)...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    set /a FOUND+=1
    echo   Killing PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
if !FOUND! equ 0 echo   Not running

echo ============================================
echo   Done
echo ============================================
pause
