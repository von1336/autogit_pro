#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки exe файла GitHub Automation Tool
"""

import subprocess
import sys
import os

def install_pyinstaller():
    """Установка PyInstaller если не установлен"""
    try:
        import PyInstaller
        print("[OK] PyInstaller уже установлен")
    except ImportError:
        print("[...] Устанавливаю PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller установлен")

def build_exe():
    """Сборка exe файла"""
    # Путь к текущей директории
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    
    # Имя выходного файла
    app_name = "GitHubAutomation"
    
    # Главный скрипт
    main_script = "github_gui_ctk.py"
    
    # Иконка
    icon_path = "icon.ico"
    
    # Команда PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",           # Перезаписать без подтверждения
        "--onefile",             # Один exe файл
        "--windowed",            # Без консоли (GUI приложение)
        f"--name={app_name}",    # Имя exe файла
        f"--icon={icon_path}",   # Иконка
        "--add-data", f"github_automation.py;.",  # Добавить модуль автоматизации
        "--add-data", f"icon.ico;.",              # Добавить иконку
        "--hidden-import", "customtkinter",       # Скрытый импорт customtkinter
        "--hidden-import", "tkinter",             # Скрытый импорт tkinter
        "--hidden-import", "requests",            # Скрытый импорт requests
        "--collect-all", "customtkinter",         # Собрать все файлы customtkinter
        main_script
    ]
    
    print("=" * 60)
    print("[BUILD] Начинаю сборку exe файла...")
    print("=" * 60)
    print(f"[DIR] Рабочая директория: {current_dir}")
    print(f"[FILE] Главный скрипт: {main_script}")
    print(f"[ICON] Иконка: {icon_path}")
    print(f"[OUT] Имя выходного файла: {app_name}.exe")
    print("=" * 60)
    
    try:
        subprocess.check_call(cmd)
        print("=" * 60)
        print("[SUCCESS] Сборка завершена успешно!")
        print(f"[PATH] Exe файл находится в: {os.path.join(current_dir, 'dist', f'{app_name}.exe')}")
        print("=" * 60)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ошибка при сборке: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("    GitHub Automation - Build EXE")
    print("=" * 60)
    
    install_pyinstaller()
    build_exe()
