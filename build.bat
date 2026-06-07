@echo off
setlocal enabledelayedexpansion

REM Build script for Windows (PyInstaller)
REM Requirements: Python 3.12+ installed and available on PATH

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "VENV_DIR=.venv"
set "DIST_DIR=dist"

echo.
echo [1/4] Create venv (if missing)
if not exist "%VENV_DIR%\Scripts\python.exe" (
  py -3 -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate venv.
  exit /b 1
)

echo.
echo [2/4] Install dependencies
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

REM spaCy models like fr_core_news_lg are not meant to be installed via requirements.txt on Windows.
REM If you still have fr-core-news-lg in requirements.txt, pip will fail.
findstr /i "fr-core-news-lg" requirements.txt >nul 2>&1
if %errorlevel%==0 (
  echo ERROR: requirements.txt contains fr-core-news-lg. Remove it.
  echo Use: python -m spacy download fr_core_news_lg
  exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 exit /b 1

pip install pyinstaller
if errorlevel 1 exit /b 1

echo.
echo [3/4] Install spaCy model (fr_core_news_lg)
python -m spacy download fr_core_news_lg
if errorlevel 1 (
  echo spaCy model install failed. You can try again manually:
  echo   python -m spacy download fr_core_news_lg
  exit /b 1
)

echo.
echo [4/4] Build exe
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "build" rmdir /s /q "build"
if exist "anonymyseur.spec" del /q "anonymyseur.spec"

pyinstaller --noconfirm --onefile --name anonymyseur --hidden-import fitz --collect-all pymupdf app_gui.py
if errorlevel 1 exit /b 1

echo.
echo Done.
echo Output: %CD%\dist\anonymyseur.exe
endlocal
