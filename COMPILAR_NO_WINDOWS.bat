@echo off
REM ============================================================
REM  Compila o OpenFFBoard Configurator (visual SimPro) no Windows
REM  Usa a mesma receita oficial do projeto: build\OpenFFBoard.spec
REM  Resultado: build\dist\OpenFFBoard\OpenFFBoard.exe
REM ============================================================
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao encontrado.
    echo Instale o Python 3.12 em https://www.python.org/downloads/windows/
    echo e MARQUE a opcao "Add python.exe to PATH" na primeira tela do instalador.
    echo Depois rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/4] Criando ambiente isolado de compilacao (.venv_build)...
if not exist ".venv_build\Scripts\python.exe" (
    python -m venv .venv_build
    if errorlevel 1 goto :erro
)
call ".venv_build\Scripts\activate.bat"

echo.
echo [2/4] Instalando dependencias (pode demorar alguns minutos)...
python -m pip install --upgrade pip
if errorlevel 1 goto :erro
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :erro

echo.
echo [3/4] Compilando...
cd build
pyinstaller --noconfirm OpenFFBoard.spec
if errorlevel 1 goto :erro

echo.
echo [4/4] Pronto!
echo O programa esta em: %CD%\dist\OpenFFBoard\OpenFFBoard.exe
echo (copie a pasta "OpenFFBoard" inteira; o .exe precisa dos arquivos ao lado dele)
explorer "%CD%\dist\OpenFFBoard"
echo.
pause
exit /b 0

:erro
echo.
echo [ERRO] A compilacao falhou. Tire um print desta janela e envie.
pause
exit /b 1
