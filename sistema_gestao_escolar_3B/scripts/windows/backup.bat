@echo off
setlocal

for %%I in ("%~dp0\..\..") do set "PROJECT_ROOT=%%~fI"
set "DATA_FILE=%PROJECT_ROOT%\data\escola.db"
set "BACKUP_DIR=%PROJECT_ROOT%\backups"

if not exist "%DATA_FILE%" (
    echo Banco não encontrado: %DATA_FILE%
    echo Inicie a aplicação ou crie os dados antes de executar o backup.
    exit /b 1
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
copy /Y "%DATA_FILE%" "%BACKUP_DIR%\escola_%STAMP%.db" >nul

echo Backup criado em: %BACKUP_DIR%\escola_%STAMP%.db
endlocal
