@echo off
title Futsal Scout API Server
cd /d "%~dp0"
echo ========================================================
echo   Futsal Scout Hub 5x5 Server
echo ========================================================
echo.
echo Starting FastAPI server at http://localhost:8000 ...
echo Press Ctrl+C to stop the server.
echo.
"C:\Users\ersov\AppData\Local\Programs\Python\Python314\python.exe" server.py
echo.
echo Server stopped.
pause
