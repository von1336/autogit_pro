#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import webbrowser

# Исправление кодировки для Windows консоли
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import customtkinter as ctk
except ImportError:
    print("Trebuetsya paket customtkinter. Ustanovite: pip install customtkinter")
    sys.exit(1)

from github_automation import GitHubAutomation

# ═══════════════════════════════════════════════════════════════════════════════
# ОПРЕДЕЛЕНИЕ ПУТИ К ПРИЛОЖЕНИЮ (для PyInstaller)
# ═══════════════════════════════════════════════════════════════════════════════

def get_app_path():
    """
    Получить путь к директории приложения.
    Работает корректно как для .py скрипта, так и для .exe файла (PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        # Запуск из exe файла - путь к директории где лежит exe
        return os.path.dirname(sys.executable)
    else:
        # Запуск как Python скрипт
        return os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════════════
# ЦВЕТОВАЯ СХЕМА
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "bg_dark": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "border": "#30363d",
    "text_primary": "#f0f6fc",
    "text_secondary": "#8b949e",
    "accent": "#238636",
    "accent_hover": "#2ea043",
    "danger": "#da3633",
    "danger_hover": "#f85149",
    "warning": "#d29922",
    "info": "#58a6ff",
    "purple": "#8957e5",
    "sidebar": "#010409",
}

# ═══════════════════════════════════════════════════════════════════════════════
# ИКОНКИ (Unicode символы)
# ═══════════════════════════════════════════════════════════════════════════════

ICONS = {
    "upload": "📤",
    "repos": "📚",
    "create": "➕",
    "branch": "🌿",
    "pr": "🔀",
    "settings": "⚙️",
    "info": "ℹ️",
    "delete": "🗑️",
    "folder": "📁",
    "file": "📄",
    "refresh": "🔄",
    "user": "👤",
    "lock": "🔒",
    "unlock": "🌐",
    "check": "✅",
    "error": "❌",
    "warning": "⚠️",
    "star": "⭐",
    "clock": "🕐",
    "link": "🔗",
    "logout": "🚪",
    "theme": "🎨",
    "home": "🏠",
    "clear": "🧹",
}


class AnimatedButton(ctk.CTkButton):
    """Анимированная кнопка с hover-эффектом"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.default_fg = kwargs.get('fg_color', COLORS["accent"])
        self.hover_fg = kwargs.get('hover_color', COLORS["accent_hover"])
        

