# --- DEBUG: Начало скрипта ---
print("[DEBUG] 1. Скрипт main.py начал выполняться")

import sys
import os
import re
import subprocess
# import shutil # Закомментирован, т.к. не используется

# --- DEBUG: После базовых импортов ---
print("[DEBUG] 2. Базовые импорты выполнены (sys, os, re, subprocess)")

# --- НЕОБХОДИМЫЕ ИМПОРТЫ PyQt6 ---
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QListWidget, QLabel, QPlainTextEdit, QMessageBox,
        QTabWidget, QFileDialog, QLineEdit, QGroupBox, QStyle, QSpacerItem,
        QSizePolicy
    )
    from PyQt6.QtCore import QThread, pyqtSignal, Qt, QObject
    from PyQt6.QtGui import QIcon, QPixmap

    # --- DEBUG: После импортов PyQt ---
    print("[DEBUG] 3. Импорты PyQt6 выполнены успешно")

    # Попытка импорта qt-material (но использовать не будем)
    try:
        # from qt_material import apply_stylesheet # Закомментировано, т.к. не используется
        QT_MATERIAL_AVAILABLE = True
        print("[DEBUG] 3.1 qt_material найден (но не используется)")
    except ImportError:
        QT_MATERIAL_AVAILABLE = False
        print("[DEBUG] 3.1 qt_material не найден.")

except ImportError as e:
    print(f"[DEBUG] КРИТИЧЕСКАЯ ОШИБКА: Не удалось импортировать PyQt6 или его компоненты.")
    print(f"[DEBUG] Текст ошибки: {e}")
    sys.exit(1)
# --- КОНЕЦ НЕОБХОДИМЫХ ИМПОРТОВ ---


# --- Функция поиска исполняемых файлов ---
def find_executable(name):
    """Ищет исполняемый файл в подпапке platform-tools относительно скрипта или exe."""
    executable_path = None
    print(f"\n[DEBUG] --- Поиск '{name}' ---") # Отступ исправлен

    if getattr(sys, 'frozen', False):
        # Если приложение "заморожено" (скомпилировано в exe)
        if hasattr(sys, '_MEIPASS'):
            # Режим PyInstaller onefile
            basedir = sys._MEIPASS
            print(f"[DEBUG] Режим: Frozen (onefile), basedir (_MEIPASS): {basedir}")
        else:
            # Режим PyInstaller onefolder
            basedir = os.path.dirname(sys.executable)
            print(f"[DEBUG] Режим: Frozen (folder), basedir (executable): {basedir}")
    else:
        # Обычный режим запуска скрипта .py
        basedir = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] Режим: Скрипт PY, basedir (__file__): {basedir}")

    tools_subdir = 'platform-tools'
    tools_path = os.path.join(basedir, tools_subdir)
    print(f"[DEBUG] Ожидаемая папка с инструментами: {tools_path}")

    exe_name = f'{name}.exe' if os.name == 'nt' else name
    full_exe_path = os.path.join(tools_path, exe_name)
    print(f"[DEBUG] Полный ожидаемый путь к файлу: {full_exe_path}")

    if os.path.isfile(full_exe_path):
        executable_path = full_exe_path
        print(f"[DEBUG] УСПЕХ: Файл '{name}' найден по пути: {executable_path}")
    else:
        if not os.path.isdir(tools_path):
            print(f"[DEBUG] ОШИБКА: Папка '{tools_path}' не существует!")
        else:
            print(f"[DEBUG] ОШИБКА: Файл '{exe_name}' не найден в папке '{tools_path}'.")

    print("[DEBUG] --- Конец поиска ---")
    return executable_path


# --- Класс для выполнения команд в потоке ---
class CommandWorker(QThread):
    result_ready = pyqtSignal(str, str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    command_info = pyqtSignal(list) # Сигнал с выполняемой командой

    def __init__(self, executable_path, command_args):
        super().__init__()
        self.command_args = command_args
        self.executable_path = executable_path
        print(f"[DEBUG] CommandWorker создан для: {' '.join(self.command_args)}")

    def run(self):
        print(f"[DEBUG] CommandWorker: Запуск потока для команды: {' '.join(self.command_args)}")
        self.command_info.emit(self.command_args) # Отправляем команду

        if not self.executable_path or not os.path.isfile(self.executable_path):
            error_msg = f"Ошибка потока: Путь '{self.executable_path}' недействителен."
            print(error_msg)
            self.error_occurred.emit(error_msg)
            self.finished.emit()
            return

        try:
            print(f"[DEBUG] CommandWorker: Выполнение subprocess.run для: {' '.join(self.command_args)}")
            startupinfo = None
            if os.name == 'nt':
                # Скрытие окна консоли в Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.wShowWindow = subprocess.SW_HIDE
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                self.command_args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace', # Замена некорректных символов
                check=False, # Не вызывать исключение при ненулевом коде возврата
                startupinfo=startupinfo
            )
            stdout = process.stdout
            stderr = process.stderr
            print(f"[DEBUG] CommandWorker: Команда завершена.")
            # Отправляем результат независимо от кода возврата
            self.result_ready.emit(stdout, stderr)

        except FileNotFoundError:
            error_msg = f"Ошибка потока FileNotFoundError: Не найден исполняемый файл {self.command_args[0]}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"Непредвиденная ошибка потока: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            print("[DEBUG] CommandWorker: Поток завершает работу (блок finally)")
            self.finished.emit()


