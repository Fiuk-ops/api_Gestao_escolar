@echo off
setlocal EnableExtensions
title Sistema de Gestao Escolar - Servidor

REM Sempre executa a partir da pasta onde este arquivo esta salvo.
cd /d "%~dp0"

REM Prioriza ambientes virtuais do proprio projeto.
set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist "venv\Scripts\python.exe" set "PYTHON_CMD=venv\Scripts\python.exe"

REM Se nao houver ambiente virtual, usa o Python instalado no Windows.
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo.
    echo Python nao foi encontrado.
    echo Instale o Python 3.11 ou superior e execute este arquivo novamente.
    echo.
    pause
    exit /b 1
)

echo.
echo Iniciando o Sistema de Gestao Escolar...
echo Quando aparecer "Running on", abra: http://localhost:5000
echo Para encerrar o servidor, pressione Ctrl+C nesta janela.
echo.

%PYTHON_CMD% app.py

echo.
echo O servidor foi encerrado.
pause
