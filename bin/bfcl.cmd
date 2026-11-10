@echo off
REM bfcl command wrapper for cmd.exe / PowerShell (equivalent to bin/bfcl).
REM
REM Keep this file ASCII-only: cmd.exe parses .bat/.cmd as the system ANSI
REM codepage (GBK on zh-CN), so a UTF-8 Chinese path here would be garbled.
REM The venv lives under a Chinese directory, hence the ASCII junction
REM D:\bfcl-venv -> D:\py<chinese>\bfcl\.venv3
REM
REM Usage:
REM   set PATH=D:\bfcl-repro\bin;%PATH%
REM   bfcl models
REM   bfcl generate --model DeepSeek-V4.1-Flash-FC --test-category simple_python --num-threads 8
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "BFCL_PROJECT_ROOT=%ROOT%"
if "%BFCL_PYTHON%"=="" set "BFCL_PYTHON=D:\bfcl-venv\Scripts\python.exe"
"%BFCL_PYTHON%" "%ROOT%\tools\bfcl_cli.py" %*
