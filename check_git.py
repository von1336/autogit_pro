#!/usr/bin/env python3
"""
Скрипт для проверки установки Git и настройки
"""

import subprocess
import sys
import os

def check_git_installation():
    """Проверка установки Git"""
    print("🔍 Проверка установки Git...")
    
    try:
        result = subprocess.run(["git", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Git установлен: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("❌ Git не найден в системе")
        return False
    except FileNotFoundError:
        print("❌ Git не установлен")
        return False

def check_git_config():
    """Проверка настройки Git"""
    print("\n🔍 Проверка настройки Git...")
    
    configs = {
        "user.name": "Имя пользователя",
        "user.email": "Email пользователя"
    }
    
    all_configured = True
    
    for config_key, config_name in configs.items():
        try:
            result = subprocess.run(["git", "config", "--global", config_key], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ {config_name}: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print(f"❌ {config_name}: не настроен")
            all_configured = False
    
    return all_configured

def setup_git_config():
    """Настройка Git конфигурации"""
    print("\n🔧 Настройка Git конфигурации...")
    
    name = input("Введите ваше имя для Git: ")
    email = input("Введите ваш email для Git: ")
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", name], check=True)
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)
        print("✅ Git конфигурация настроена успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка настройки Git: {e}")
        return False

def test_git_operations():
    """Тест основных Git операций"""
    print("\n🧪 Тест Git операций...")
    
    # Создаем временную директорию для теста
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        os.chdir(temp_dir)
        
        # Инициализация Git репозитория
        subprocess.run(["git", "init"], check=True, capture_output=True)
        print("✅ Git репозиторий инициализирован")
        
        # Создание тестового файла
        with open("test.txt", "w") as f:
            f.write("Тестовый файл")
        
        # Добавление файла в Git
        subprocess.run(["git", "add", "test.txt"], check=True, capture_output=True)
        print("✅ Файл добавлен в Git")
        
        # Создание коммита
        subprocess.run(["git", "commit", "-m", "Тестовый коммит"], 
                      check=True, capture_output=True)
        print("✅ Коммит создан успешно")
        
        print("✅ Все Git операции работают корректно!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка в Git операциях: {e}")
        return False
    finally:
        # Очистка временной директории
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """Основная функция"""
    print("🚀 Проверка системы для GitHub Automation Tool")
    print("=" * 50)
    
    # Проверка установки Git
    git_installed = check_git_installation()
    
    if not git_installed:
        print("\n📥 Для установки Git:")
        print("1. Перейдите на https://git-scm.com/downloads")
        print("2. Скачайте и установите Git для вашей системы")
        print("3. Перезапустите этот скрипт")
        return
    
    # Проверка конфигурации Git
    git_configured = check_git_config()
    
    if not git_configured:
        print("\n🔧 Git не настроен. Хотите настроить сейчас? (y/n): ", end="")
        if input().lower() == 'y':
            if setup_git_config():
                git_configured = True
            else:
                print("❌ Не удалось настроить Git")
                return
        else:
            print("⚠️ Настройте Git вручную:")
            print("git config --global user.name 'Ваше имя'")
            print("git config --global user.email 'ваш@email.com'")
            return
    
    # Тест Git операций
    if git_configured:
        test_git_operations()
    
    print("\n" + "=" * 50)
    print("✅ Система готова к работе с GitHub Automation Tool!")
    print("🎉 Теперь вы можете загружать файлы как обычные файлы в репозитории")

if __name__ == "__main__":
    main() 