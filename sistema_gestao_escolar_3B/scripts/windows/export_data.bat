@echo off
setlocal

for %%I in ("%~dp0\..\..") do set "PROJECT_ROOT=%%~fI"
set "DATABASE=%PROJECT_ROOT%\data\escola.db"
set "EXPORT_DIR=%PROJECT_ROOT%\exports"

where sqlite3 >nul 2>nul
if errorlevel 1 (
    echo O executável sqlite3 não foi encontrado no PATH.
    exit /b 1
)

if not exist "%DATABASE%" (
    echo Banco não encontrado: %DATABASE%
    exit /b 1
)

if not exist "%EXPORT_DIR%" mkdir "%EXPORT_DIR%"

for %%T in (usuarios alunos professores funcionarios cursos modulos turmas matriculas frequencias notas) do (
    sqlite3 "%DATABASE%" ".headers on" ".mode csv" ".output %EXPORT_DIR%\%%T.csv" "SELECT * FROM %%T;"
)

echo Arquivos CSV criados em: %EXPORT_DIR%
endlocal
