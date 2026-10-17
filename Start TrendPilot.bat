@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\trendpilot.exe" (
  "%~dp0.venv\Scripts\trendpilot.exe" desktop
) else (
  where uv >nul 2>nul
  if errorlevel 1 (
    echo TrendPilot needs uv to set up its Python environment.
    echo Install uv, then double-click this file again.
    pause
    exit /b 1
  )
  uv run trendpilot desktop
)

if errorlevel 1 pause
