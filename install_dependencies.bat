@echo off
chcp 65001 >nul
title GitHub Automation - Установка зависимостей
color 0A

echo ════════════════════════════════════════════════════════════
echo     GitHub Automation - Установка зависимостей
echo ════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! 
    echo.
    echo Скачайте и установите Python с https://python.org
    echo При установке обязательно отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python найден
echo.

echo Обновление pip...
python -m pip install --upgrade pip
echo.

echo Установка зависимостей из requirements.txt...
pip install -r requirements.txt

echo.
echo ════════════════════════════════════════════════════════════
echo [OK] Все зависимости установлены!
echo.
echo Теперь вы можете:
echo   - Запустить приложение: python github_gui_ctk.py
echo   - Собрать EXE: build_exe.bat
echo   - Или всё вместе: install_and_build.bat
echo ════════════════════════════════════════════════════════════
echo.
pause