# --- Основной класс окна приложения ---
class MainWindow(QMainWindow):
    def __init__(self):
        print("[DEBUG] MainWindow: Начало __init__")
        super().__init__()
        self.setWindowTitle("ADB & Fastboot GUI Tool v1.1(4PDA)") # Оставляем ваше название
        self.setGeometry(150, 150, 850, 750) # Немного увеличил ширину по умолчанию

        self.adb_path = None
        self.fastboot_path = None
        self.current_worker = None
        self.last_started_command = None # Храним саму команду (список аргументов)
        self.devices_found_list = [] # Список серийников найденных устройств (для ADB)

        # Переменные для хранения путей к файлам/папкам
        self.local_file_to_push = ""
        self.local_folder_to_pull = ""
        self.apk_to_install = ""
        self.fb_image_to_flash = ""
        self.fb_kernel_to_boot = ""
        self.selected_fb_partition = None # <<< НОВАЯ ПЕРЕМЕННАЯ для хранения выбранного раздела
        self.partition_buttons = {} # <<< НОВЫЙ СЛОВАРЬ для кнопок разделов

        # Определение basedir для иконок
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                basedir = sys._MEIPASS
            else:
                basedir = os.path.dirname(sys.executable)
        else:
            basedir = os.path.dirname(os.path.abspath(__file__))

        # Иконка ОКНА
        icon_filename = '4pda_icon.png'
        icon_path = os.path.join(basedir, icon_filename)
        print(f"[DEBUG] Попытка загрузки иконки ОКНА из: {icon_path}")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            print(f"[DEBUG] Установлена иконка ОКНА: {icon_path}")
        else:
            print(f"[DEBUG] Файл иконки ОКНА '{icon_path}' не найден.")

        print("[DEBUG] MainWindow: Вызов find_tools()")
        self.find_tools()
        print("[DEBUG] MainWindow: Вызов setup_ui()")
        self.setup_ui()
        print("[DEBUG] MainWindow: Конец __init__")

    def find_tools(self):
        """Ищет adb и fastboot при запуске."""
        print("[DEBUG] MainWindow.find_tools: Начало поиска инструментов")
        self.adb_path = find_executable('adb')
        self.fastboot_path = find_executable('fastboot')
        print(f"[DEBUG] MainWindow.find_tools: ADB='{self.adb_path}', Fastboot='{self.fastboot_path}'")

    def setup_ui(self):
        """Создает элементы интерфейса."""
        print("[DEBUG] MainWindow.setup_ui: Начало настройки UI")
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- Верхняя строка статуса (БЕЗ БАТАРЕИ) ---
        top_status_layout = QHBoxLayout()

        # Логотип в UI
        self.logo_label = QLabel()
        logo_icon_filename = '4pda_icon.png'
        logo_max_height = 24 # Макс. высота лого

        # Определение basedir (повторно, т.к. find_tools может быть вызван позже)
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'): basedir = sys._MEIPASS
            else: basedir = os.path.dirname(sys.executable)
        else: basedir = os.path.dirname(os.path.abspath(__file__))

        logo_icon_path = os.path.join(basedir, logo_icon_filename)
        print(f"[DEBUG] Попытка загрузки логотипа UI из: {logo_icon_path}")
        if os.path.isfile(logo_icon_path):
            try:
                pixmap = QPixmap(logo_icon_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaledToHeight(logo_max_height, Qt.TransformationMode.SmoothTransformation)
                    self.logo_label.setPixmap(pixmap)
                    self.logo_label.setToolTip("Логотип 4PDA")
                    print(f"[DEBUG] Логотип UI загружен.")
                else:
                    print(f"[DEBUG] Ошибка QPixmap: не удалось загрузить изображение из {logo_icon_path}")
                    self.logo_label.setText("[logo?]")
                    self.logo_label.setToolTip(f"Ошибка загрузки {logo_icon_path}")
            except Exception as e:
                print(f"[DEBUG] Исключение при загрузке логотипа: {e}")
                self.logo_label.setText("[logo err]")
                self.logo_label.setToolTip(f"Ошибка загрузки логотипа: {e}")
        else:
            print(f"[DEBUG] Файл логотипа UI не найден: {logo_icon_path}")
            self.logo_label.setText(" ") # Пусто, если нет лого
            self.logo_label.setToolTip(f"Файл {logo_icon_path} не найден")

        top_status_layout.addWidget(self.logo_label)
        top_status_layout.addSpacing(10)

        # Статусы ADB / Fastboot
        adb_status_text = f"ADB: {self.adb_path or 'Не найден'}"
        self.adb_status_label = QLabel(adb_status_text)
        self.adb_status_label.setStyleSheet("color: green;" if self.adb_path else "color: red;")
        self.adb_status_label.setToolTip(self.adb_path or "Исполняемый файл adb не найден")

        fastboot_status_text = f"Fastboot: {self.fastboot_path or 'Не найден'}"
        self.fastboot_status_label = QLabel(fastboot_status_text)
        self.fastboot_status_label.setStyleSheet("color: green;" if self.fastboot_path else "color: red;")
        self.fastboot_status_label.setToolTip(self.fastboot_path or "Исполняемый файл fastboot не найден")

        top_status_layout.addWidget(self.adb_status_label)
        top_status_layout.addWidget(self.fastboot_status_label)
        top_status_layout.addStretch(1) # Растягиваем пространство до правого края

        main_layout.addLayout(top_status_layout)

        # --- Вкладки ---
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Вкладка ADB ---
        self.adb_tab = QWidget()
        self.tab_widget.addTab(self.adb_tab, "ADB")
        adb_main_layout = QVBoxLayout(self.adb_tab)

        # Группа Устройства ADB
        adb_device_group = QGroupBox("Устройства ADB")
        adb_main_layout.addWidget(adb_device_group)
        adb_device_layout = QVBoxLayout(adb_device_group)
        adb_device_buttons_layout = QHBoxLayout()
        self.refresh_adb_button = QPushButton("Обновить ADB устр-ва")
        self.refresh_adb_button.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)))
        self.refresh_adb_button.setEnabled(bool(self.adb_path))
        self.refresh_adb_button.clicked.connect(self.refresh_adb_devices)
        adb_device_buttons_layout.addWidget(self.refresh_adb_button)
        adb_device_buttons_layout.addStretch(1)
        adb_device_layout.addLayout(adb_device_buttons_layout)
        self.adb_device_list_widget = QListWidget()
        self.adb_device_list_widget.setToolTip("Список устройств ADB. Выберите устройство для команд.")
        adb_device_layout.addWidget(self.adb_device_list_widget)

        # Группа Перезагрузка (ADB)
        adb_reboot_group = QGroupBox("Перезагрузка")
        adb_main_layout.addWidget(adb_reboot_group)
        adb_reboot_layout = QHBoxLayout(adb_reboot_group)
        self.reboot_button = QPushButton("Перезагрузка")
        self.reboot_button.setToolTip("adb reboot")
        self.reboot_button.setEnabled(bool(self.adb_path))
        self.reboot_button.clicked.connect(self.run_simple_adb_command_reboot)
        adb_reboot_layout.addWidget(self.reboot_button)
        self.reboot_recovery_button = QPushButton("В Recovery")
        self.reboot_recovery_button.setToolTip("adb reboot recovery")
        self.reboot_recovery_button.setEnabled(bool(self.adb_path))
        self.reboot_recovery_button.clicked.connect(self.run_simple_adb_command_recovery)
        adb_reboot_layout.addWidget(self.reboot_recovery_button)
        self.reboot_bootloader_button = QPushButton("В Bootloader")
        self.reboot_bootloader_button.setToolTip("adb reboot bootloader")
        self.reboot_bootloader_button.setEnabled(bool(self.adb_path))
        self.reboot_bootloader_button.clicked.connect(self.run_simple_adb_command_bootloader)
        adb_reboot_layout.addWidget(self.reboot_bootloader_button)
        adb_reboot_layout.addStretch(1)

        # Группа Копирование файлов (ADB)
        adb_files_group = QGroupBox("Копирование файлов")
        adb_main_layout.addWidget(adb_files_group)
        adb_files_layout = QVBoxLayout(adb_files_group)
        # -- Push --
        push_select_layout = QHBoxLayout() # Отдельный layout для выбора файла
        self.select_file_push_button = QPushButton("Выбрать файл (Push)")
        self.select_file_push_button.setToolTip("Выбрать локальный файл для отправки на устройство.")
        self.select_file_push_button.setEnabled(bool(self.adb_path))
        self.select_file_push_button.clicked.connect(self.select_local_file_push)
        push_select_layout.addWidget(self.select_file_push_button)
        self.local_file_push_label = QLabel("Файл не выбран")
        push_select_layout.addWidget(self.local_file_push_label, 1) # Растягиваем метку
        adb_files_layout.addLayout(push_select_layout)

        push_dest_layout = QHBoxLayout() # Отдельный layout для пути назначения и кнопки
        push_dest_layout.addWidget(QLabel("Путь на устр-ве:"))
        self.remote_path_push_edit = QLineEdit()
        self.remote_path_push_edit.setPlaceholderText("/sdcard/Download/")
        self.remote_path_push_edit.setToolTip("Куда скопировать файл на устройстве.")
        self.remote_path_push_edit.setEnabled(bool(self.adb_path))
        push_dest_layout.addWidget(self.remote_path_push_edit, 1) # Растягиваем поле ввода
        self.push_button = QPushButton("Отправить (Push)")
        self.push_button.setToolTip("Скопировать выбранный файл на устройство.")
        self.push_button.setEnabled(bool(self.adb_path))
        self.push_button.clicked.connect(self.push_file_to_device)
        push_dest_layout.addWidget(self.push_button)
        adb_files_layout.addLayout(push_dest_layout)

        # Добавим разделитель для ясности
        # spacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        # adb_files_layout.addSpacerItem(spacer)

        # -- Pull --
        pull_remote_layout = QHBoxLayout() # Layout для пути на устройстве
        pull_remote_layout.addWidget(QLabel("Путь на устр-ве:"))
        self.remote_path_pull_edit = QLineEdit()
        self.remote_path_pull_edit.setPlaceholderText("/sdcard/DCIM/Camera/image.jpg")
        self.remote_path_pull_edit.setToolTip("Какой файл/папку скачать с устройства.")
        self.remote_path_pull_edit.setEnabled(bool(self.adb_path))
        pull_remote_layout.addWidget(self.remote_path_pull_edit, 1) # Растягиваем
        adb_files_layout.addLayout(pull_remote_layout)

        pull_local_layout = QHBoxLayout() # Layout для выбора папки и кнопки
        self.select_folder_pull_button = QPushButton("Куда сохранить (Pull)")
        self.select_folder_pull_button.setToolTip("Выбрать локальную папку для сохранения файла/папки с устройства.")
        self.select_folder_pull_button.setEnabled(bool(self.adb_path))
        self.select_folder_pull_button.clicked.connect(self.select_local_folder_pull)
        pull_local_layout.addWidget(self.select_folder_pull_button)
        self.local_folder_pull_label = QLabel("Папка не выбрана")
        pull_local_layout.addWidget(self.local_folder_pull_label, 1) # Растягиваем метку
        self.pull_button = QPushButton("Скачать (Pull)")
        self.pull_button.setToolTip("Скачать указанный файл/папку с устройства.")
        self.pull_button.setEnabled(bool(self.adb_path))
        self.pull_button.clicked.connect(self.pull_file_from_device)
        pull_local_layout.addWidget(self.pull_button)
        adb_files_layout.addLayout(pull_local_layout)

        # Группа Управление приложениями (ADB)
        adb_apps_group = QGroupBox("Управление приложениями")
        adb_main_layout.addWidget(adb_apps_group)
        adb_apps_layout = QVBoxLayout(adb_apps_group)
        apk_install_layout = QHBoxLayout()
        self.select_apk_button = QPushButton("Выбрать APK")
        self.select_apk_button.setToolTip("Выбрать .apk файл для установки.")
        self.select_apk_button.setEnabled(bool(self.adb_path))
        self.select_apk_button.clicked.connect(self.select_apk_file)
        apk_install_layout.addWidget(self.select_apk_button)
        self.apk_path_label = QLabel("APK не выбран")
        apk_install_layout.addWidget(self.apk_path_label, 1) # Растягиваем метку
        self.install_apk_button = QPushButton("Установить APK")
        self.install_apk_button.setToolTip("Установить выбранный APK на устройство.")
        self.install_apk_button.setEnabled(bool(self.adb_path))
        self.install_apk_button.clicked.connect(self.install_selected_apk)
        apk_install_layout.addWidget(self.install_apk_button)
        adb_apps_layout.addLayout(apk_install_layout)

        adb_main_layout.addStretch(1) # Растягиватель в конце вкладки ADB

        # --- Вкладка Fastboot ---
        self.fastboot_tab = QWidget()
        self.tab_widget.addTab(self.fastboot_tab, "Fastboot")
        fastboot_layout = QVBoxLayout(self.fastboot_tab)

        # --- Группа Устройства Fastboot ---
        fb_device_group = QGroupBox("Устройства Fastboot")
        fastboot_layout.addWidget(fb_device_group)
        fb_device_layout_inner = QVBoxLayout(fb_device_group)
        fb_device_buttons_layout = QHBoxLayout()
        self.refresh_fastboot_button = QPushButton("Обновить Fastboot устр-ва")
        self.refresh_fastboot_button.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)))
        self.refresh_fastboot_button.setEnabled(bool(self.fastboot_path))
        self.refresh_fastboot_button.clicked.connect(self.refresh_fastboot_devices)
        fb_device_buttons_layout.addWidget(self.refresh_fastboot_button)
        fb_device_buttons_layout.addStretch(1)
        fb_device_layout_inner.addLayout(fb_device_buttons_layout)
        self.fastboot_device_list_widget = QListWidget()
        self.fastboot_device_list_widget.setToolTip("Список устройств Fastboot. Выберите устройство для команд.")
        fb_device_layout_inner.addWidget(self.fastboot_device_list_widget)

        # --- Группа Информация (Fastboot) ---
        fb_info_group = QGroupBox("Информация")
        fastboot_layout.addWidget(fb_info_group)
        fb_info_layout = QVBoxLayout(fb_info_group)
        fb_getvar_layout = QHBoxLayout()
        self.fb_getvar_all_button = QPushButton("Get All Variables")
        self.fb_getvar_all_button.setToolTip("fastboot getvar all")
        self.fb_getvar_all_button.setEnabled(bool(self.fastboot_path))
        self.fb_getvar_all_button.clicked.connect(self.fb_get_all_vars)
        fb_getvar_layout.addWidget(self.fb_getvar_all_button)
        fb_getvar_layout.addStretch(1)
        fb_getvar_specific_layout = QHBoxLayout()
        fb_getvar_specific_layout.addWidget(QLabel("Переменная:"))
        self.fb_getvar_specific_edit = QLineEdit()
        self.fb_getvar_specific_edit.setPlaceholderText("например, product или version-bootloader")
        self.fb_getvar_specific_edit.setEnabled(bool(self.fastboot_path))
        fb_getvar_specific_layout.addWidget(self.fb_getvar_specific_edit, 1) # Растягиваем
        self.fb_getvar_specific_button = QPushButton("Get Variable")
        self.fb_getvar_specific_button.setToolTip("fastboot getvar <переменная>")
        self.fb_getvar_specific_button.setEnabled(bool(self.fastboot_path))
        self.fb_getvar_specific_button.clicked.connect(self.fb_get_specific_var)
        fb_getvar_specific_layout.addWidget(self.fb_getvar_specific_button)
        fb_info_layout.addLayout(fb_getvar_layout)
        fb_info_layout.addLayout(fb_getvar_specific_layout)

        # --- Группа Прошивка / Стирание / Boot (СПОЙЛЕР + КНОПКИ) ---
        fb_flash_group = QGroupBox("Прошивка / Стирание / Boot")
        fb_flash_group.setCheckable(True)  # Делаем группу сворачиваемой
        fb_flash_group.setChecked(False) # Изначально свернута
        fastboot_layout.addWidget(fb_flash_group)

        # Основной layout внутри GroupBox
        fb_flash_main_layout = QVBoxLayout(fb_flash_group)

        # Виджет, который будет показываться/скрываться вместе с GroupBox
        # (GroupBox сам управляет видимостью своего layout при setChecked)

        warning_flash_label = QLabel("⚠️ ВНИМАНИЕ: НЕПРАВИЛЬНАЯ ПРОШИВКА/СТИРАНИЕ МОЖЕТ ОКИРПИЧИТЬ УСТРОЙСТВО!")
        warning_flash_label.setStyleSheet("color: red; font-weight: bold;")
        fb_flash_main_layout.addWidget(warning_flash_label)

        # -- Выбор раздела КНОПКАМИ --
        partition_select_layout = QHBoxLayout()
        partition_select_layout.addWidget(QLabel("Раздел:"))
        # Метка для отображения выбранного раздела
        self.selected_partition_label = QLabel("<i>Не выбран</i>")
        self.selected_partition_label.setStyleSheet("font-weight: bold;") # Выделим жирным
        self.selected_partition_label.setToolTip("Раздел, выбранный кнопкой ниже")
        partition_select_layout.addWidget(self.selected_partition_label)
        partition_select_layout.addStretch(1)
        fb_flash_main_layout.addLayout(partition_select_layout)

        # Layout для кнопок разделов (можно использовать QGridLayout для компактности)
        # Используем QHBoxLayout для простоты
        partition_buttons_layout_1 = QHBoxLayout()
        partition_buttons_layout_2 = QHBoxLayout()

        common_partitions = ["boot", "recovery", "system", "vendor", "vbmeta", "dtbo", "userdata"] # Основные разделы
        # Можно добавить больше: cache, persist, modem, dsp, abl, xbl, etc.
        # Разделим на две строки для компактности
        partitions_line1 = ["boot", "recovery", "vbmeta", "dtbo"]
        partitions_line2 = ["system", "vendor", "userdata"] # userdata для erase

        self.partition_buttons = {} # Словарь для хранения кнопок {name: button}
        for partition_name in partitions_line1:
            button = QPushButton(partition_name)
            button.setToolTip(f"Выбрать раздел '{partition_name}' для прошивки/стирания")
            button.setEnabled(bool(self.fastboot_path))
            # Используем lambda для передачи имени раздела в слот
            button.clicked.connect(lambda checked=False, name=partition_name: self.select_fb_partition(name))
            partition_buttons_layout_1.addWidget(button)
            self.partition_buttons[partition_name] = button
        partition_buttons_layout_1.addStretch(1) # Прижимаем кнопки влево

        for partition_name in partitions_line2:
            button = QPushButton(partition_name)
            button.setToolTip(f"Выбрать раздел '{partition_name}' для прошивки/стирания")
            button.setEnabled(bool(self.fastboot_path))
            button.clicked.connect(lambda checked=False, name=partition_name: self.select_fb_partition(name))
            partition_buttons_layout_2.addWidget(button)
            self.partition_buttons[partition_name] = button
        partition_buttons_layout_2.addStretch(1) # Прижимаем кнопки влево

        fb_flash_main_layout.addLayout(partition_buttons_layout_1)
        fb_flash_main_layout.addLayout(partition_buttons_layout_2)

        # -- Выбор файла образа для ПРОШИВКИ --
        flash_file_layout = QHBoxLayout()
        self.fb_select_image_button = QPushButton("Выбрать образ (.img) для Flash")
        self.fb_select_image_button.setToolTip("Выбрать файл образа для прошивки в ВЫБРАННЫЙ раздел")
        self.fb_select_image_button.setEnabled(bool(self.fastboot_path))
        self.fb_select_image_button.clicked.connect(self.fb_select_image)
        flash_file_layout.addWidget(self.fb_select_image_button)
        self.fb_image_path_label = QLabel("Образ не выбран")
        flash_file_layout.addWidget(self.fb_image_path_label, 1) # Растягиваем
        fb_flash_main_layout.addLayout(flash_file_layout)

        # -- Кнопки действий: Прошить и Стереть --
        action_buttons_layout = QHBoxLayout()
        self.fb_flash_button = QPushButton("Прошить (`flash`)")
        self.fb_flash_button.setToolTip("Прошить выбранный образ в ВЫБРАННЫЙ раздел")
        self.fb_flash_button.setEnabled(bool(self.fastboot_path))
        self.fb_flash_button.clicked.connect(self.fb_flash_partition)
        action_buttons_layout.addWidget(self.fb_flash_button)

        self.fb_erase_button = QPushButton("Стереть (`erase`)")
        self.fb_erase_button.setToolTip("Стереть ВЫБРАННЫЙ раздел (НЕОБРАТИМО!)")
        self.fb_erase_button.setEnabled(bool(self.fastboot_path))
        self.fb_erase_button.clicked.connect(self.fb_erase_partition)
        action_buttons_layout.addWidget(self.fb_erase_button)
        action_buttons_layout.addStretch(1)
        fb_flash_main_layout.addLayout(action_buttons_layout)

        # Добавим разделитель
        fb_flash_main_layout.addSpacing(15)

        # -- Выбор файла ядра для BOOT --
        boot_select_layout = QHBoxLayout()
        self.fb_select_boot_kernel_button = QPushButton("Выбрать ядро/рекавери (.img) для Boot")
        self.fb_select_boot_kernel_button.setToolTip("Выбрать образ для временной загрузки (без прошивки)")
        self.fb_select_boot_kernel_button.setEnabled(bool(self.fastboot_path))
        self.fb_select_boot_kernel_button.clicked.connect(self.fb_select_boot_kernel)
        boot_select_layout.addWidget(self.fb_select_boot_kernel_button)
        self.fb_boot_kernel_label = QLabel("Ядро/Рекавери не выбрано")
        boot_select_layout.addWidget(self.fb_boot_kernel_label, 1) # Растягиваем
        fb_flash_main_layout.addLayout(boot_select_layout)

        # -- Кнопка действия: Boot --
        boot_action_layout = QHBoxLayout()
        self.fb_boot_button = QPushButton("Загрузить (`boot`)")
        self.fb_boot_button.setToolTip("Временно загрузиться с выбранным образом (без прошивки)")
        self.fb_boot_button.setEnabled(bool(self.fastboot_path))
        self.fb_boot_button.clicked.connect(self.fb_boot_kernel)
        boot_action_layout.addWidget(self.fb_boot_button)
        boot_action_layout.addStretch(1)
        fb_flash_main_layout.addLayout(boot_action_layout)
        # --- КОНЕЦ ИЗМЕНЕНИЙ в Группе Прошивка / Стирание ---

        # --- Группа Загрузчик ---
        fb_loader_group = QGroupBox("Загрузчик")
        fastboot_layout.addWidget(fb_loader_group)
        fb_loader_layout = QVBoxLayout(fb_loader_group)
        warning_unlock_label = QLabel("⚠️ ВНИМАНИЕ: РАЗБЛОКИРОВКА СТИРАЕТ ВСЕ ДАННЫЕ И СНИМАЕТ ГАРАНТИЮ!")
        warning_unlock_label.setStyleSheet("color: red; font-weight: bold;")
        fb_loader_layout.addWidget(warning_unlock_label)
        loader_buttons_layout = QHBoxLayout()
        self.fb_unlock_button = QPushButton("Разблокировать (`flashing unlock`)")
        self.fb_unlock_button.setEnabled(bool(self.fastboot_path))
        self.fb_unlock_button.clicked.connect(self.fb_unlock_bootloader)
        loader_buttons_layout.addWidget(self.fb_unlock_button)
        self.fb_lock_button = QPushButton("Заблокировать (`flashing lock`)")
        self.fb_lock_button.setEnabled(bool(self.fastboot_path))
        self.fb_lock_button.clicked.connect(self.fb_lock_bootloader)
        loader_buttons_layout.addWidget(self.fb_lock_button)
        loader_buttons_layout.addStretch(1) # Прижимаем влево
        fb_loader_layout.addLayout(loader_buttons_layout)

        # --- Группа A/B Слоты ---
        fb_slot_group = QGroupBox("A/B Слоты")
        fastboot_layout.addWidget(fb_slot_group)
        fb_slot_layout = QHBoxLayout(fb_slot_group)
        self.fb_get_slot_button = QPushButton("Текущий слот")
        self.fb_get_slot_button.setEnabled(bool(self.fastboot_path))
        self.fb_get_slot_button.clicked.connect(self.fb_get_current_slot)
        fb_slot_layout.addWidget(self.fb_get_slot_button)
        self.fb_current_slot_label = QLabel("Слот: -")
        fb_slot_layout.addWidget(self.fb_current_slot_label)
        self.fb_set_active_a_button = QPushButton("Актив.: A")
        self.fb_set_active_a_button.setEnabled(bool(self.fastboot_path))
        self.fb_set_active_a_button.clicked.connect(lambda: self.fb_set_active_slot('a'))
        fb_slot_layout.addWidget(self.fb_set_active_a_button)
        self.fb_set_active_b_button = QPushButton("Актив.: B")
        self.fb_set_active_b_button.setEnabled(bool(self.fastboot_path))
        self.fb_set_active_b_button.clicked.connect(lambda: self.fb_set_active_slot('b'))
        fb_slot_layout.addWidget(self.fb_set_active_b_button)
        fb_slot_layout.addStretch(1) # Прижимаем влево

        # --- Группа Перезагрузка (Fastboot) ---
        fb_reboot_group = QGroupBox("Перезагрузка (из Fastboot)")
        fastboot_layout.addWidget(fb_reboot_group)
        fb_reboot_layout = QHBoxLayout(fb_reboot_group)
        self.fb_reboot_system_button = QPushButton("В Систему (`reboot`)")
        self.fb_reboot_system_button.setEnabled(bool(self.fastboot_path))
        self.fb_reboot_system_button.clicked.connect(self.fb_reboot_system)
        fb_reboot_layout.addWidget(self.fb_reboot_system_button)
        self.fb_reboot_bootloader_button = QPushButton("В Bootloader (`reboot-bootloader`)")
        self.fb_reboot_bootloader_button.setEnabled(bool(self.fastboot_path))
        self.fb_reboot_bootloader_button.clicked.connect(self.fb_reboot_bootloader)
        fb_reboot_layout.addWidget(self.fb_reboot_bootloader_button)
        fb_reboot_layout.addStretch(1) # Прижимаем влево

        fastboot_layout.addStretch(1) # Растягиватель в конце вкладки Fastboot
        self.tab_widget.setTabEnabled(1, bool(self.fastboot_path)) # Включаем/выключаем вкладку Fastboot

        # --- Консоль вывода ---
        main_layout.addWidget(QLabel("Консоль вывода:"))
        self.output_console = QPlainTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setObjectName("ConsoleOutput") # Для возможной стилизации
        # Устанавливаем темный фон и светлый текст для консоли
        self.output_console.setStyleSheet("""
            background-color: #2B2B2B;
            color: #DCDCDC;
            font-family: Consolas, Courier New, monospace;
        """)
        main_layout.addWidget(self.output_console, 1) # Растягиваем консоль по вертикали

        self.statusBar().showMessage("Приложение готово.")
        print("[DEBUG] MainWindow.setup_ui: Конец настройки UI")


    # --- Слоты и обработчики ---

    def clear_log(self):
        """Очищает консоль вывода."""
        self.output_console.clear()

    def log_message(self, message):
        """Добавляет сообщение в консоль и в лог DEBUG."""
        self.output_console.appendPlainText(message)
        print(f"LOG: {message}") # Дублируем в основной лог для отладки

    def start_worker(self, executable_path, command_args_list, result_handler, serial=None):
        """Запускает CommandWorker для выполнения команды."""
        if not executable_path:
            # Пытаемся угадать имя инструмента из команды
            tool_name = "???"
            if command_args_list:
                 # Проверяем первый аргумент, похож ли он на adb или fastboot
                 if 'adb' in command_args_list[0].lower(): tool_name = 'adb'
                 elif 'fastboot' in command_args_list[0].lower(): tool_name = 'fastboot'

            QMessageBox.warning(self, "Ошибка", f"Путь к {tool_name} не найден или не задан.")
            return False # Не запускаем

        if self.current_worker and self.current_worker.isRunning():
            self.log_message("Предыдущая команда еще выполняется...")
            QMessageBox.information(self, "Информация", "Дождитесь завершения предыдущей операции.")
            return False # Не запускаем новую

        # Формируем полную команду
        full_command = [executable_path]
        if serial:
            full_command.extend(['-s', serial]) # Добавляем серийник, если он есть
        full_command.extend(command_args_list) # Добавляем основные аргументы команды

        log_str = ' '.join(full_command) # Собираем строку для лога
        self.log_message(f"Выполнение: {log_str}")
        self.statusBar().showMessage(f"Выполнение: {log_str}")
        self.set_buttons_enabled(False) # Блокируем кнопки

        self.current_worker = CommandWorker(executable_path, full_command)
        # Подключаем сигналы
        self.current_worker.command_info.connect(self.handle_worker_started)
        self.current_worker.result_ready.connect(result_handler)
        self.current_worker.error_occurred.connect(self.handle_worker_error)
        self.current_worker.finished.connect(self.handle_worker_finished)
        self.current_worker.start() # Запускаем поток
        return True # Запуск успешен

    def set_buttons_enabled(self, enabled):
        """Включает или выключает кнопки в зависимости от доступности adb/fastboot и состояния worker'а."""
        is_running = bool(self.current_worker and self.current_worker.isRunning())
        actual_enabled_state = enabled and not is_running # Кнопки активны, если разрешено и ничего не выполняется
        adb_ok = bool(self.adb_path)
        fastboot_ok = bool(self.fastboot_path)

        # --- ADB Кнопки ---
        self.refresh_adb_button.setEnabled(actual_enabled_state and adb_ok)
        self.reboot_button.setEnabled(actual_enabled_state and adb_ok)
        self.reboot_recovery_button.setEnabled(actual_enabled_state and adb_ok)
        self.reboot_bootloader_button.setEnabled(actual_enabled_state and adb_ok)
        self.select_file_push_button.setEnabled(actual_enabled_state and adb_ok)
        self.remote_path_push_edit.setEnabled(actual_enabled_state and adb_ok)
        self.push_button.setEnabled(actual_enabled_state and adb_ok)
        self.remote_path_pull_edit.setEnabled(actual_enabled_state and adb_ok)
        self.select_folder_pull_button.setEnabled(actual_enabled_state and adb_ok)
        self.pull_button.setEnabled(actual_enabled_state and adb_ok)
        self.select_apk_button.setEnabled(actual_enabled_state and adb_ok)
        self.install_apk_button.setEnabled(actual_enabled_state and adb_ok)

        # --- Fastboot Кнопки ---
        self.refresh_fastboot_button.setEnabled(actual_enabled_state and fastboot_ok)
        # Info
        self.fb_getvar_all_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_getvar_specific_edit.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_getvar_specific_button.setEnabled(actual_enabled_state and fastboot_ok)
        # Flash/Erase/Boot group
        # Саму группу (спойлер) не блокируем, только ее содержимое
        for btn in self.partition_buttons.values(): # Кнопки разделов
             btn.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_select_image_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_flash_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_erase_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_select_boot_kernel_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_boot_button.setEnabled(actual_enabled_state and fastboot_ok)
        # Loader
        self.fb_unlock_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_lock_button.setEnabled(actual_enabled_state and fastboot_ok)
        # Slots
        self.fb_get_slot_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_set_active_a_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_set_active_b_button.setEnabled(actual_enabled_state and fastboot_ok)
        # Reboot
        self.fb_reboot_system_button.setEnabled(actual_enabled_state and fastboot_ok)
        self.fb_reboot_bootloader_button.setEnabled(actual_enabled_state and fastboot_ok)

        # Вкладка Fastboot целиком
        self.tab_widget.setTabEnabled(1, fastboot_ok)


    def handle_worker_started(self, command_args):
        """Запоминает, какая команда была запущена (без пути к exe и -s serial)."""
        # command_args это full_command из start_worker
        if command_args and len(command_args) > 0:
            # Убираем путь к exe
            args_only = command_args[1:]
            # Убираем '-s serial' если есть
            if len(args_only) >= 2 and args_only[0] == '-s':
                self.last_started_command = args_only[2:]
            else:
                self.last_started_command = args_only
        else:
             self.last_started_command = []
        print(f"[DEBUG] Worker started for command type: {self.last_started_command}")

    def get_selected_adb_device(self):
        """Возвращает серийный номер выбранного ADB устройства или None."""
        current_item = self.adb_device_list_widget.currentItem()
        if not current_item:
            if self.adb_device_list_widget.count() > 0:
                QMessageBox.warning(self, "Нет выбора", "Пожалуйста, выберите устройство из списка ADB.")
            else:
                 QMessageBox.warning(self, "Нет устройств", "Нет подключенных устройств ADB.")
            return None

        text = current_item.text()
        # Извлекаем серийник до первого пробела или скобки
        match = re.match(r"([a-zA-Z0-9\-\_]+)\s*.*", text) # Более общее регулярное выражение
        if match:
            serial = match.group(1)
            print(f"[DEBUG] Выбрано устройство ADB: {serial}")
            return serial
        else:
            self.log_message(f"Не удалось извлечь серийный номер из: {text}")
            QMessageBox.warning(self, "Ошибка", "Не удалось определить серийный номер устройства.")
            return None

    def get_selected_fastboot_device(self):
        """Возвращает серийный номер выбранного Fastboot устройства или None."""
        current_item = self.fastboot_device_list_widget.currentItem()
        if not current_item:
            if self.fastboot_device_list_widget.count() > 0:
                 QMessageBox.warning(self, "Нет выбора", "Пожалуйста, выберите устройство из списка Fastboot.")
            else:
                QMessageBox.warning(self, "Нет устройств", "Нет подключенных устройств Fastboot.")
            return None

        text = current_item.text()
         # Извлекаем серийник до первого пробела или скобки
        match = re.match(r"([a-zA-Z0-9\-\_]+)\s*.*", text) # Более общее регулярное выражение
        if match:
            serial = match.group(1)
            print(f"[DEBUG] Выбрано устройство Fastboot: {serial}")
            return serial
        else:
            self.log_message(f"Не удалось извлечь серийный номер из: {text}")
            QMessageBox.warning(self, "Ошибка", "Не удалось определить серийный номер устройства.")
            return None

    def refresh_adb_devices(self):
        """Обновляет список ADB устройств."""
        self.clear_log()
        self.adb_device_list_widget.clear()
        self.devices_found_list = [] # Сбрасываем список серийников
        # if self.battery_label: self.battery_label.setText("Батарея: --") # Батарею убрали
        self.log_message("Сканирование ADB устройств...")
        self.start_worker(self.adb_path, ['devices'], self.handle_adb_devices_result)

    def handle_adb_devices_result(self, stdout, stderr):
        """Обрабатывает результат команды 'adb devices'."""
        self.log_message("--- Результат 'adb devices' ---")
        self.devices_found_list = [] # Сбрасываем перед заполнением
        self.adb_device_list_widget.clear()
        devices_parsed_count = 0

        if stdout:
            self.log_message(f"STDOUT:\n{stdout.strip()}")
            lines = stdout.strip().splitlines()
            # Пропускаем первую строку "List of devices attached"
            if len(lines) > 1:
                 for line in lines[1:]:
                    line = line.strip()
                    if line:
                        parts = line.split(None, 1) # Разделяем по первому пробелу/табуляции
                        if len(parts) == 2:
                            serial, status = parts[0].strip(), parts[1].strip()
                            self.adb_device_list_widget.addItem(f"{serial} ({status})")
                            # Добавляем только активные устройства для последующих команд
                            if status not in ('offline', 'unauthorized'):
                                self.devices_found_list.append(serial)
                            devices_parsed_count += 1
                        else:
                             self.log_message(f"Не удалось распознать строку устройства: {line}")

        if stderr:
            # Некоторые версии adb могут писать ошибки в stderr, даже если устройства найдены
            self.log_message(f"STDERR:\n{stderr.strip()}")
            self.statusBar().showMessage("Ошибка или вывод в stderr при 'adb devices'.", 5000)

        if devices_parsed_count == 0 and not (stderr and ("error" in stderr.lower() or "daemon" in stderr.lower() or "server" in stderr.lower())):
            # Сообщение "не найдены", только если нет явных ошибок сервера в stderr
            self.adb_device_list_widget.addItem("ADB устройства не найдены")
            self.log_message("Подключенные ADB устройства не обнаружены.")
        elif devices_parsed_count > 0:
            self.log_message(f"Найдено активных ADB устройств: {len(self.devices_found_list)} (всего строк: {devices_parsed_count})")

        self.log_message("-----------------------------")
        # Батарею больше не запрашиваем

    def run_simple_adb_command_reboot(self):
        """Перезагружает выбранное ADB устройство."""
        serial = self.get_selected_adb_device()
        if serial:
            self.start_worker(self.adb_path, ['reboot'], self.handle_simple_command_result, serial=serial)

    def run_simple_adb_command_recovery(self):
        """Перезагружает выбранное ADB устройство в Recovery."""
        serial = self.get_selected_adb_device()
        if serial:
            self.start_worker(self.adb_path, ['reboot', 'recovery'], self.handle_simple_command_result, serial=serial)

    def run_simple_adb_command_bootloader(self):
        """Перезагружает выбранное ADB устройство в Bootloader."""
        serial = self.get_selected_adb_device()
        if serial:
             self.start_worker(self.adb_path, ['reboot', 'bootloader'], self.handle_simple_command_result, serial=serial)

    def select_local_file_push(self):
        """Открывает диалог выбора файла для отправки (Push)."""
        fileName, _ = QFileDialog.getOpenFileName(self, "Выберите файл для отправки", "", "Все файлы (*.*)")
        if fileName:
            self.local_file_to_push = fileName
            self.local_file_push_label.setText(os.path.basename(fileName))
            self.local_file_push_label.setToolTip(fileName)
            print(f"[DEBUG] Push файл выбран: {self.local_file_to_push}")
        else:
            # Сбрасываем, если пользователь отменил выбор
            self.local_file_to_push = ""
            self.local_file_push_label.setText("Файл не выбран")
            self.local_file_push_label.setToolTip("")

    def push_file_to_device(self):
        """Отправляет выбранный файл на устройство."""
        serial = self.get_selected_adb_device()
        if not serial:
            return

        local_path = self.local_file_to_push
        if not local_path or not os.path.isfile(local_path):
            QMessageBox.warning(self, "Ошибка", f"Локальный файл не выбран или не существует:\n{local_path}")
            return

        remote_path = self.remote_path_push_edit.text().strip()
        if not remote_path:
            QMessageBox.warning(self, "Ошибка", "Не указан путь назначения на устройстве (например, /sdcard/Download/).")
            return

        command_args = ['push', local_path, remote_path]
        self.start_worker(self.adb_path, command_args, self.handle_simple_command_result, serial=serial)

    def select_local_folder_pull(self):
        """Открывает диалог выбора папки для сохранения (Pull)."""
        folderName = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", "")
        if folderName:
            self.local_folder_to_pull = folderName
            # Показываем полный путь для ясности
            self.local_folder_pull_label.setText(folderName)
            self.local_folder_pull_label.setToolTip(folderName)
            print(f"[DEBUG] Pull папка выбрана: {self.local_folder_to_pull}")
        else:
            self.local_folder_to_pull = ""
            self.local_folder_pull_label.setText("Папка не выбрана")
            self.local_folder_pull_label.setToolTip("")

    def pull_file_from_device(self):
        """Скачивает файл или папку с устройства."""
        serial = self.get_selected_adb_device()
        if not serial:
            return

        remote_path = self.remote_path_pull_edit.text().strip()
        if not remote_path:
            QMessageBox.warning(self, "Ошибка", "Не указан путь к файлу/папке на устройстве.")
            return

        local_path = self.local_folder_to_pull
        if not local_path or not os.path.isdir(local_path):
            QMessageBox.warning(self, "Ошибка", f"Локальная папка для сохранения не выбрана или не существует:\n{local_path}")
            return

        command_args = ['pull', remote_path, local_path]
        self.start_worker(self.adb_path, command_args, self.handle_simple_command_result, serial=serial)

    def select_apk_file(self):
        """Открывает диалог выбора APK файла."""
        fileName, _ = QFileDialog.getOpenFileName(self, "Выберите APK файл", "", "APK Files (*.apk);;All Files (*)")
        if fileName:
            self.apk_to_install = fileName
            self.apk_path_label.setText(os.path.basename(fileName))
            self.apk_path_label.setToolTip(fileName)
            print(f"[DEBUG] APK выбран: {self.apk_to_install}")
        else:
            self.apk_to_install = ""
            self.apk_path_label.setText("APK не выбран")
            self.apk_path_label.setToolTip("")

    def install_selected_apk(self):
        """Устанавливает выбранный APK."""
        serial = self.get_selected_adb_device()
        if not serial:
            return

        apk_path = self.apk_to_install
        if not apk_path or not os.path.isfile(apk_path):
            QMessageBox.warning(self, "Ошибка", f"APK файл не выбран или не существует:\n{apk_path}")
            return

        self.log_message(f"Установка {os.path.basename(apk_path)}...")
        self.statusBar().showMessage(f"Установка {os.path.basename(apk_path)}...")
        # Добавляем ключ -r для возможности переустановки
        command_args = ['install', '-r', apk_path]
        self.start_worker(self.adb_path, command_args, self.handle_install_apk_result, serial=serial)

    def handle_install_apk_result(self, stdout, stderr):
        """Обрабатывает результат установки APK."""
        self.log_message("--- Результат установки APK ---")
        success = False
        output = ""
        if stdout:
            stdout_clean = stdout.strip()
            self.log_message(f"STDOUT:\n{stdout_clean}")
            output += stdout_clean + "\n"
            if 'success' in stdout_clean.lower():
                 success = True
        if stderr:
            stderr_clean = stderr.strip()
            self.log_message(f"STDERR:\n{stderr_clean}")
            output += stderr_clean
            # Иногда success пишется в stderr
            if 'success' in stderr_clean.lower():
                success = True

        # Показываем сообщение пользователю
        if success:
            QMessageBox.information(self, "Успех", f"APK '{os.path.basename(self.apk_to_install)}' успешно установлен.")
            self.statusBar().showMessage("APK установлен.", 5000)
        else:
            QMessageBox.warning(self, "Ошибка установки", f"Не удалось установить APK.\nПодробности в консоли.\n\nВывод:\n{output[:200]}") # Показываем часть вывода
            self.statusBar().showMessage("Ошибка установки APK.", 5000)

        self.log_message("------------------------------")

    # --- Обработчики Fastboot ---
    def refresh_fastboot_devices(self):
        """Обновляет список Fastboot устройств."""
        self.clear_log()
        self.fastboot_device_list_widget.clear()
        self.log_message("Сканирование Fastboot устройств...")
        self.start_worker(self.fastboot_path, ['devices'], self.handle_fastboot_devices_result)

    def handle_fastboot_devices_result(self, stdout, stderr):
        """Обрабатывает результат 'fastboot devices'."""
        self.log_message("--- Результат 'fastboot devices' ---")
        devices_found = 0
        output_lines = []
        # fastboot devices часто пишет в stderr
        if stderr:
            output_lines.extend(stderr.strip().splitlines())
        if stdout:
            output_lines.extend(stdout.strip().splitlines())

        self.log_message(f"Raw Output:\n" + "\n".join(output_lines))
        self.fastboot_device_list_widget.clear()

        unique_serials = set() # Чтобы избежать дубликатов, если вывод в обеих
        for line in output_lines:
            line = line.strip()
            if line:
                # Разделяем по пробелу или табуляции
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[1].lower().strip() == 'fastboot':
                    serial = parts[0].strip()
                    if serial not in unique_serials:
                        self.fastboot_device_list_widget.addItem(f"{serial} (fastboot)")
                        unique_serials.add(serial)
                        devices_found += 1

        if devices_found == 0:
            self.fastboot_device_list_widget.addItem("Fastboot устройства не найдены")
            self.log_message("Подключенные Fastboot устройства не обнаружены.")
        elif devices_found > 0:
            self.log_message(f"Найдено Fastboot устройств: {devices_found}")

        self.log_message("-----------------------------")

    # --- Новые обработчики Fastboot ---
    def fb_get_all_vars(self):
        """Запрашивает все переменные Fastboot."""
        serial = self.get_selected_fastboot_device()
        if serial:
            self.log_message("Запрос всех переменных Fastboot...")
            self.start_worker(self.fastboot_path, ['getvar', 'all'], self.handle_fastboot_getvar_result, serial=serial)

    def fb_get_specific_var(self):
        """Запрашивает конкретную переменную Fastboot."""
        serial = self.get_selected_fastboot_device()
        if not serial:
             return

        var_name = self.fb_getvar_specific_edit.text().strip()
        if not var_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя переменной для запроса.")
            return

        self.log_message(f"Запрос переменной: {var_name}...")
        self.start_worker(self.fastboot_path, ['getvar', var_name], self.handle_fastboot_getvar_result, serial=serial)

    def handle_fastboot_getvar_result(self, stdout, stderr):
        """Обрабатывает результат 'fastboot getvar'."""
        self.log_message(f"--- Результат 'fastboot getvar' ---")
        output = ""
        # getvar часто пишет основной вывод в stderr
        if stderr:
            stderr_clean = stderr.strip()
            self.log_message(f"STDERR:\n{stderr_clean}")
            output += stderr_clean + "\n"
        if stdout:
            stdout_clean = stdout.strip()
            self.log_message(f"STDOUT:\n{stdout_clean}")
            output += stdout_clean

        if not output.strip():
            self.log_message("Нет вывода от команды getvar.")

        self.log_message("------------------------------------")

    def fb_select_image(self):
        """Открывает диалог выбора файла образа (.img) для прошивки."""
        fileName, _ = QFileDialog.getOpenFileName(self, "Выберите образ для прошивки", "", "Образы (*.img);;Все файлы (*.*)")
        if fileName:
            self.fb_image_to_flash = fileName
            self.fb_image_path_label.setText(os.path.basename(fileName))
            self.fb_image_path_label.setToolTip(fileName)
            print(f"[DEBUG] Образ для flash выбран: {self.fb_image_to_flash}")
        else:
            self.fb_image_to_flash = ""
            self.fb_image_path_label.setText("Образ не выбран")
            self.fb_image_path_label.setToolTip("")

    # <<< НОВЫЙ СЛОТ для обработки нажатия кнопок разделов >>>
    def select_fb_partition(self, partition_name):
        """Вызывается при нажатии на кнопку раздела."""
        self.selected_fb_partition = partition_name
        self.selected_partition_label.setText(f"<b>{partition_name}</b>") # Обновляем метку
        print(f"[DEBUG] Выбран раздел Fastboot: {partition_name}")

        # Сбрасываем стиль для всех кнопок и выделяем нажатую
        default_style = "" # Или стиль по умолчанию вашего UI
        selected_style = "background-color: #4a5a6a; color: white;" # Пример стиля для выделения

        for name, button in self.partition_buttons.items():
            if name == partition_name:
                button.setStyleSheet(selected_style)
                button.setDown(True) # Делаем вид, что кнопка нажата
            else:
                button.setStyleSheet(default_style)
                button.setDown(False)

    # <<< ИЗМЕНЕННЫЙ МЕТОД >>>
    def fb_flash_partition(self):
        """Прошивает выбранный образ в ВЫБРАННЫЙ КНОПКОЙ раздел."""
        serial = self.get_selected_fastboot_device()
        if not serial:
            return

        # --- ИЗМЕНЕНО: Берем раздел из self.selected_fb_partition ---
        partition = self.selected_fb_partition
        if not partition:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите раздел для прошивки (нажмите кнопку раздела).")
            return
        # ----------------------------------------------------------

        image_path = self.fb_image_to_flash
        if not image_path or not os.path.isfile(image_path):
            QMessageBox.warning(self, "Ошибка", f"Файл образа для прошивки не выбран или не существует:\n{image_path}")
            return

        # Двойное подтверждение опасной операции
        reply1 = QMessageBox.warning(self, "!!! ПРЕДУПРЕЖДЕНИЕ !!!",
                                     f"Прошивка раздела '{partition}' - ОПАСНАЯ ОПЕРАЦИЯ!\n"
                                     f"Файл: {os.path.basename(image_path)}\n\n"
                                     "Неправильный файл или раздел могут ОКИРПИЧИТЬ устройство.\n"
                                     "Автор программы НЕ НЕСЕТ ОТВЕТСТВЕННОСТИ за любые повреждения.\n\n"
                                     "Вы уверены, что хотите продолжить?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel) # По умолчанию Cancel
        if reply1 != QMessageBox.StandardButton.Yes:
            self.log_message("Прошивка отменена (1).")
            return

        reply2 = QMessageBox.question(self, "Окончательное подтверждение",
                                      f"Точно прошить раздел '{partition}'\n"
                                      f"файлом '{os.path.basename(image_path)}'\n"
                                      f"на устройстве {serial}?\n\n"
                                      "ЭТО МОЖЕТ БЫТЬ НЕОБРАТИМЫМ!",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No) # По умолчанию No
        if reply2 == QMessageBox.StandardButton.Yes:
            self.log_message(f"Запуск прошивки раздела '{partition}'...")
            command_args = ['flash', partition, image_path]
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
            self.log_message("Прошивка отменена (2).")

    # <<< ИЗМЕНЕННЫЙ МЕТОД >>>
    def fb_erase_partition(self):
        """Стирает ВЫБРАННЫЙ КНОПКОЙ раздел."""
        serial = self.get_selected_fastboot_device()
        if not serial:
            return

        # --- ИЗМЕНЕНО: Берем раздел из self.selected_fb_partition ---
        partition = self.selected_fb_partition
        if not partition:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите раздел для стирания (нажмите кнопку раздела).")
            return
        # ----------------------------------------------------------

        # Дополнительное предупреждение для userdata
        warning_text = ""
        if partition.lower() == 'userdata':
            warning_text = "\n\nСТИРАНИЕ 'userdata' УДАЛИТ ВСЕ ВАШИ ЛИЧНЫЕ ДАННЫЕ!"

        reply = QMessageBox.question(self, "Подтверждение стирания",
                                     f"Точно СТЕРЕТЬ раздел '{partition}'\n"
                                     f"на устройстве {serial}?\n"
                                     f"{warning_text}\n"
                                     "ДАННЫЕ НА ЭТОМ РАЗДЕЛЕ БУДУТ ПОТЕРЯНЫ!\n"
                                     "ДЕЙСТВИЕ НЕОБРАТИМО!",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # По умолчанию No
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Запуск стирания раздела '{partition}'...")
            command_args = ['erase', partition]
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
             self.log_message("Стирание отменено.")

    def fb_select_boot_kernel(self):
        """Открывает диалог выбора ядра для временной загрузки."""
        fileName, _ = QFileDialog.getOpenFileName(self, "Выберите образ ядра/рекавери для Boot", "", "Образы (*.img *.IMG);;Все файлы (*.*)")
        if fileName:
            self.fb_kernel_to_boot = fileName
            self.fb_boot_kernel_label.setText(os.path.basename(fileName))
            self.fb_boot_kernel_label.setToolTip(fileName)
            print(f"[DEBUG] Ядро для boot выбрано: {self.fb_kernel_to_boot}")
        else:
            self.fb_kernel_to_boot = ""
            self.fb_boot_kernel_label.setText("Ядро/Рекавери не выбрано")
            self.fb_boot_kernel_label.setToolTip("")

    def fb_boot_kernel(self):
        """Временно загружается с выбранным ядром/рекавери."""
        serial = self.get_selected_fastboot_device()
        if not serial:
            return

        kernel_path = self.fb_kernel_to_boot
        if not kernel_path or not os.path.isfile(kernel_path):
            QMessageBox.warning(self, "Ошибка", f"Файл ядра/рекавери для boot не выбран или не существует:\n{kernel_path}")
            return

        reply = QMessageBox.question(self, "Подтверждение временной загрузки",
                                     f"Загрузиться с образом\n'{os.path.basename(kernel_path)}'\n"
                                     f"(БЕЗ ПРОШИВКИ) на устройстве {serial}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # По умолчанию No
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Запуск временной загрузки (boot) с {os.path.basename(kernel_path)}...")
            command_args = ['boot', kernel_path]
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
            self.log_message("Временная загрузка отменена.")

    def fb_unlock_bootloader(self):
        """Разблокирует загрузчик."""
        serial = self.get_selected_fastboot_device()
        if not serial:
             return

        # Двойное подтверждение ОЧЕНЬ опасной операции
        reply1 = QMessageBox.critical(self, "!!! ОЧЕНЬ ОПАСНО !!!",
                                      "Разблокировка загрузчика ПОЛНОСТЬЮ СТИРАЕТ ВСЕ ДАННЫЕ НА УСТРОЙСТВЕ!\n"
                                      "(Фото, видео, приложения, настройки - ВСЁ БУДЕТ УДАЛЕНО!)\n"
                                      "Это также может аннулировать гарантию производителя.\n\n"
                                      "ВЫ ТОЧНО УВЕРЕНЫ, ЧТО ХОТИТЕ ЭТО СДЕЛАТЬ?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Cancel) # По умолчанию Cancel
        if reply1 != QMessageBox.StandardButton.Yes:
            self.log_message("Разблокировка загрузчика отменена (1).")
            return

        reply2 = QMessageBox.question(self, "Финальное подтверждение",
                                      f"Точно разблокировать загрузчик на {serial} и СТЕРЕТЬ ВСЕ ДАННЫЕ?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No) # По умолчанию No
        if reply2 == QMessageBox.StandardButton.Yes:
            self.log_message(f"Запуск разблокировки загрузчика для {serial}...")
            # Используем стандартную команду, но OEM-специфичные могут отличаться!
            command_args = ['flashing', 'unlock']
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
             self.log_message("Разблокировка загрузчика отменена (2).")

    def fb_lock_bootloader(self):
        """Блокирует загрузчик."""
        serial = self.get_selected_fastboot_device()
        if not serial:
            return

        reply = QMessageBox.question(self, "Подтверждение блокировки",
                                     f"Заблокировать загрузчик на устройстве {serial}?\n\n"
                                     "Убедитесь, что на устройстве установлена ПОЛНОСТЬЮ ОФИЦИАЛЬНАЯ (стоковая) прошивка, иначе можете получить КИРПИЧ!",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # По умолчанию No
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Запуск блокировки загрузчика для {serial}...")
            command_args = ['flashing', 'lock']
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
            self.log_message("Блокировка загрузчика отменена.")

    def fb_get_current_slot(self):
        """Запрашивает текущий активный слот (для A/B устройств)."""
        serial = self.get_selected_fastboot_device()
        if serial:
            self.log_message(f"Запрос текущего слота для {serial}...")
            self.start_worker(self.fastboot_path, ['getvar', 'current-slot'], self.handle_get_slot_result, serial=serial)

    def handle_get_slot_result(self, stdout, stderr):
        """Обрабатывает результат запроса слота."""
        self.log_message("--- Результат 'getvar current-slot' ---")
        slot = "-"
        output = ""
        # Вывод часто в stderr
        if stderr:
            output += stderr.strip() + "\n"
        if stdout:
            output += stdout.strip()

        self.log_message(f"Raw Output:\n{output.strip()}")

        # Ищем строку вида "current-slot: a" или "current-slot: b"
        match = re.search(r'current-slot:\s*([ab])', output, re.IGNORECASE)
        if match:
            slot = match.group(1).lower() # Приводим к нижнему регистру
            self.log_message(f"Текущий активный слот: {slot}")
        else:
            self.log_message("Не удалось определить текущий слот (возможно, не A/B устройство или нет вывода).")
            slot = "N/A" # Not Applicable / Неприменимо

        self.fb_current_slot_label.setText(f"Слот: {slot}")
        self.log_message("----------------------------------------")

    def fb_set_active_slot(self, slot_id):
        """Устанавливает активный слот (a или b)."""
        if slot_id not in ('a', 'b'):
            print(f"[ERROR] Неверный slot_id для fb_set_active_slot: {slot_id}")
            return

        serial = self.get_selected_fastboot_device()
        if not serial:
            return

        reply = QMessageBox.question(self, f"Смена активного слота на '{slot_id}'",
                                     f"Сделать активным слот '{slot_id}' на устройстве {serial}?\n"
                                     "(Это изменит раздел, с которого будет загружаться система)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # По умолчанию No
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message(f"Установка активного слота '{slot_id}' для {serial}...")
            # Команда для смены слота
            command_args = [f'--set-active={slot_id}']
            self.start_worker(self.fastboot_path, command_args, self.handle_simple_command_result, serial=serial)
        else:
            self.log_message(f"Смена активного слота на '{slot_id}' отменена.")

    def fb_reboot_system(self):
        """Перезагружает устройство из Fastboot в систему."""
        serial = self.get_selected_fastboot_device()
        if serial:
            self.log_message(f"Перезагрузка из Fastboot в систему для {serial}...")
            self.start_worker(self.fastboot_path, ['reboot'], self.handle_simple_command_result, serial=serial)

    def fb_reboot_bootloader(self):
        """Перезагружает устройство из Fastboot снова в Bootloader/Fastboot."""
        serial = self.get_selected_fastboot_device()
        if serial:
            self.log_message(f"Перезагрузка из Fastboot в Bootloader для {serial}...")
            self.start_worker(self.fastboot_path, ['reboot-bootloader'], self.handle_simple_command_result, serial=serial)

    # --- Общие обработчики потока ---
    def handle_simple_command_result(self, stdout, stderr):
        """Обрабатывает результат простой команды (stdout/stderr)."""
        self.log_message("--- Результат команды ---")
        if stdout:
            self.log_message(f"STDOUT:\n{stdout.strip()}")
        if stderr:
            self.log_message(f"STDERR:\n{stderr.strip()}")
        self.log_message("-----------------------")
        # Сообщение об успехе/ошибке будет показано в handle_worker_finished/error

    def handle_worker_error(self, error_message):
        """Обрабатывает сигнал ошибки от потока."""
        self.log_message(f"КРИТИЧЕСКАЯ ОШИБКА ПОТОКА: {error_message}")
        self.statusBar().showMessage(f"Ошибка выполнения: {error_message}", 5000)
        QMessageBox.critical(self, "Ошибка выполнения команды", error_message)
        # Важно разблокировать интерфейс и сбросить worker
        self.set_buttons_enabled(True)
        self.current_worker = None
        self.last_started_command = None

    def handle_worker_finished(self):
        """Обрабатывает сигнал завершения потока."""
        finished_command_args = self.last_started_command
        print(f"[DEBUG] MainWindow.handle_worker_finished: Поток для '{finished_command_args}' завершился.")

        # Просто разблокируем кнопки и сбрасываем состояние
        self.log_message("Операция завершена.")
        self.statusBar().showMessage("Готово.", 3000)
        self.set_buttons_enabled(True)
        self.current_worker = None
        self.last_started_command = None
        # Можно добавить автоматическое обновление списка устройств после некоторых команд


# --- Блок запуска ---
if __name__ == "__main__":
    print("[DEBUG] 4. Вход в блок if __name__ == '__main__'")
    try:
        app = QApplication(sys.argv)
        print("[DEBUG] 5. QApplication создан")

        # Отключили qt-material
        print("[DEBUG] Стиль qt-material отключен.")

        mainWin = MainWindow()
        print("[DEBUG] 6. MainWindow создан")
        mainWin.show()
        print("[DEBUG] 7. mainWin.show() вызван")
        print("[DEBUG] 8. Запуск app.exec()...");
        exit_code = app.exec()
        print(f"[DEBUG] 9. app.exec() завершился с кодом: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        # Ловим любые другие исключения при запуске
        print(f"[DEBUG] КРИТИЧЕСКАЯ ОШИБКА В БЛОКЕ MAIN: {e}")
        import traceback
        traceback.print_exc() # Печатаем полный traceback
        # Показываем сообщение об ошибке, если возможно
        try:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Критическая ошибка запуска")
            error_box.setText(f"Произошла критическая ошибка при запуске приложения:\n\n{e}\n\nПодробности в консоли.")
            error_box.setDetailedText(traceback.format_exc())
            error_box.exec()
        except Exception as e2:
             print(f"[DEBUG] Не удалось даже показать QMessageBox: {e2}") # На случай если и PyQt не работает
        sys.exit(1) # Выход с кодом ошибки