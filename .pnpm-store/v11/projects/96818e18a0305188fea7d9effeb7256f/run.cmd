@echo off
setlocal
cd /d "%~dp0"
set "HEPIC_NODE=node"
where node.exe >nul 2>&1
if not errorlevel 1 goto check_version
set "HEPIC_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
if not exist "%HEPIC_NODE%" goto missing_node
for %%I in ("%HEPIC_NODE%") do set "PATH=%%~dpI;%PATH%"

:check_version
"%HEPIC_NODE%" -e "const [major,minor]=process.versions.node.split('.').map(Number); if(major<22||(major===22&&minor<13)){console.error('HEPIC requer Node.js 22.13 ou superior.');process.exit(1);}"
if errorlevel 1 exit /b 1
if "%~1"=="" goto start_local
"%HEPIC_NODE%" %*
exit /b %ERRORLEVEL%

:start_local
"%HEPIC_NODE%" scripts\local.mjs
exit /b %ERRORLEVEL%

:missing_node
echo Node.js nao encontrado no PATH nem no runtime do Codex.
echo Instale Node.js 22.13 ou superior e abra um novo terminal.
exit /b 1
