@echo off
cd /d "%~dp0"
echo Starting frontend from %CD%
if not exist "node_modules" (
  echo Installing dependencies...
  call npm install
)
npm run dev
