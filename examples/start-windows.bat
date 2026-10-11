@echo off
rem Author: Maurizio Verde - LastReload
rem mnemonic-proxy on native Windows: llama-server.exe in its own window, the proxy in this one.
rem Edit the four paths below (or set them in the environment first). Run from the folder that holds slots\ and data\ (created if missing).
rem slot_dir in the config and --slot-save-path must be the SAME folder: both are .\slots here.

if not defined LLAMA set LLAMA=C:\llama\llama-server.exe
if not defined MODEL set MODEL=C:\models\model.gguf
if not defined CONFIG set CONFIG=%~dp0config.llama-server.json
if not defined VENV set VENV=%USERPROFILE%\mnemonic-venv

cd /d "%~dp0"
if not exist slots mkdir slots
if not exist data mkdir data

rem engine: one slot, 32K window (raise -c if you have the memory; add -ngl 99 for a GPU build)
start "llama-server" "%LLAMA%" -m "%MODEL%" -c 32768 --parallel 1 --jinja --slot-save-path .\slots --port 8095

rem wait for the engine, then check the setup once (exit code 0 = ready, 2 = warnings, 1 = not ready)
:wait
ping -n 3 127.0.0.1 >nul
curl -sf http://127.0.0.1:8095/health >nul 2>&1 || goto wait
"%VENV%\Scripts\mnemonic-proxy.exe" check --upstream http://127.0.0.1:8095 --data .\data --config "%CONFIG%"
if %errorlevel% equ 1 (
  echo mnemonic-proxy check: NOT READY, see above
  pause
  exit /b 1
)

rem proxy: point the agent at http://127.0.0.1:8096/v1
"%VENV%\Scripts\mnemonic-proxy.exe" --upstream http://127.0.0.1:8095 --port 8096 --data .\data --config "%CONFIG%"
