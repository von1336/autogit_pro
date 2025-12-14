#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Automation Tool
Автоматизация загрузки файлов на GitHub с управлением приватностью веток
"""

import os
import sys
import io
import json

# Исправление кодировки для Windows консоли
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import requests
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import getpass
import base64
import shutil
import tempfile
import urllib.parse

class GitHubAutomation:
    def __init__(self, token: str = None, username: str = None):
        """
        Инициализация GitHub автоматизации
        
        Args:
            token: GitHub Personal Access Token
            username: GitHub username
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.username = username or os.getenv('GITHUB_USERNAME')
        self.api_base = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Automation-Tool'
        }
        
        if not self.token:
            raise ValueError("GitHub token не найден. Установите GITHUB_TOKEN или передайте token параметр")
        
        if not self.username:
            raise ValueError("GitHub username не найден. Установите GITHUB_USERNAME или передайте username параметр")

    def validate_credentials(self) -> Tuple[bool, Optional[Dict]]:
        """Проверка валидности токена и соответствия username.

        Returns:
            (ok, user_info): ok=True, если токен действителен и username совпадает.
        """
        try:
            url = f"{self.api_base}/user"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code != 200:
                return False, None
            user_info = resp.json()
            if not isinstance(user_info, dict):
                return False, None
            login = user_info.get("login")
            if not login:
                return False, None
            if self.username and login.lower() != self.username.lower():
                return False, user_info
            return True, user_info
        except Exception:
            return False, None

    def create_repository(self, repo_name: str, description: str = "", private: bool = True, 
                         auto_init: bool = True, gitignore_template: str = "Python") -> Dict:
        """
        Создание нового репозитория
        
        Args:
            repo_name: Название репозитория
            description: Описание репозитория
            private: Приватный репозиторий
            auto_init: Автоматическая инициализация с README
            gitignore_template: Шаблон .gitignore
            
        Returns:
            Dict с информацией о созданном репозитории
        """
        url = f"{self.api_base}/user/repos"
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
            "gitignore_template": gitignore_template
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            print(f"✅ Репозиторий '{repo_name}' успешно создан")
            return response.json()
        else:
            print(f"❌ Ошибка создания репозитория: {response.status_code}")
            print(response.text)
            return {}

    def upload_files(self, repo_name: str, files: List[str], branch: str = "main", 
                    commit_message: str = "Auto upload files", repo_path_base: str = "") -> bool:
        """
        Загрузка файлов и содержимого папок в репозиторий (GitHub Contents API)
        
        Args:
            repo_name: Название репозитория
            files: Список путей (файлы и/или папки)
            branch: Ветка для загрузки
            commit_message: Сообщение коммита
            repo_path_base: Базовый путь внутри репозитория (подпапка назначения)
            
        Returns:
            bool: Успешность операции
        """
        print(f"📤 Загружаю в репозиторий '{repo_name}'...")

        upload_pairs: List[Tuple[str, str]] = []  # (local_path, repo_path)

        def norm_repo_path(path: str) -> str:
            path = path.replace("\\", "/")
            while "//" in path:
                path = path.replace("//", "/")
            return path.strip("/")

        base_in_repo = norm_repo_path(repo_path_base or "")

        for input_path in files:
            if not os.path.exists(input_path):
                print(f"⚠️ Не найден путь: {input_path}")
                continue

            if os.path.isdir(input_path):
                # Рекурсивно добавляем все файлы из папки, сохраняя структуру относительно выбранной папки
                for root, _dirs, filenames in os.walk(input_path):
                    for fname in filenames:
                        local_file = os.path.join(root, fname)
                        rel = os.path.relpath(local_file, start=input_path)
                        repo_rel = norm_repo_path(rel)
                        repo_path = norm_repo_path(f"{base_in_repo}/{os.path.basename(input_path)}/{repo_rel}" if base_in_repo else f"{os.path.basename(input_path)}/{repo_rel}")
                        upload_pairs.append((local_file, repo_path))
            else:
                # Одиночный файл загружаем в базовую папку, имя файла сохраняем
                repo_path = norm_repo_path(f"{base_in_repo}/{os.path.basename(input_path)}" if base_in_repo else os.path.basename(input_path))
                upload_pairs.append((input_path, repo_path))

        for local_path, repo_path in upload_pairs:
            try:
                with open(local_path, 'rb') as f:
                    content = f.read()
                content_b64 = base64.b64encode(content).decode('utf-8')

                sha = self._get_file_sha(repo_name, repo_path, branch)

                data = {
                    "message": commit_message,
                    "content": content_b64,
                    "branch": branch
                }
                if sha:
                    data["sha"] = sha

                url = f"{self.api_base}/repos/{self.username}/{repo_name}/contents/{repo_path}"
                response = requests.put(url, headers=self.headers, json=data)

                if response.status_code in [201, 200]:
                    print(f"✅ Загружено: {repo_path}")
                else:
                    print(f"❌ Ошибка загрузки '{repo_path}': {response.status_code}")
                    print(response.text)
            except Exception as e:
                print(f"❌ Ошибка при обработке '{local_path}': {str(e)}")

        return True

    def upload_files_git(self, repo_name: str, files: List[str], branch: str = "main",
                         commit_message: str = "Auto upload files", repo_path_base: str = "") -> bool:
        """
        Массовая загрузка через Git одним коммитом. Сохраняет структуру папок.

        Args:
            repo_name: Название репозитория
            files: Пути к файлам и/или папкам
            branch: Целевая ветка
            commit_message: Сообщение коммита
            repo_path_base: Базовый путь внутри репозитория
        """
        print(f"📦 Подготовка массовой загрузки в '{repo_name}' ветка '{branch}' (git)...")

        # Подготовка временной директории и клонирование
        temp_dir = tempfile.mkdtemp(prefix="gh-auto-")
        repo_dir = os.path.join(temp_dir, repo_name)

        # Безопасная авторизация в URL
        quoted_user = urllib.parse.quote(self.username or "")
        quoted_token = urllib.parse.quote(self.token or "")
        remote_url = f"https://{quoted_user}:{quoted_token}@github.com/{self.username}/{repo_name}.git"

        def run_git(args, cwd=None, check=True):
            return subprocess.run(["git"] + args, cwd=cwd, check=check, capture_output=True, text=True)

        try:
            # Пытаемся клонировать указанную ветку, если нет — клонируем по умолчанию
            try:
                run_git(["clone", "--depth", "1", "--branch", branch, remote_url, repo_dir])
            except subprocess.CalledProcessError:
                run_git(["clone", remote_url, repo_dir])
                # Создаём ветку, если отсутствует
                run_git(["checkout", "-B", branch], cwd=repo_dir)

            # Создаём базовую папку назначения
            def norm_repo(p: str) -> str:
                p = p.replace("\\", "/").strip("/")
                return p
            base_in_repo = norm_repo(repo_path_base or "")
            dest_root = os.path.join(repo_dir, base_in_repo) if base_in_repo else repo_dir
            os.makedirs(dest_root, exist_ok=True)

            def copy_into_repo(input_path: str):
                if os.path.isdir(input_path):
                    top_name = os.path.basename(os.path.normpath(input_path))
                    for root, _dirs, filenames in os.walk(input_path):
                        # пропустить .git
                        if ".git" in root.split(os.sep):
                            continue
                        rel = os.path.relpath(root, start=input_path)
                        rel = "" if rel == "." else rel
                        target_dir = os.path.join(dest_root, top_name, rel) if rel else os.path.join(dest_root, top_name)
                        os.makedirs(target_dir, exist_ok=True)
                        for fname in filenames:
                            src_file = os.path.join(root, fname)
                            dst_file = os.path.join(target_dir, fname)
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            shutil.copy2(src_file, dst_file)
                else:
                    # одиночный файл
                    os.makedirs(dest_root, exist_ok=True)
                    dst_file = os.path.join(dest_root, os.path.basename(input_path))
                    shutil.copy2(input_path, dst_file)

            for p in files:
                if not os.path.exists(p):
                    print(f"⚠️ Путь не найден и будет пропущен: {p}")
                    continue
                copy_into_repo(p)

            # Коммит и push
            run_git(["add", "."], cwd=repo_dir)
            # Проверка наличия изменений
            status = run_git(["status", "--porcelain"], cwd=repo_dir)
            if not status.stdout.strip():
                print("ℹ️ Нет изменений для коммита")
                return True
            run_git(["commit", "-m", commit_message], cwd=repo_dir)
            run_git(["push", "-u", "origin", branch], cwd=repo_dir)
            print("✅ Массовая загрузка завершена (один коммит)")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка Git: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _get_file_sha(self, repo_name: str, file_path: str, branch: str) -> Optional[str]:
        """Получение SHA файла для обновления"""
        try:
            url = f"{self.api_base}/repos/{self.username}/{repo_name}/contents/{file_path}"
            params = {"ref": branch}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json().get("sha")
        except:
            pass
        return None

    def create_branch(self, repo_name: str, branch_name: str, source_branch: str = "main") -> bool:
        """
        Создание новой ветки
        
        Args:
            repo_name: Название репозитория
            branch_name: Название новой ветки
            source_branch: Исходная ветка
            
        Returns:
            bool: Успешность операции
        """
        # Получаем SHA последнего коммита в source_branch
        url = f"{self.api_base}/repos/{self.username}/{repo_name}/git/refs/heads/{source_branch}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Не удалось получить информацию о ветке '{source_branch}'")
            return False
        
        sha = response.json()["object"]["sha"]
        
        # Создаем новую ветку
        url = f"{self.api_base}/repos/{self.username}/{repo_name}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            print(f"✅ Ветка '{branch_name}' создана")
            return True
        else:
            print(f"❌ Ошибка создания ветки: {response.status_code}")
            print(response.text)
            return False

    def set_branch_protection(self, repo_name: str, branch_name: str, 
                             require_reviews: bool = True, 
                             dismiss_stale_reviews: bool = True,
                             require_code_owner_reviews: bool = False,
                             required_approving_review_count: int = 1) -> bool:
        """
        Настройка защиты ветки
        
        Args:
            repo_name: Название репозитория
            branch_name: Название ветки
            require_reviews: Требовать ревью
            dismiss_stale_reviews: Отклонять устаревшие ревью
            require_code_owner_reviews: Требовать ревью владельца кода
            required_approving_review_count: Количество необходимых одобрений
            
        Returns:
            bool: Успешность операции
        """
        url = f"{self.api_base}/repos/{self.username}/{repo_name}/branches/{branch_name}/protection"
        
        data = {
            "required_status_checks": None,
            "enforce_admins": False,
            "required_pull_request_reviews": {
                "required_approving_review_count": required_approving_review_count,
                "dismiss_stale_reviews": dismiss_stale_reviews,
                "require_code_owner_reviews": require_code_owner_reviews
            } if require_reviews else None,
            "restrictions": None
        }
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Защита ветки '{branch_name}' настроена")
            return True
        else:
            print(f"❌ Ошибка настройки защиты ветки: {response.status_code}")
            print(response.text)
            return False

    def create_pull_request(self, repo_name: str, title: str, body: str, 
                           head_branch: str, base_branch: str = "main") -> Dict:
        """
        Создание Pull Request
        
        Args:
            repo_name: Название репозитория
            title: Заголовок PR
            body: Описание PR
            head_branch: Ветка с изменениями
            base_branch: Целевая ветка
            
        Returns:
            Dict с информацией о PR
        """
        url = f"{self.api_base}/repos/{self.username}/{repo_name}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            pr_data = response.json()
            print(f"✅ Pull Request создан: {pr_data['html_url']}")
            return pr_data
        else:
            print(f"❌ Ошибка создания PR: {response.status_code}")
            print(response.text)
            return {}

    def list_repositories(self) -> List[Dict]:
        """Получение списка репозиториев пользователя"""
        url = f"{self.api_base}/user/repos"
        params = {"per_page": 100, "sort": "updated"}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения списка репозиториев: {response.status_code}")
            return []

    def delete_repository(self, repo_name: str) -> bool:
        """
        Удаление репозитория
        
        Args:
            repo_name: Название репозитория
            
        Returns:
            bool: Успешность операции
        """
        url = f"{self.api_base}/repos/{self.username}/{repo_name}"
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 204:
            print(f"✅ Репозиторий '{repo_name}' удален")
            return True
        else:
            print(f"❌ Ошибка удаления репозитория: {response.status_code}")
            return False

    def get_repository_info(self, repo_name: str) -> Dict:
        """Получение информации о репозитории"""
        url = f"{self.api_base}/repos/{self.username}/{repo_name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения информации о репозитории: {response.status_code}")
            return {}

    def update_repository_settings(self, repo_name: str, private: bool = None, 
                                 description: str = None, homepage: str = None) -> bool:
        """
        Обновление настроек репозитория
        
        Args:
            repo_name: Название репозитория
            private: Приватность репозитория
            description: Описание
            homepage: Домашняя страница
            
        Returns:
            bool: Успешность операции
        """
        url = f"{self.api_base}/repos/{self.username}/{repo_name}"
        data = {}
        
        if private is not None:
            data["private"] = private
        if description is not None:
            data["description"] = description
        if homepage is not None:
            data["homepage"] = homepage
        
        if not data:
            return True
        
        response = requests.patch(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Настройки репозитория '{repo_name}' обновлены")
            return True
        else:
            print(f"❌ Ошибка обновления настроек: {response.status_code}")
            print(response.text)
            return False

def main():
    """Основная функция программы"""
    parser = argparse.ArgumentParser(description="GitHub Automation Tool")
    parser.add_argument("--token", help="GitHub Personal Access Token")
    parser.add_argument("--username", help="GitHub username")
    parser.add_argument("--action", choices=[
        "create-repo", "upload-files", "create-branch", "protect-branch",
        "create-pr", "list-repos", "delete-repo", "update-settings"
    ], required=True, help="Действие для выполнения")
    
    # Параметры для создания репозитория
    parser.add_argument("--repo-name", help="Название репозитория")
    parser.add_argument("--description", help="Описание репозитория")
    parser.add_argument("--private", action="store_true", help="Приватный репозиторий")
    
    # Параметры для загрузки файлов
    parser.add_argument("--files", nargs="+", help="Список путей (файлы и/или папки) для загрузки")
    parser.add_argument("--branch", default="main", help="Ветка для загрузки")
    parser.add_argument("--commit-message", help="Сообщение коммита")
    parser.add_argument("--repo-path-base", default="", help="Базовый путь в репозитории (подпапка)")
    
    # Параметры для веток
    parser.add_argument("--branch-name", help="Название ветки")
    parser.add_argument("--source-branch", default="main", help="Исходная ветка")
    
    # Параметры для PR
    parser.add_argument("--pr-title", help="Заголовок Pull Request")
    parser.add_argument("--pr-body", help="Описание Pull Request")
    parser.add_argument("--head-branch", help="Ветка с изменениями")
    parser.add_argument("--base-branch", default="main", help="Целевая ветка")
    
    args = parser.parse_args()
    
    try:
        # Инициализация GitHub автоматизации
        github = GitHubAutomation(token=args.token, username=args.username)
        
        if args.action == "create-repo":
            if not args.repo_name:
                print("❌ Необходимо указать --repo-name")
                return
            
            repo = github.create_repository(
                repo_name=args.repo_name,
                description=args.description or "",
                private=args.private
            )
            
            if repo:
                print(f"🌐 URL репозитория: {repo.get('html_url')}")
                print(f"🔒 Приватный: {repo.get('private')}")
                print(f"📝 Описание: {repo.get('description')}")
        
        elif args.action == "upload-files":
            if not args.repo_name or not args.files:
                print("❌ Необходимо указать --repo-name и --files")
                return
            
            success = github.upload_files(
                repo_name=args.repo_name,
                files=args.files,
                branch=args.branch,
                commit_message=args.commit_message or "Auto upload files",
                repo_path_base=args.repo_path_base
            )
            
            if success:
                print("✅ Все файлы загружены успешно")
        
        elif args.action == "create-branch":
            if not args.repo_name or not args.branch_name:
                print("❌ Необходимо указать --repo-name и --branch-name")
                return
            
            github.create_branch(
                repo_name=args.repo_name,
                branch_name=args.branch_name,
                source_branch=args.source_branch
            )
        
        elif args.action == "protect-branch":
            if not args.repo_name or not args.branch_name:
                print("❌ Необходимо указать --repo-name и --branch-name")
                return
            
            github.set_branch_protection(
                repo_name=args.repo_name,
                branch_name=args.branch_name
            )
        
        elif args.action == "create-pr":
            if not all([args.repo_name, args.pr_title, args.head_branch]):
                print("❌ Необходимо указать --repo-name, --pr-title и --head-branch")
                return
            
            pr = github.create_pull_request(
                repo_name=args.repo_name,
                title=args.pr_title,
                body=args.pr_body or "",
                head_branch=args.head_branch,
                base_branch=args.base_branch
            )
        
        elif args.action == "list-repos":
            repos = github.list_repositories()
            print(f"📋 Найдено {len(repos)} репозиториев:")
            for repo in repos:
                print(f"  • {repo['name']} ({'🔒' if repo['private'] else '🌐'}) - {repo['html_url']}")
        
        elif args.action == "delete-repo":
            if not args.repo_name:
                print("❌ Необходимо указать --repo-name")
                return
            
            confirm = input(f"⚠️ Вы уверены, что хотите удалить репозиторий '{args.repo_name}'? (y/N): ")
            if confirm.lower() == 'y':
                github.delete_repository(args.repo_name)
        
        elif args.action == "update-settings":
            if not args.repo_name:
                print("❌ Необходимо указать --repo-name")
                return
            
            github.update_repository_settings(
                repo_name=args.repo_name,
                private=args.private,
                description=args.description
            )
    
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 