class SidebarButton(ctk.CTkButton):
    """Кнопка боковой панели"""
    def __init__(self, master, icon, text, command=None, **kwargs):
        super().__init__(
            master,
            text=f"{icon}  {text}",
            command=command,
            font=("Segoe UI Emoji", 13),
            fg_color="transparent",
            hover_color=COLORS["bg_tertiary"],
            anchor="w",
            height=45,
            corner_radius=8,
            **kwargs
        )
        self._is_active = False
        
    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.configure(fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        else:
            self.configure(fg_color="transparent", hover_color=COLORS["bg_tertiary"])


class StatusBar(ctk.CTkFrame):
    """Статус-бар внизу окна"""
    def __init__(self, master):
        super().__init__(master, height=30, fg_color=COLORS["bg_secondary"])
        self.grid_columnconfigure(1, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self, 
            text="Готово", 
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        
        self.progress = ctk.CTkProgressBar(self, height=3, width=150)
        self.progress.grid(row=0, column=1, padx=10, pady=5)
        self.progress.set(0)
        self.progress.grid_remove()
        
        self.user_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"]
        )
        self.user_label.grid(row=0, column=2, padx=15, pady=5, sticky="e")
        
    def set_status(self, text: str, status_type: str = "info"):
        icons = {"info": "ℹ️", "success": "✅", "error": "❌", "loading": "⏳"}
        colors = {"info": COLORS["info"], "success": COLORS["accent"], 
                  "error": COLORS["danger"], "loading": COLORS["warning"]}
        self.status_label.configure(
            text=f"{icons.get(status_type, '')} {text}",
            text_color=colors.get(status_type, COLORS["text_secondary"])
        )
        
    def set_user(self, username: str):
        self.user_label.configure(text=f"👤 {username}")
        
    def show_progress(self, show: bool = True):
        if show:
            self.progress.grid()
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.grid_remove()


class CustomFileBrowser(ctk.CTkToplevel):
    """Кастомный проводник с Ctrl+клик для выбора файлов и папок"""
    def __init__(self, master):
        super().__init__(master)
        self.title("Выберите файлы и папки")
        self.geometry("800x600")
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.selected_items = set()
        self.current_path = os.path.expanduser("~")
        self.result = None
        self.item_widgets = {}  # path -> widget frame
        
        self.transient(master)
        self.grab_set()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # === Панель навигации ===
        nav = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=0)
        nav.grid(row=0, column=0, sticky="ew")
        nav.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(nav, text="↑", width=40, height=36, font=("Segoe UI", 16),
                      fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
                      command=self._go_up).grid(row=0, column=0, padx=(10,5), pady=8)
        
        self.path_var = tk.StringVar(value=self.current_path)
        self.path_entry = ctk.CTkEntry(nav, textvariable=self.path_var, height=36,
                                        fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"])
        self.path_entry.grid(row=0, column=1, sticky="ew", pady=8)
        self.path_entry.bind("<Return>", lambda e: self._go_to(self.path_var.get()))
        
        ctk.CTkButton(nav, text="Перейти", width=80, height=36,
                      fg_color=COLORS["info"], hover_color="#4090d0",
                      command=lambda: self._go_to(self.path_var.get())).grid(row=0, column=2, padx=10, pady=8)
        
        # === Быстрые ссылки ===
        quick = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"], corner_radius=0, height=40)
        quick.grid(row=1, column=0, sticky="ew")
        
        drives_and_folders = [
            ("Рабочий стол", os.path.join(os.path.expanduser("~"), "Desktop")),
            ("Документы", os.path.join(os.path.expanduser("~"), "Documents")),
            ("Загрузки", os.path.join(os.path.expanduser("~"), "Downloads")),
        ]
        # Добавляем диски
        for letter in "CDEF":
            path = f"{letter}:/"
            if os.path.exists(path):
                drives_and_folders.append((f"Диск {letter}:", path))
        
        for name, path in drives_and_folders:
            if os.path.exists(path):
                ctk.CTkButton(quick, text=name, height=28, width=90, font=("Segoe UI", 10),
                              fg_color="transparent", hover_color=COLORS["bg_secondary"],
                              command=lambda p=path: self._go_to(p)).pack(side="left", padx=3, pady=6)
        
        # === Подсказка ===
        hint = ctk.CTkLabel(self, text="💡 Ctrl+клик для выбора нескольких | Клик на папку = войти | Ctrl+клик на папку = выбрать",
                            font=("Segoe UI", 11), text_color=COLORS["text_secondary"])
        hint.grid(row=2, column=0, sticky="ew", padx=10, pady=(10,0))
        
        # === Список файлов ===
        list_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=8)
        list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        
        self.file_list = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.file_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.file_list.grid_columnconfigure(0, weight=1)
        
        # === Панель выбора ===
        select_panel = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"], corner_radius=8)
        select_panel.grid(row=4, column=0, sticky="ew", padx=10, pady=(0,10))
        select_panel.grid_columnconfigure(0, weight=1)
        
        self.select_label = ctk.CTkLabel(select_panel, text="Выбрано: 0", font=("Segoe UI", 12))
        self.select_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        ctk.CTkButton(select_panel, text="Выбрать всё", width=110, height=32,
                      fg_color=COLORS["info"], hover_color="#4090d0",
                      command=self._select_all).grid(row=0, column=1, padx=5, pady=10)
        
        ctk.CTkButton(select_panel, text="Снять выбор", width=110, height=32,
                      fg_color=COLORS["bg_secondary"], hover_color=COLORS["border"],
                      command=self._clear_selection).grid(row=0, column=2, padx=5, pady=10)
        
        # === Кнопки действий ===
        btn_panel = ctk.CTkFrame(self, fg_color="transparent")
        btn_panel.grid(row=5, column=0, sticky="ew", padx=10, pady=(0,15))
        
        ctk.CTkButton(btn_panel, text="Отмена", width=120, height=42,
                      fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
                      command=self._cancel).pack(side="right", padx=5)
        
        ctk.CTkButton(btn_panel, text="Добавить выбранное", width=180, height=42,
                      font=("Segoe UI", 13, "bold"),
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      command=self._confirm).pack(side="right", padx=5)
        
        self._refresh()
        self._center_window()
        
    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 800) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")
        
    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self._go_to(parent)
            
    def _go_to(self, path):
        if os.path.isdir(path):
            self.current_path = os.path.normpath(path)
            self.path_var.set(self.current_path)
            self._refresh()
            # Сброс прокрутки наверх после обновления
            self.after(10, self._scroll_to_top)
    
    def _scroll_to_top(self):
        """Прокрутка списка файлов в начало"""
        try:
            self.file_list._parent_canvas.yview_moveto(0)
        except:
            pass
            
    def _refresh(self):
        # Очистка
        for w in self.file_list.winfo_children():
            w.destroy()
        self.item_widgets.clear()
        
        try:
            items = os.listdir(self.current_path)
        except PermissionError:
            ctk.CTkLabel(self.file_list, text="⛔ Нет доступа", text_color=COLORS["danger"],
                         font=("Segoe UI", 14)).grid(row=0, column=0, pady=30)
            return
        
        # Сортировка: папки сначала
        dirs = sorted([i for i in items if os.path.isdir(os.path.join(self.current_path, i)) and not i.startswith('.')], key=str.lower)
        files = sorted([i for i in items if os.path.isfile(os.path.join(self.current_path, i)) and not i.startswith('.')], key=str.lower)
        
        row = 0
        for name in dirs + files:
            full_path = os.path.join(self.current_path, name)
            is_dir = os.path.isdir(full_path)
            is_selected = full_path in self.selected_items
            
            # Создаём строку
            item_frame = ctk.CTkFrame(self.file_list, 
                                       fg_color=COLORS["accent"] if is_selected else COLORS["bg_tertiary"],
                                       corner_radius=6, height=38)
            item_frame.grid(row=row, column=0, sticky="ew", pady=2)
            item_frame.grid_columnconfigure(1, weight=1)
            item_frame.grid_propagate(False)
            
            self.item_widgets[full_path] = item_frame
            
            # Иконка
            icon = "📁" if is_dir else "📄"
            ctk.CTkLabel(item_frame, text=icon, font=("Segoe UI Emoji", 14), width=30
                        ).grid(row=0, column=0, padx=(10,5), pady=6)
            
            # Имя (кликабельное)
            name_label = ctk.CTkLabel(item_frame, text=name, font=("Segoe UI", 12),
                                       text_color="white", anchor="w", cursor="hand2")
            name_label.grid(row=0, column=1, sticky="ew", pady=6)
            
            # Привязка кликов
            name_label.bind("<Button-1>", lambda e, p=full_path, d=is_dir: self._on_click(e, p, d))
            item_frame.bind("<Button-1>", lambda e, p=full_path, d=is_dir: self._on_click(e, p, d))
            
            # Размер файла
            if not is_dir:
                try:
                    size = os.path.getsize(full_path)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024*1024:
                        size_str = f"{size//1024} KB"
                    else:
                        size_str = f"{size//(1024*1024)} MB"
                except:
                    size_str = ""
                ctk.CTkLabel(item_frame, text=size_str, font=("Segoe UI", 10),
                             text_color=COLORS["text_secondary"], width=70
                            ).grid(row=0, column=2, padx=10, pady=6)
            else:
                ctk.CTkLabel(item_frame, text="<папка>", font=("Segoe UI", 10),
                             text_color=COLORS["text_secondary"], width=70
                            ).grid(row=0, column=2, padx=10, pady=6)
            
            row += 1
            
        if row == 0:
            ctk.CTkLabel(self.file_list, text="Папка пуста", text_color=COLORS["text_secondary"],
                         font=("Segoe UI", 12)).grid(row=0, column=0, pady=30)
                         
        self._update_selection_label()
        
    def _on_click(self, event, path, is_dir):
        ctrl_pressed = event.state & 0x4  # Проверка Ctrl
        
        if ctrl_pressed:
            # Ctrl+клик = переключить выбор
            if path in self.selected_items:
                self.selected_items.remove(path)
            else:
                self.selected_items.add(path)
            self._update_item_color(path)
        else:
            if is_dir:
                # Обычный клик на папку = войти
                self._go_to(path)
            else:
                # Обычный клик на файл = выбрать только его
                self.selected_items.clear()
                self.selected_items.add(path)
                self._refresh()
                
        self._update_selection_label()
        
    def _update_item_color(self, path):
        if path in self.item_widgets:
            is_selected = path in self.selected_items
            self.item_widgets[path].configure(
                fg_color=COLORS["accent"] if is_selected else COLORS["bg_tertiary"]
            )
            
    def _select_all(self):
        try:
            for name in os.listdir(self.current_path):
                if not name.startswith('.'):
                    self.selected_items.add(os.path.join(self.current_path, name))
            self._refresh()
        except:
            pass
            
    def _clear_selection(self):
        self.selected_items.clear()
        self._refresh()
        
    def _update_selection_label(self):
        count = len(self.selected_items)
        dirs = sum(1 for p in self.selected_items if os.path.isdir(p))
        files = count - dirs
        self.select_label.configure(text=f"Выбрано: {count} (папок: {dirs}, файлов: {files})")
        
    def _cancel(self):
        self.result = None
        self.destroy()
        
    def _confirm(self):
        self.result = list(self.selected_items)
        self.destroy()
        
    def get_result(self):
        self.wait_window()
        return self.result


