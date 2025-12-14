@echo off
chcp 65001 >nul
title GitHub Automation - Установка и сборка
color 0A

echo ════════════════════════════════════════════════════════════
echo     GitHub Automation - Установка зависимостей и сборка EXE
echo ════════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установите Python с https://python.org
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python найден
echo.

echo [2/4] Обновление pip...
python -m pip install --upgrade pip
echo.

echo [3/4] Установка зависимостей...
echo.
echo    - customtkinter (GUI библиотека)
pip install customtkinter
echo.
echo    - requests (HTTP запросы)
pip install requests
echo.
echo    - pyinstaller (сборка EXE)
pip install pyinstaller
echo.
echo    - pillow (работа с изображениями)
pip install pillow
echo.

echo [OK] Все зависимости установлены!
echo.

echo ════════════════════════════════════════════════════════════
echo [4/4] Сборка EXE файла...
echo ════════════════════════════════════════════════════════════
echo.

python build_exe.py

echo.
echo ════════════════════════════════════════════════════════════
if exist "dist\GitHubAutomation.exe" (
    echo [SUCCESS] Готово! EXE файл создан:
    echo.
    echo    dist\GitHubAutomation.exe
    echo.
    echo Вы можете скопировать его куда угодно и запустить.
) else (
    echo [ERROR] Ошибка при сборке EXE файла
)
echo ════════════════════════════════════════════════════════════
echo.
pause