class FileDropZone(ctk.CTkFrame):
    """Зона для добавления файлов с визуальным оформлением"""
    def __init__(self, master, on_files_added=None):
        super().__init__(
            master, 
            fg_color=COLORS["bg_tertiary"],
            corner_radius=12,
            border_width=2,
            border_color=COLORS["border"]
        )
        self.on_files_added = on_files_added
        self.selected_paths = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header,
            text="📁 Файлы и папки для загрузки",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w")
        
        self.count_label = ctk.CTkLabel(
            header,
            text="0 элементов",
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"]
        )
        self.count_label.grid(row=0, column=1, sticky="e", padx=10)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e")
        
        # Одна кнопка "Добавить" - открывает кастомный проводник
        self.add_btn = ctk.CTkButton(
            btn_frame,
            text="+ Добавить",
            width=130,
            height=38,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._open_browser
        )
        self.add_btn.pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="Очистить",
            width=90,
            height=38,
            font=("Segoe UI", 12),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            command=self._clear
        ).pack(side="left", padx=2)
        
        # Список файлов
        list_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=8)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        self.scrollable = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["text_secondary"]
        )
        self.scrollable.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.scrollable.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        self.placeholder = ctk.CTkLabel(
            self.scrollable,
            text="Нажмите '+ Добавить' чтобы открыть проводник\n\nCtrl+клик — выбрать несколько файлов/папок\nКлик на папку — войти в неё | Ctrl+клик на папку — выбрать",
            font=("Segoe UI", 12),
            text_color=COLORS["text_secondary"],
            justify="center"
        )
        self.placeholder.grid(row=0, column=0, pady=40)
        
    def _open_browser(self):
        """Открыть кастомный проводник для выбора файлов и папок"""
        browser = CustomFileBrowser(self.winfo_toplevel())
        result = browser.get_result()
        if result:
            self._add_paths(result)
            
    def _add_paths(self, paths):
        for p in paths:
            if p not in self.selected_paths:
                self.selected_paths.append(p)
        self._refresh_list()
        if self.on_files_added:
            self.on_files_added(self.selected_paths)
            
    def _clear(self):
        self.selected_paths = []
        self._refresh_list()
        if self.on_files_added:
            self.on_files_added(self.selected_paths)
            
    def _remove_path(self, path):
        if path in self.selected_paths:
            self.selected_paths.remove(path)
        self._refresh_list()
        if self.on_files_added:
            self.on_files_added(self.selected_paths)
            
    def _refresh_list(self):
        for widget in self.scrollable.winfo_children():
            widget.destroy()
            
        if not self.selected_paths:
            self.placeholder = ctk.CTkLabel(
                self.scrollable,
                text="Нажмите '+ Добавить' чтобы открыть проводник\n\nCtrl+клик — выбрать несколько файлов/папок\nКлик на папку — войти в неё | Ctrl+клик на папку — выбрать",
                font=("Segoe UI", 12),
                text_color=COLORS["text_secondary"],
                justify="center"
            )
            self.placeholder.grid(row=0, column=0, pady=40)
            self.count_label.configure(text="0 элементов")
            return
            
        self.count_label.configure(text=f"{len(self.selected_paths)} элементов")
        
        for i, path in enumerate(self.selected_paths):
            item = ctk.CTkFrame(self.scrollable, fg_color=COLORS["bg_tertiary"], corner_radius=6, height=36)
            item.grid(row=i, column=0, sticky="ew", pady=2)
            item.grid_columnconfigure(1, weight=1)
            
            is_dir = os.path.isdir(path)
            icon = "📁" if is_dir else "📄"
            
            # Считаем файлы в папке
            if is_dir:
                file_count = sum(len(files) for _, _, files in os.walk(path))
                size_text = f"({file_count} файлов)"
            else:
                size = os.path.getsize(path)
                if size < 1024:
                    size_text = f"({size} B)"
                elif size < 1024 * 1024:
                    size_text = f"({size // 1024} KB)"
                else:
                    size_text = f"({size // (1024 * 1024)} MB)"
            
            ctk.CTkLabel(
                item,
                text=icon,
                font=("Segoe UI Emoji", 14),
                width=30
            ).grid(row=0, column=0, padx=(10, 5), pady=8)
            
            ctk.CTkLabel(
                item,
                text=os.path.basename(path),
                font=("Segoe UI", 12),
                text_color=COLORS["text_primary"],
                anchor="w"
            ).grid(row=0, column=1, sticky="w", pady=8)
            
            ctk.CTkLabel(
                item,
                text=size_text,
                font=("Segoe UI", 10),
                text_color=COLORS["text_secondary"]
            ).grid(row=0, column=2, padx=10, pady=8)
            
            ctk.CTkButton(
                item,
                text="✕",
                width=28,
                height=28,
                font=("Segoe UI", 12),
                fg_color="transparent",
                hover_color=COLORS["danger"],
                command=lambda p=path: self._remove_path(p)
            ).grid(row=0, column=3, padx=5, pady=4)


class LoginFrame(ctk.CTkFrame):
    """Экран входа"""
    def __init__(self, master, on_success_login):
        super().__init__(master, fg_color=COLORS["bg_dark"])
        self.on_success_login = on_success_login
        self._config_path = os.path.join(get_app_path(), 'user_config.json')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Центральная карточка
        card = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=16, width=420)
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)
        
        # Логотип
        ctk.CTkLabel(
            card,
            text="🐙",
            font=("Segoe UI Emoji", 64)
        ).grid(row=0, column=0, pady=(40, 10))
        
        ctk.CTkLabel(
            card,
            text="GitHub Automation",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=1, column=0, pady=(0, 5))
        
        ctk.CTkLabel(
            card,
            text="Войдите в свой аккаунт GitHub",
            font=("Segoe UI", 13),
            text_color=COLORS["text_secondary"]
        ).grid(row=2, column=0, pady=(0, 30))
        
        # Поля ввода
        input_frame = ctk.CTkFrame(card, fg_color="transparent")
        input_frame.grid(row=3, column=0, padx=40, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            input_frame,
            text="👤 Username",
            font=("Segoe UI Emoji", 12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.username_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите ваш GitHub username",
            height=45,
            font=("Segoe UI", 13),
            corner_radius=8,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_tertiary"]
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        
        ctk.CTkLabel(
            input_frame,
            text="🔑 Token",
            font=("Segoe UI Emoji", 12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        ).grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        self.token_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите ваш Personal Access Token",
            show="•",
            height=45,
            font=("Segoe UI", 13),
            corner_radius=8,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_tertiary"]
        )
        self.token_entry.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        
        self.remember_var = tk.BooleanVar(value=True)
        self.remember_check = ctk.CTkCheckBox(
            input_frame,
            text="Запомнить меня",
            variable=self.remember_var,
            font=("Segoe UI", 12),
            checkbox_height=20,
            checkbox_width=20,
            corner_radius=4,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.remember_check.grid(row=4, column=0, sticky="w", pady=(0, 20))
        
        self.login_button = ctk.CTkButton(
            input_frame,
            text="Войти",
            height=48,
            font=("Segoe UI", 14, "bold"),
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._handle_login
        )
        self.login_button.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        
        # Ссылка на создание токена
        link_btn = ctk.CTkButton(
            input_frame,
            text="🔗 Как получить токен?",
            font=("Segoe UI Emoji", 11),
            fg_color="transparent",
            hover_color=COLORS["bg_tertiary"],
            text_color=COLORS["info"],
            command=lambda: webbrowser.open("https://github.com/settings/tokens/new")
        )
        link_btn.grid(row=6, column=0, pady=(0, 30))
        
        self._load_saved()
        
    def _handle_login(self):
        username = self.username_entry.get().strip()
        token = self.token_entry.get().strip()
        
        if not username or not token:
            messagebox.showwarning("Внимание", "Введите username и token")
            return
            
        self.login_button.configure(state="disabled", text="Проверка...")
        
        def worker():
            try:
                gh = GitHubAutomation(token=token, username=username)
                ok, user_info = gh.validate_credentials()
                if not ok:
                    self.after(0, lambda: messagebox.showerror("Ошибка", "Неверный токен или username"))
                    self.after(0, lambda: self.login_button.configure(state="normal", text="Войти"))
                    return
                if self.remember_var.get():
                    os.environ['GITHUB_TOKEN'] = token
                    os.environ['GITHUB_USERNAME'] = username
                    self._save({'username': username, 'token': token})
                else:
                    self._clear_saved()
                self.after(0, lambda: self.on_success_login(gh, user_info or {}))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.login_button.configure(state="normal", text="Войти"))
                
        threading.Thread(target=worker, daemon=True).start()
        
    def _load_saved(self):
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                username = data.get('username') or ""
                token = data.get('token') or ""
                if username:
                    self.username_entry.delete(0, tk.END)
                    self.username_entry.insert(0, username)
                if token:
                    self.token_entry.delete(0, tk.END)
                    self.token_entry.insert(0, token)
                self.remember_var.set(True if username and token else False)
        except Exception:
            pass
            
    def _save(self, data: dict):
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    def _clear_saved(self):
        try:
            if os.path.exists(self._config_path):
                os.remove(self._config_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ПАНЕЛИ ФУНКЦИЙ
# ═══════════════════════════════════════════════════════════════════════════════

class UploadPanel(ctk.CTkFrame):
    """Панель загрузки файлов"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        self.selected_paths = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(
            header,
            text="📤 Загрузка файлов",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")
        
        # Настройки
        settings = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        settings.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Репозиторий
        ctk.CTkLabel(settings, text="Репозиторий", font=("Segoe UI", 12), 
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        repo_frame = ctk.CTkFrame(settings, fg_color="transparent")
        repo_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        repo_frame.grid_columnconfigure(0, weight=1)
        
        self.repo_option = ctk.CTkOptionMenu(
            repo_frame,
            values=["Загрузка..."],
            font=("Segoe UI", 12),
            height=38,
            corner_radius=8,
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["text_secondary"]
        )
        self.repo_option.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(
            repo_frame,
            text="🔄",
            width=40,
            height=38,
            font=("Segoe UI Emoji", 14),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            command=self._refresh_repos
        ).grid(row=0, column=1, padx=(5, 0))
        
        # Ветка
        ctk.CTkLabel(settings, text="Ветка", font=("Segoe UI", 12),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=1, padx=15, pady=(15, 5), sticky="w")
        self.branch_entry = ctk.CTkEntry(
            settings, placeholder_text="main", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.branch_entry.insert(0, "main")
        self.branch_entry.grid(row=1, column=1, padx=15, pady=(0, 15), sticky="ew")
        
        # Путь в репо
        ctk.CTkLabel(settings, text="Путь в репозитории", font=("Segoe UI", 12),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=2, padx=15, pady=(15, 5), sticky="w")
        self.base_path_entry = ctk.CTkEntry(
            settings, placeholder_text="папка/назначения", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.base_path_entry.grid(row=1, column=2, padx=15, pady=(0, 15), sticky="ew")
        
        # Сообщение коммита
        ctk.CTkLabel(settings, text="Сообщение коммита", font=("Segoe UI", 12),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=3, padx=15, pady=(15, 5), sticky="w")
        self.commit_entry = ctk.CTkEntry(
            settings, placeholder_text="Auto upload files", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.commit_entry.grid(row=1, column=3, padx=15, pady=(0, 15), sticky="ew")
        
        # Зона файлов
        self.file_zone = FileDropZone(self, on_files_added=self._on_files_changed)
        self.file_zone.grid(row=2, column=0, sticky="nsew", pady=(0, 15))
        
        # Нижняя панель с опциями и кнопкой
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)
        
        self.use_git_var = tk.BooleanVar(value=True)  # По умолчанию Git (быстрее для больших файлов)
        ctk.CTkCheckBox(
            bottom,
            text="Использовать Git (требуется установка Git, быстрее для больших файлов)",
            variable=self.use_git_var,
            font=("Segoe UI", 12),
            checkbox_height=22,
            checkbox_width=22,
            corner_radius=4,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        ).grid(row=0, column=0, sticky="w")
        
        self.upload_btn = ctk.CTkButton(
            bottom,
            text="📤 Загрузить на GitHub",
            height=48,
            width=220,
            font=("Segoe UI Emoji", 14, "bold"),
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._upload
        )
        self.upload_btn.grid(row=0, column=1, sticky="e")
        
        self._refresh_repos()
        
    def _on_files_changed(self, paths):
        self.selected_paths = paths
        
    def _refresh_repos(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass  # Игнорируем ошибки если виджет уничтожен
        threading.Thread(target=worker, daemon=True).start()
        
    def _upload(self):
        repo = self.repo_option.get().strip()
        if not repo or repo.startswith("<"):
            messagebox.showwarning("Внимание", "Выберите репозиторий")
            return
        if not self.selected_paths:
            messagebox.showwarning("Внимание", "Добавьте файлы или папки")
            return
            
        branch = self.branch_entry.get().strip() or "main"
        base = self.base_path_entry.get().strip()
        msg = self.commit_entry.get().strip() or "Auto upload files"
        
        self.upload_btn.configure(state="disabled", text="⏳ Загрузка...")
        self.status_bar.set_status("Загрузка файлов...", "loading")
        self.status_bar.show_progress(True)
        
        def worker():
            try:
                if self.use_git_var.get():
                    ok = self.gh.upload_files_git(repo_name=repo, files=self.selected_paths, 
                                                   branch=branch, commit_message=msg, repo_path_base=base)
                else:
                    ok = self.gh.upload_files(repo_name=repo, files=self.selected_paths,
                                               branch=branch, commit_message=msg, repo_path_base=base)
                if ok:
                    self.after(0, lambda: self.status_bar.set_status("Загрузка завершена!", "success"))
                    self.after(0, lambda: messagebox.showinfo("Готово", "Загрузка завершена успешно!"))
            except Exception as e:
                self.after(0, lambda: self.status_bar.set_status(f"Ошибка: {str(e)}", "error"))
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.upload_btn.configure(state="normal", text="📤 Загрузить на GitHub"))
                self.after(0, lambda: self.status_bar.show_progress(False))
                
        threading.Thread(target=worker, daemon=True).start()


class ReposPanel(ctk.CTkFrame):
    """Панель списка репозиториев"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header,
            text="📚 Мои репозитории",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w")
        
        self.count_label = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 12),
            text_color=COLORS["text_secondary"]
        )
        self.count_label.grid(row=0, column=1, sticky="w", padx=15)
        
        ctk.CTkButton(
            header,
            text="🔄 Обновить",
            width=120,
            height=38,
            font=("Segoe UI Emoji", 12),
            fg_color=COLORS["bg_secondary"],
            hover_color=COLORS["bg_tertiary"],
            command=self._refresh
        ).grid(row=0, column=2, sticky="e")
        
        # Список
        self.scrollable = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["text_secondary"]
        )
        self.scrollable.grid(row=1, column=0, sticky="nsew")
        self.scrollable.grid_columnconfigure(0, weight=1)
        
        self._refresh()
        
    def _refresh(self):
        if not self.winfo_exists():
            return
        self.status_bar.set_status("Загрузка репозиториев...", "loading")
        
        def worker():
            try:
                repos = self.gh.list_repositories()
                def apply():
                    if self.winfo_exists():
                        self._fill(repos)
                        self.status_bar.set_status("Готово", "success")
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _fill(self, repos):
        for widget in self.scrollable.winfo_children():
            widget.destroy()
            
        self.count_label.configure(text=f"{len(repos)} репозиториев")
        
        for i, repo in enumerate(repos):
            card = ctk.CTkFrame(self.scrollable, fg_color=COLORS["bg_tertiary"], corner_radius=10, height=70)
            card.grid(row=i, column=0, sticky="ew", pady=5, padx=10)
            card.grid_columnconfigure(1, weight=1)
            
            # Иконка
            icon = "🔒" if repo.get('private') else "🌐"
            ctk.CTkLabel(
                card,
                text=icon,
                font=("Segoe UI Emoji", 24)
            ).grid(row=0, column=0, rowspan=2, padx=15, pady=15)
            
            # Название
            ctk.CTkLabel(
                card,
                text=repo.get('name', ''),
                font=("Segoe UI", 14, "bold"),
                text_color=COLORS["text_primary"],
                anchor="w"
            ).grid(row=0, column=1, sticky="sw", pady=(15, 0))
            
            # Описание
            desc = repo.get('description') or "Без описания"
            ctk.CTkLabel(
                card,
                text=desc[:60] + "..." if len(desc) > 60 else desc,
                font=("Segoe UI", 11),
                text_color=COLORS["text_secondary"],
                anchor="w"
            ).grid(row=1, column=1, sticky="nw", pady=(0, 15))
            
            # Статистика
            stats = ctk.CTkFrame(card, fg_color="transparent")
            stats.grid(row=0, column=2, rowspan=2, padx=15)
            
            ctk.CTkLabel(
                stats,
                text=f"⭐ {repo.get('stargazers_count', 0)}",
                font=("Segoe UI Emoji", 11),
                text_color=COLORS["text_secondary"]
            ).pack(side="left", padx=5)
            
            ctk.CTkLabel(
                stats,
                text=f"🍴 {repo.get('forks_count', 0)}",
                font=("Segoe UI Emoji", 11),
                text_color=COLORS["text_secondary"]
            ).pack(side="left", padx=5)
            
            # Кнопка открыть
            ctk.CTkButton(
                card,
                text="🔗",
                width=40,
                height=40,
                font=("Segoe UI Emoji", 16),
                fg_color=COLORS["info"],
                hover_color="#4090d0",
                corner_radius=8,
                command=lambda url=repo.get('html_url'): webbrowser.open(url)
            ).grid(row=0, column=3, rowspan=2, padx=15)


class CreateRepoPanel(ctk.CTkFrame):
    """Панель создания репозитория"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="➕ Создать репозиторий",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Форма
        form = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        
        # Название
        ctk.CTkLabel(form, text="📝 Название репозитория", font=("Segoe UI Emoji", 13),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.name_entry = ctk.CTkEntry(
            form, placeholder_text="my-awesome-project", height=45, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"], font=("Segoe UI", 13)
        )
        self.name_entry.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        # Описание
        ctk.CTkLabel(form, text="📄 Описание", font=("Segoe UI Emoji", 13),
                     text_color=COLORS["text_secondary"]).grid(row=2, column=0, padx=20, pady=(0, 5), sticky="w")
        self.desc_entry = ctk.CTkEntry(
            form, placeholder_text="Краткое описание проекта...", height=45, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"], font=("Segoe UI", 13)
        )
        self.desc_entry.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        # Опции
        options = ctk.CTkFrame(form, fg_color="transparent")
        options.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        
        self.private_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options,
            text="🔒 Приватный репозиторий",
            variable=self.private_var,
            font=("Segoe UI Emoji", 13),
            checkbox_height=22,
            checkbox_width=22,
            corner_radius=4,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        ).pack(side="left")
        
        self.create_btn = ctk.CTkButton(
            options,
            text="➕ Создать",
            height=45,
            width=150,
            font=("Segoe UI Emoji", 14, "bold"),
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._create
        )
        self.create_btn.pack(side="right")
        
    def _create(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Введите название репозитория")
            return
            
        desc = self.desc_entry.get().strip()
        private = self.private_var.get()
        
        self.create_btn.configure(state="disabled", text="⏳ Создание...")
        self.status_bar.set_status("Создание репозитория...", "loading")
        
        def worker():
            try:
                repo = self.gh.create_repository(repo_name=name, description=desc, private=private)
                if repo:
                    url = repo.get('html_url', '')
                    self.after(0, lambda: self.status_bar.set_status("Репозиторий создан!", "success"))
                    self.after(0, lambda: messagebox.showinfo("Готово", f"Репозиторий создан!\n{url}"))
                    self.after(0, lambda: self.name_entry.delete(0, tk.END))
                    self.after(0, lambda: self.desc_entry.delete(0, tk.END))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.status_bar.set_status("Ошибка", "error"))
            finally:
                self.after(0, lambda: self.create_btn.configure(state="normal", text="➕ Создать"))
                
        threading.Thread(target=worker, daemon=True).start()


class BranchesPanel(ctk.CTkFrame):
    """Панель управления ветками"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="🌿 Управление ветками",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Создание ветки
        create_card = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        create_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        create_card.grid_columnconfigure((1, 2, 3), weight=1)
        
        ctk.CTkLabel(create_card, text="➕ Создать ветку", font=("Segoe UI Emoji", 16, "bold"),
                     text_color=COLORS["text_primary"]).grid(row=0, column=0, columnspan=4, padx=20, pady=(15, 10), sticky="w")
        
        ctk.CTkLabel(create_card, text="Репозиторий", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        repo_frame = ctk.CTkFrame(create_card, fg_color="transparent")
        repo_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        self.repo_option = ctk.CTkOptionMenu(
            repo_frame, values=["Загрузка..."], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.repo_option.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(
            repo_frame, text="🔄", width=40, height=38,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            command=self._refresh
        ).pack(side="left", padx=(5, 0))
        
        ctk.CTkLabel(create_card, text="Исходная ветка", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=1, column=1, padx=10, pady=(0, 5), sticky="w")
        self.source_entry = ctk.CTkEntry(
            create_card, placeholder_text="main", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.source_entry.insert(0, "main")
        self.source_entry.grid(row=2, column=1, padx=10, pady=(0, 15), sticky="ew")
        
        ctk.CTkLabel(create_card, text="Новая ветка", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=1, column=2, padx=10, pady=(0, 5), sticky="w")
        self.new_branch_entry = ctk.CTkEntry(
            create_card, placeholder_text="feature-name", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.new_branch_entry.grid(row=2, column=2, padx=10, pady=(0, 15), sticky="ew")
        
        self.create_branch_btn = ctk.CTkButton(
            create_card, text="Создать", height=38, width=120,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._create_branch
        )
        self.create_branch_btn.grid(row=2, column=3, padx=20, pady=(0, 15))
        
        # Защита ветки
        protect_card = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        protect_card.grid(row=2, column=0, sticky="ew")
        protect_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(protect_card, text="🛡️ Защита ветки", font=("Segoe UI Emoji", 16, "bold"),
                     text_color=COLORS["text_primary"]).grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        ctk.CTkLabel(protect_card, text="Ветка для защиты", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        self.branch_protect_entry = ctk.CTkEntry(
            protect_card, placeholder_text="main", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.branch_protect_entry.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        self.protect_btn = ctk.CTkButton(
            protect_card, text="🛡️ Включить защиту", height=38, width=160,
            fg_color=COLORS["warning"], hover_color="#c08820",
            command=self._protect_branch
        )
        self.protect_btn.grid(row=2, column=2, padx=20, pady=(0, 15))
        
        self._refresh()
        
    def _refresh(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _create_branch(self):
        repo = self.repo_option.get().strip()
        source = self.source_entry.get().strip() or "main"
        newb = self.new_branch_entry.get().strip()
        
        if not repo or not newb:
            messagebox.showwarning("Внимание", "Укажите репозиторий и имя ветки")
            return
            
        self.create_branch_btn.configure(state="disabled")
        self.status_bar.set_status("Создание ветки...", "loading")
        
        def worker():
            try:
                ok = self.gh.create_branch(repo_name=repo, branch_name=newb, source_branch=source)
                if ok:
                    self.after(0, lambda: self.status_bar.set_status("Ветка создана!", "success"))
                    self.after(0, lambda: messagebox.showinfo("Готово", f"Ветка '{newb}' создана"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.status_bar.set_status("Ошибка", "error"))
            finally:
                self.after(0, lambda: self.create_branch_btn.configure(state="normal"))
        threading.Thread(target=worker, daemon=True).start()
        
    def _protect_branch(self):
        repo = self.repo_option.get().strip()
        br = self.branch_protect_entry.get().strip()
        
        if not repo or not br:
            messagebox.showwarning("Внимание", "Укажите репозиторий и ветку")
            return
            
        self.protect_btn.configure(state="disabled")
        
        def worker():
            try:
                ok = self.gh.set_branch_protection(repo_name=repo, branch_name=br)
                if ok:
                    self.after(0, lambda: messagebox.showinfo("Готово", "Защита включена"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.protect_btn.configure(state="normal"))
        threading.Thread(target=worker, daemon=True).start()


class PullRequestPanel(ctk.CTkFrame):
    """Панель создания Pull Request"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="🔀 Создать Pull Request",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Форма
        form = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure((0, 1), weight=1)
        
        # Репозиторий
        ctk.CTkLabel(form, text="Репозиторий", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        repo_frame = ctk.CTkFrame(form, fg_color="transparent")
        repo_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        repo_frame.grid_columnconfigure(0, weight=1)
        
        self.repo_option = ctk.CTkOptionMenu(
            repo_frame, values=["Загрузка..."], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.repo_option.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(
            repo_frame, text="🔄", width=40, height=38,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            command=self._refresh
        ).grid(row=0, column=1, padx=(5, 0))
        
        # Заголовок PR
        ctk.CTkLabel(form, text="Заголовок PR", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")
        self.title_entry = ctk.CTkEntry(
            form, placeholder_text="Добавлен новый функционал...", height=42, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.title_entry.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        # Описание
        ctk.CTkLabel(form, text="Описание", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")
        self.body_entry = ctk.CTkEntry(
            form, placeholder_text="Подробное описание изменений...", height=42, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.body_entry.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        # Ветки
        ctk.CTkLabel(form, text="Head ветка (откуда)", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=6, column=0, padx=20, pady=(0, 5), sticky="w")
        self.head_entry = ctk.CTkEntry(
            form, placeholder_text="feature-branch", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.head_entry.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        ctk.CTkLabel(form, text="Base ветка (куда)", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=6, column=1, padx=20, pady=(0, 5), sticky="w")
        self.base_entry = ctk.CTkEntry(
            form, placeholder_text="main", height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.base_entry.insert(0, "main")
        self.base_entry.grid(row=7, column=1, padx=20, pady=(0, 20), sticky="ew")
        
        # Кнопка
        self.create_btn = ctk.CTkButton(
            form, text="🔀 Создать Pull Request", height=48, width=220,
            font=("Segoe UI Emoji", 14, "bold"), corner_radius=8,
            fg_color=COLORS["purple"], hover_color="#7048c5",
            command=self._create_pr
        )
        self.create_btn.grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 20))
        
        self._refresh()
        
    def _refresh(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _create_pr(self):
        repo = self.repo_option.get().strip()
        title = self.title_entry.get().strip()
        body = self.body_entry.get().strip()
        head = self.head_entry.get().strip()
        base = self.base_entry.get().strip() or "main"
        
        if not repo or not title or not head:
            messagebox.showwarning("Внимание", "Заполните репозиторий, заголовок и head ветку")
            return
            
        self.create_btn.configure(state="disabled", text="⏳ Создание...")
        
        def worker():
            try:
                pr = self.gh.create_pull_request(repo_name=repo, title=title, body=body,
                                                  head_branch=head, base_branch=base)
                if pr:
                    url = pr.get('html_url', '')
                    self.after(0, lambda: messagebox.showinfo("Готово", f"PR создан!\n{url}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.create_btn.configure(state="normal", text="🔀 Создать Pull Request"))
        threading.Thread(target=worker, daemon=True).start()


class SettingsPanel(ctk.CTkFrame):
    """Панель настроек репозитория"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="⚙️ Настройки репозитория",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Форма
        form = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        
        # Репозиторий
        ctk.CTkLabel(form, text="Репозиторий", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        repo_frame = ctk.CTkFrame(form, fg_color="transparent")
        repo_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        repo_frame.grid_columnconfigure(0, weight=1)
        
        self.repo_option = ctk.CTkOptionMenu(
            repo_frame, values=["Загрузка..."], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.repo_option.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(
            repo_frame, text="🔄", width=40, height=38,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            command=self._refresh
        ).grid(row=0, column=1, padx=(5, 0))
        
        # Описание
        ctk.CTkLabel(form, text="Новое описание", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")
        self.desc_entry = ctk.CTkEntry(
            form, placeholder_text="Введите новое описание...", height=42, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"]
        )
        self.desc_entry.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        
        # Приватность
        ctk.CTkLabel(form, text="Видимость", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=4, column=0, padx=20, pady=(0, 5), sticky="w")
        self.private_menu = ctk.CTkOptionMenu(
            form, values=["без изменений", "🔒 Private", "🌐 Public"], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.private_menu.set("без изменений")
        self.private_menu.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.update_btn = ctk.CTkButton(
            form, text="💾 Сохранить изменения", height=45, width=200,
            font=("Segoe UI Emoji", 13, "bold"), corner_radius=8,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._update
        )
        self.update_btn.grid(row=5, column=1, padx=20, pady=(0, 20), sticky="e")
        
        self._refresh()
        
    def _refresh(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _update(self):
        repo = self.repo_option.get().strip()
        if not repo:
            messagebox.showwarning("Внимание", "Выберите репозиторий")
            return
            
        desc = self.desc_entry.get().strip()
        priv_text = self.private_menu.get()
        private = None
        if "Private" in priv_text:
            private = True
        elif "Public" in priv_text:
            private = False
            
        self.update_btn.configure(state="disabled")
        
        def worker():
            try:
                ok = self.gh.update_repository_settings(repo_name=repo, private=private,
                                                         description=desc if desc else None)
                if ok:
                    self.after(0, lambda: messagebox.showinfo("Готово", "Настройки обновлены"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.update_btn.configure(state="normal"))
        threading.Thread(target=worker, daemon=True).start()


class InfoPanel(ctk.CTkFrame):
    """Панель информации о репозитории"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="ℹ️ Информация о репозитории",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Выбор репо
        select_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        select_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        select_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(select_frame, text="Репозиторий", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        self.repo_option = ctk.CTkOptionMenu(
            select_frame, values=["Загрузка..."], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.repo_option.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        ctk.CTkButton(
            select_frame, text="🔄", width=40, height=38,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            command=self._refresh
        ).grid(row=0, column=2, padx=(0, 10), pady=15)
        
        ctk.CTkButton(
            select_frame, text="📊 Показать информацию", height=38, width=180,
            fg_color=COLORS["info"], hover_color="#4090d0",
            command=self._show
        ).grid(row=0, column=3, padx=(0, 20), pady=15)
        
        # Информация
        self.info_text = ctk.CTkTextbox(
            self, fg_color=COLORS["bg_secondary"], corner_radius=12,
            font=("Consolas", 12), text_color=COLORS["text_primary"]
        )
        self.info_text.grid(row=2, column=0, sticky="nsew")
        
        self._refresh()
        
    def _refresh(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _show(self):
        repo = self.repo_option.get().strip()
        if not repo:
            messagebox.showwarning("Внимание", "Выберите репозиторий")
            return
            
        self.status_bar.set_status("Загрузка информации...", "loading")
        
        def worker():
            try:
                info = self.gh.get_repository_info(repo_name=repo)
                self.after(0, lambda: self._fill(info))
                self.after(0, lambda: self.status_bar.set_status("Готово", "success"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.status_bar.set_status("Ошибка", "error"))
        threading.Thread(target=worker, daemon=True).start()
        
    def _fill(self, info):
        self.info_text.delete("1.0", tk.END)
        import json as _json
        self.info_text.insert("1.0", _json.dumps(info, ensure_ascii=False, indent=2))


class DeletePanel(ctk.CTkFrame):
    """Панель удаления репозитория"""
    def __init__(self, master, gh: GitHubAutomation, status_bar: StatusBar):
        super().__init__(master, fg_color="transparent")
        self.gh = gh
        self.status_bar = status_bar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Заголовок
        ctk.CTkLabel(
            self,
            text="🗑️ Удаление репозитория",
            font=("Segoe UI Emoji", 24, "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Предупреждение
        warning = ctk.CTkFrame(self, fg_color="#2d1f1f", corner_radius=12, border_width=2, border_color=COLORS["danger"])
        warning.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(
            warning,
            text="⚠️ Внимание! Удаление репозитория необратимо!",
            font=("Segoe UI Emoji", 14, "bold"),
            text_color=COLORS["danger"]
        ).pack(padx=20, pady=15)
        
        ctk.CTkLabel(
            warning,
            text="Все файлы, история коммитов, issues и pull requests будут удалены навсегда.",
            font=("Segoe UI", 12),
            text_color=COLORS["text_secondary"]
        ).pack(padx=20, pady=(0, 15))
        
        # Форма
        form = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=12)
        form.grid(row=2, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(form, text="Выберите репозиторий для удаления", font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")
        
        self.repo_option = ctk.CTkOptionMenu(
            form, values=["Загрузка..."], height=38, corner_radius=8,
            fg_color=COLORS["bg_tertiary"], button_color=COLORS["border"]
        )
        self.repo_option.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        
        ctk.CTkButton(
            form, text="🔄", width=40, height=38,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            command=self._refresh
        ).grid(row=1, column=2, padx=(5, 20), pady=(0, 20))
        
        self.delete_btn = ctk.CTkButton(
            form, text="🗑️ Удалить репозиторий", height=48, width=220,
            font=("Segoe UI Emoji", 14, "bold"), corner_radius=8,
            fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"],
            command=self._delete
        )
        self.delete_btn.grid(row=2, column=0, columnspan=3, padx=20, pady=(0, 20))
        
        self._refresh()
        
    def _refresh(self):
        def worker():
            try:
                repos = self.gh.list_repositories()
                names = [r.get('name', '') for r in repos if r.get('name')]
                if not names:
                    names = ["<нет репозиториев>"]
                def apply():
                    if self.winfo_exists():
                        self.repo_option.configure(values=names)
                        self.repo_option.set(names[0])
                self.after(0, apply)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        
    def _delete(self):
        repo = self.repo_option.get().strip()
        if not repo:
            messagebox.showwarning("Внимание", "Выберите репозиторий")
            return
            
        if not messagebox.askyesno("Подтверждение", 
            f"Вы уверены, что хотите УДАЛИТЬ репозиторий '{repo}'?\n\nЭто действие НЕОБРАТИМО!"):
            return
            
        self.delete_btn.configure(state="disabled", text="⏳ Удаление...")
        self.status_bar.set_status("Удаление репозитория...", "loading")
        
        def worker():
            try:
                ok = self.gh.delete_repository(repo)
                if ok:
                    self.after(0, lambda: self.status_bar.set_status("Репозиторий удалён", "success"))
                    self.after(0, lambda: messagebox.showinfo("Готово", f"Репозиторий '{repo}' удалён"))
                    self.after(0, self._refresh)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.status_bar.set_status("Ошибка", "error"))
            finally:
                self.after(0, lambda: self.delete_btn.configure(state="normal", text="🗑️ Удалить репозиторий"))
        threading.Thread(target=worker, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GitHub Automation Pro")
        self.geometry("1200x750")
        self.minsize(1000, 600)
        
        # Тёмная тема
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.gh = None
        self.user_info = {}
        self.current_panel = None
        self.sidebar_buttons = {}
        
        self._show_login()
        
    def _show_login(self):
        for child in self.winfo_children():
            child.destroy()
            
        login = LoginFrame(self, on_success_login=self._on_login_success)
        login.pack(fill="both", expand=True)
        
    def _on_login_success(self, gh: GitHubAutomation, user_info):
        try:
            self.gh = gh
            self.user_info = user_info
            self._show_main()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Ошибка", f"Ошибка при загрузке интерфейса:\n{str(e)}")
        
    def _show_main(self):
        for child in self.winfo_children():
            child.destroy()
            
        # Основной контейнер
        main_container = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # ══════════════════════════════════════════════════════════
        # БОКОВАЯ ПАНЕЛЬ СПРАВА
        # ══════════════════════════════════════════════════════════
        
        sidebar = ctk.CTkFrame(main_container, fg_color=COLORS["sidebar"], width=220, corner_radius=0)
        sidebar.grid(row=0, column=2, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Логотип и пользователь
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=20)
        
        ctk.CTkLabel(
            header,
            text="🐙 GitHub Pro",
            font=("Segoe UI Emoji", 18, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        
        user_name = self.user_info.get('login', self.gh.username)
        ctk.CTkLabel(
            header,
            text=f"👤 {user_name}",
            font=("Segoe UI Emoji", 12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(5, 0))
        
        # Разделитель
        ctk.CTkFrame(sidebar, fg_color=COLORS["border"], height=1).pack(fill="x", padx=15, pady=10)
        
        # Навигационные кнопки
        nav_items = [
            ("upload", ICONS["upload"], "Загрузка", UploadPanel),
            ("repos", ICONS["repos"], "Репозитории", ReposPanel),
            ("create", ICONS["create"], "Создать репозиторий", CreateRepoPanel),
            ("branch", ICONS["branch"], "Ветки", BranchesPanel),
            ("pr", ICONS["pr"], "Pull Request", PullRequestPanel),
            ("settings", ICONS["settings"], "Настройки", SettingsPanel),
            ("info", ICONS["info"], "Информация", InfoPanel),
            ("delete", ICONS["delete"], "Удалить", DeletePanel),
        ]
        
        for key, icon, text, panel_class in nav_items:
            btn = SidebarButton(sidebar, icon, text, command=lambda k=key, pc=panel_class: self._switch_panel(k, pc))
            btn.pack(fill="x", padx=10, pady=2)
            self.sidebar_buttons[key] = btn
            
        # Нижняя часть сайдбара
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        
        # Разделитель
        ctk.CTkFrame(sidebar, fg_color=COLORS["border"], height=1).pack(fill="x", padx=15, pady=10)
        
        # Тема
        theme_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(
            theme_frame,
            text="🎨 Тема",
            font=("Segoe UI Emoji", 11),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")
        
        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="",
            width=40,
            onvalue="light",
            offvalue="dark",
            command=self._toggle_theme,
            fg_color=COLORS["border"],
            progress_color=COLORS["accent"]
        )
        self.theme_switch.pack(side="right")
        
        # Выход
        ctk.CTkButton(
            sidebar,
            text="🚪 Выйти",
            font=("Segoe UI Emoji", 12),
            fg_color="transparent",
            hover_color=COLORS["bg_tertiary"],
            anchor="w",
            height=40,
            command=self._logout
        ).pack(fill="x", padx=10, pady=(5, 15))
        
        # ══════════════════════════════════════════════════════════
        # ОСНОВНАЯ ОБЛАСТЬ
        # ══════════════════════════════════════════════════════════
        
        content_area = ctk.CTkFrame(main_container, fg_color=COLORS["bg_dark"])
        content_area.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=25, pady=(20, 0))
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_rowconfigure(0, weight=1)
        
        self.content_frame = content_area
        
        # Статус-бар
        self.status_bar = StatusBar(main_container)
        self.status_bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.status_bar.set_user(user_name)
        
        # Показать панель загрузки по умолчанию
        self._switch_panel("upload", UploadPanel)
        
    def _switch_panel(self, key: str, panel_class):
        # Убираем старую панель
        for child in self.content_frame.winfo_children():
            child.destroy()
            
        # Обновляем активную кнопку
        for k, btn in self.sidebar_buttons.items():
            btn.set_active(k == key)
            
        # Создаём новую панель
        panel = panel_class(self.content_frame, self.gh, self.status_bar)
        panel.grid(row=0, column=0, sticky="nsew")
        self.current_panel = panel
        
    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "light" if current == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        
    def _logout(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.gh = None
            self.user_info = {}
            self._show_login()


def main():
    try:
        app = MainApp()
        app.mainloop()
    except Exception as e:
        import traceback
        print("=" * 50)
        print("ERROR:")
        traceback.print_exc()
        print("=" * 50)
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
