# pyright: reportGeneralTypeIssues=false, reportOptionalMemberAccess=false, reportArgumentType=false
#!/usr/bin/env python3
"""SyNasPy - NAS Management Tool
GUI-Anwendung zur Verwaltung eines Synology NAS-Servers
Funktionen: Wake-on-LAN, Herunterfahren, Volume-Management

Einstellungsdialog: Zugriff über Zahnrad-Button oder Cmd+E
· NAS-Benutzername, DNS, IP, MAC
· SSH-Key Pfad (SSH-Key Hilfe mit Erklärung, was zu tun ist)
· Volume-Liste (mit Haupt-Volume "NAS Dokumente")
· Auto-Shutdown/Start Verzögerung
· WOL und SMB Wartezeiten
· Mount-Wiederholungen
· Zeiteinstellungen: Alle Timeouts und Verzögerungen
· Pfad zur Statusdatei

Speichert die Konfiguration in zwei Formaten:
1. QSettings: Für plattformübergreifende Kompatibilität
2. JSON-Datei (~/.SyNasPy/config.json): Für einfache manuelle Bearbeitung. (Die JSON-Datei hat Vorrang vor QSettings, falls beide vorhanden sind.)

Kompatibilität
· Funktioniert auf Intel und Apple Silicon Macs
"""

import getpass
import json
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import (
    Q_ARG,
    QMetaObject,
    QSettings,
    Qt,
    QTimer,
    pyqtSlot,
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QDesktopWidget,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller Bundle - verwende _MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    else:
        # Entwicklungsmodus - verwende aktuelles Verzeichnis
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


# =======================================
# LOGGING KLASSE (TXT-Dateien)
# =======================================


class AppLogger:
    """Logging-Klasse mit TXT-Dateien und Rotation (max 5 Dateien)"""

    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.expanduser("~/Library/Application Support/SyNasPy/Logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_files = 5
        self.current_log_file = None
        self.log_buffer = []
        self.buffer_size = 10  # Nach 10 Einträgen wird geschrieben

        # Alte Logs aufräumen
        self.cleanup_old_logs()

        # Neues Log erstellen
        self.create_new_log()

    def cleanup_old_logs(self):
        """Löscht die ältesten Log-Dateien, wenn mehr als max_files vorhanden"""
        try:
            log_files = sorted(
                self.log_dir.glob("SyNasPy_*.txt"), key=lambda x: x.stat().st_mtime
            )

            # Älteste löschen wenn mehr als max_files
            while len(log_files) >= self.max_files:
                oldest = log_files.pop(0)
                oldest.unlink()
                print(f"  Alte Log-Datei gelöscht: {oldest.name}")

        except Exception as e:
            print(f"Fehler beim Aufräumen der Logs: {e}")

    def create_new_log(self):
        """Erstellt eine neue Log-Datei mit Zeitstempel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = self.log_dir / f"SyNasPy_{timestamp}.txt"

        # Header schreiben
        with open(self.current_log_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"SyNasPy Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"System: {platform.system()} {platform.release()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Architektur: {platform.machine()}\n")
            f.write(f"Prozess-ID: {os.getpid()}\n")
            f.write("-" * 80 + "\n\n")

        # Log-Start schreiben
        self.log("=== SYNASPY GESTARTET ===", "START")

    def _write_buffer(self):
        """Schreibt den Buffer in die Log-Datei"""
        if not self.log_buffer:
            return

        # Prüfen ob die Log-Datei definiert ist
        if self.current_log_file is None:
            print("Fehler: current_log_file ist nicht definiert")
            return

        try:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                for entry in self.log_buffer:
                    f.write(entry)
            self.log_buffer = []
        except Exception as e:
            print(f"Fehler beim Schreiben ins Log: {e}")

    def log(self, message, level="INFO"):
        """Schreibt eine Nachricht ins Log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # In Buffer speichern
        self.log_buffer.append(log_entry)

        # Wenn Buffer voll, schreiben
        if len(self.log_buffer) >= self.buffer_size:
            self._write_buffer()

    def log_action(self, action, details=""):
        """Loggt eine Aktion mit Details"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [ACTION] {action}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"

        self.log_buffer.append(log_entry)
        if len(self.log_buffer) >= self.buffer_size:
            self._write_buffer()

    def log_error(self, error, details="", exception=None):
        """Loggt einen Fehler mit Stacktrace"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [ERROR] {error}"
        if details:
            log_entry += f" - {details}"
        log_entry += "\n"

        # Wenn Exception übergeben, Stacktrace hinzufügen
        if exception:
            log_entry += f"[{timestamp}] [TRACE] {traceback.format_exc()}\n"

        self.log_buffer.append(log_entry)
        if len(self.log_buffer) >= self.buffer_size:
            self._write_buffer()

    def log_crash(self, exception):
        """Loggt einen Absturz mit vollständigem Stacktrace"""
        # Prüfen ob die Log-Datei definiert ist
        if self.current_log_file is None:
            print(
                "Fehler: current_log_file ist nicht definiert, Crash-Log kann nicht geschrieben werden"
            )
            # Fallback: Zumindest auf der Konsole ausgeben
            print(f"CRASH: {exception}")
            traceback.print_exc()
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
    {'='*80}
    [{timestamp}] [CRASH] ANWENDUNG ABGESTÜRZT!
    {'='*80}
    Fehler: {str(exception)}
    Typ: {type(exception).__name__}

    Stacktrace:
    {traceback.format_exc()}
    {'='*80}
    """
        try:
            # Direkt schreiben, nicht über Buffer
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Fehler beim Schreiben des Crash-Logs: {e}")
            # Im Fehlerfall trotzdem Stacktrace ausgeben
            traceback.print_exc()

    def log_config(self, config_dict):
        """Loggt die aktuelle Konfiguration"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"\n[{timestamp}] [CONFIG] Aktuelle Einstellungen:\n"
        for key, value in config_dict.items():
            # Pfade und sensible Daten auslassen oder kürzen
            if key in ["logo_file", "app_icon_file", "ssh_key_path"]:
                continue
            if isinstance(value, list):
                log_entry += f"  {key}: [{', '.join(value[:3])}"
                if len(value) > 3:
                    log_entry += f", ... ({len(value)-3} mehr)"
                log_entry += "]\n"
            else:
                log_entry += f"  {key}: {value}\n"
        log_entry += "-" * 80 + "\n\n"

        self.log_buffer.append(log_entry)
        if len(self.log_buffer) >= self.buffer_size:
            self._write_buffer()

    def log_system_info(self):
        """Loggt Systeminformationen"""
        info = f"""
System-Informationen:
  Betriebssystem: {platform.system()} {platform.release()} ({platform.version()})
  Architektur: {platform.machine()}
  Prozessor: {platform.processor()}
  Python: {sys.version}
  Python Pfad: {sys.executable}
  Arbeitsverzeichnis: {os.getcwd()}
  Umgebungsvariablen:
    PATH: {os.environ.get('PATH', 'N/A')[:200]}...
    HOME: {os.environ.get('HOME', 'N/A')}
    USER: {os.environ.get('USER', 'N/A')}
"""
        self.log(info, "SYSTEM")

    def flush(self):
        """Schreibt alle gepufferten Log-Einträge"""
        self._write_buffer()

    def __del__(self):
        """Destruktor - schreibt alle verbleibenden Buffer-Einträge"""
        try:
            self.flush()
            self.log("=== SYNASPY BEENDET ===", "STOP")
            self.flush()
        except:
            pass


# =======================================
# GLOBALER EXCEPTION-HANDLER
# =======================================


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Globaler Exception-Handler für nicht abgefangene Exceptions"""
    try:
        # Versuche Logger zu finden
        logger = None
        for obj in sys._current_frames().values():
            if "self" in obj.f_locals:
                if hasattr(obj.f_locals["self"], "logger"):
                    logger = obj.f_locals["self"].logger
                    break

        if logger:
            logger.log_crash(exc_value)
            logger.flush()
        else:
            # Fallback: In Datei schreiben
            crash_log = (
                Path.home() / "Library/Application Support/SyNasPy/Logs/crash.txt"
            )
            crash_log.parent.mkdir(parents=True, exist_ok=True)
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"CRASH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Fehler: {exc_value}\n")
                f.write(f"Typ: {exc_type.__name__}\n")
                f.write(f"Stacktrace:\n{traceback.format_exc()}\n")
                f.write(f"{'='*80}\n")
    except:
        pass

    # Standard-Exception-Handler aufrufen
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


# Exception-Handler setzen
sys.excepthook = global_exception_handler

# =======================================
# KONFIGURATIONSKLASSE
# =======================================


class Config:
    """Zentrale Konfigurationsverwaltung mit QSettings und JSON-Datei."""

    # Standardwerte
    DEFAULTS = {
        "nas_user": "nasuser",
        "nas_dns": "NAS-Synology",
        "nas_ip": "192.168.1.100",
        "nas_mac": "00:11:22:33:44:55",
        "ssh_key_path": "~/.ssh/id_rsa",
        "volume_list": [
            "NAS Dokumente",
            "NAS Bilder",
            "NAS Austausch",
            "NAS Hörbücher",
            "NAS Medien",
            "NAS Tools",
            "NAS Sonstiges",
            "surveillance",
            "home",
            "homes",
        ],
        "auto_shutdown_delay": 120,  # Sekunden
        "auto_start_delay": 120,  # Sekunden
        "wol_wait_time": 180,  # Sekunden
        "smb_wait_time": 30,  # Sekunden
        "mount_retries": 3,
        "status_file_path": "~/Downloads/boQuitNASapp.txt",
        "logo_file": "BinhDiez.png",
        "app_icon_file": "SyNasPy.png",
    }

    def __init__(self):
        """Initialisiert die Konfiguration."""
        self.app_name = "SyNasPy"
        self.org_name = "SyNasPy"

        # QSettings für plattformunabhängige Einstellungen
        self.settings = QSettings(self.org_name, self.app_name)

        # Pfad für JSON-Konfigurationsdatei
        self.config_dir = Path.home() / "Library/Application Support/SyNasPy"
        self.config_file = self.config_dir / "synaspy_config.json"

        # Konfigurationsdictionary
        self.config = {}

        # Konfiguration laden
        self.load_config()

    def load_config(self):
        """Lädt die Konfiguration aus QSettings und JSON-Datei."""
        # Zuerst Standardwerte setzen
        self.config = self.DEFAULTS.copy()

        # JSON-Datei laden (hat Vorrang vor QSettings)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    json_config = json.load(f)
                    self.config.update(json_config)
            except Exception as e:
                print(f"Fehler beim Laden der JSON-Konfiguration: {e}")

        # QSettings laden (überschreibt JSON)
        for key in self.DEFAULTS.keys():
            value = self.settings.value(key)
            if value is not None:
                default_type = type(self.DEFAULTS[key])
                if default_type == bool:
                    self.config[key] = value.lower() in ("true", "1", "yes")
                elif default_type == int:
                    try:
                        self.config[key] = int(value)
                    except:
                        pass
                elif default_type == list:
                    if isinstance(value, str):
                        try:
                            self.config[key] = json.loads(value)
                        except:
                            self.config[key] = value.split(",")
                    else:
                        self.config[key] = value
                else:
                    self.config[key] = value

        # Pfade expandieren (NUR für SSH und Statusdatei)
        self.config["ssh_key_path"] = os.path.expanduser(self.config["ssh_key_path"])
        self.config["status_file_path"] = os.path.expanduser(
            self.config["status_file_path"]
        )

    def save_config(self):
        """Speichert die Konfiguration in QSettings und JSON-Datei."""
        # In QSettings speichern
        for key, value in self.config.items():
            if isinstance(value, list):
                self.settings.setValue(key, json.dumps(value))
            elif isinstance(value, bool):
                self.settings.setValue(key, str(value).lower())
            else:
                self.settings.setValue(key, value)

        # JSON-Datei speichern
        try:
            self.config_dir.mkdir(exist_ok=True)
            # Nur die wichtigen Einstellungen speichern
            save_config = {
                "nas_user": self.config["nas_user"],
                "nas_dns": self.config["nas_dns"],
                "nas_ip": self.config["nas_ip"],
                "nas_mac": self.config["nas_mac"],
                "ssh_key_path": self.config["ssh_key_path"],
                "volume_list": self.config["volume_list"],
                "auto_shutdown_delay": self.config["auto_shutdown_delay"],
                "auto_start_delay": self.config["auto_start_delay"],
                "wol_wait_time": self.config["wol_wait_time"],
                "smb_wait_time": self.config["smb_wait_time"],
                "mount_retries": self.config["mount_retries"],
                "status_file_path": self.config["status_file_path"],
            }

            with open(self.config_file, "w") as f:
                json.dump(save_config, f, indent=2)

        except Exception as e:
            print(f"Fehler beim Speichern der JSON-Konfiguration: {e}")

    def get(self, key, default=None):
        """Gibt einen Konfigurationswert zurück."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Setzt einen Konfigurationswert."""
        self.config[key] = value
        self.save_config()

    def get_volumes(self):
        """Gibt die Liste der Volumes zurück."""
        return self.config.get("volume_list", self.DEFAULTS["volume_list"])


# =======================================
# KONFIGURATIONS-DIALOG
# =======================================


class ConfigDialog(QDialog):
    """Dialog zur Konfiguration der NAS-Einstellungen."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        # Logger vom Parent übernehmen
        if parent and hasattr(parent, "logger"):
            self.logger = parent.logger
        else:
            # Fallback: Dummy-Logger erstellen
            self.logger = AppLogger()
        self.initUI()
        self.load_values()

    def initUI(self):
        """Initialisiert die Dialog-Benutzeroberfläche."""
        self.setWindowTitle("SyNasPy - Einstellungen")
        self.setFixedSize(650, 700)

        # Stil vom Hauptfenster übernehmen
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #000000;
            }
            QLabel {
                color: #ffffff;
                font-family: Helvetica, Arial, sans-serif;
            }
            QLabel#section_title {
                font-weight: bold;
                font-size: 14px;
                color: #007AFF;
                padding: 8px 0;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
                font-family: Helvetica, Arial, sans-serif;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #007AFF;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px 16px;
                margin: 4px;
                border-radius: 4px;
                border: 1px solid #333;
                background-color: #2a2a2a;
                color: white;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #007AFF;
            }
            QPushButton#btn_save {
                background-color: #007AFF;
            }
            QPushButton#btn_save:hover {
                background-color: #0055CC;
            }
            QPushButton#btn_cancel {
                background-color: #555;
            }
            QPushButton#btn_cancel:hover {
                background-color: #666;
            }
            QPushButton#btn_ssh_help {
                background-color: #2a2a2a;
                font-size: 12px;
                padding: 4px 10px;
                min-width: 60px;
            }
            QPushButton#btn_ssh_help:hover {
                background-color: #3a3a3a;
                border: 1px solid #FF6B00;
            }
            QPushButton#btn_find_mac {
                background-color: #2a2a2a;
                font-size: 12px;
                padding: 4px 10px;
                min-width: 80px;
            }
            QPushButton#btn_find_mac:hover {
                background-color: #3a3a3a;
                border: 1px solid #00FF00;
            }
            QPushButton#btn_find_ip {
                background-color: #2a2a2a;
                font-size: 12px;
                padding: 4px 10px;
                min-width: 80px;
            }
            QPushButton#btn_find_ip:hover {
                background-color: #3a3a3a;
                border: 1px solid #00FF00;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #cccccc;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ==================================
        # HEADER-Bereich mit Logo und Titel
        # ==================================

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Linkes Logo - DIREKTEN Pfad verwenden
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "BinhDiez.png")

        if os.path.exists(logo_path):
            try:
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    logo_label = QLabel()
                    logo_label.setPixmap(
                        pixmap.scaled(
                            80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    header_layout.addStretch()
                    header_layout.addWidget(logo_label)
                    header_layout.addStretch()
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_action("Logo geladen", "Erfolgreich")
                        except:
                            pass
                else:
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_error(
                                "Logo konnte nicht geladen werden", "QPixmap ist null"
                            )
                        except:
                            pass
            except Exception as e:
                if hasattr(self, "logger"):
                    try:
                        self.logger.log_error("Fehler beim Laden des Logos", str(e), e)
                    except:
                        pass
        else:
            if hasattr(self, "logger"):
                try:
                    self.logger.log_error("Logo nicht gefunden", f"Pfad: {logo_path}")
                except:
                    pass

        # Titel in der Mitte
        title_label = QLabel("Synology NAS Management")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Rechtes Icon
        icon_path = os.path.join(script_dir, "SyNasPy.png")

        if os.path.exists(icon_path):
            try:
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    icon_label = QLabel()
                    icon_label.setPixmap(
                        pixmap.scaled(
                            60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    header_layout.addStretch()
                    header_layout.addWidget(icon_label)
                    header_layout.addStretch()
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_action("Icon geladen", "Erfolgreich")
                        except:
                            pass
                else:
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_error(
                                "Icon konnte nicht geladen werden", "QPixmap ist null"
                            )
                        except:
                            pass
            except Exception as e:
                if hasattr(self, "logger"):
                    try:
                        self.logger.log_error("Fehler beim Laden des Icon", str(e), e)
                    except:
                        pass
        else:
            if hasattr(self, "logger"):
                self.logger.log_error("Icon nicht gefunden", f"Pfad: {icon_path}")

        main_layout.addLayout(header_layout)

        # Scrollbereich für Einstellungen
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === NAS Einstellungen ===
        nas_group = QGroupBox("NAS Server Einstellungen")
        nas_layout = QGridLayout()
        nas_layout.setSpacing(10)

        row = 0
        nas_layout.addWidget(QLabel("Benutzername:"), row, 0)
        self.nas_user_edit = QLineEdit()
        self.nas_user_edit.setPlaceholderText("z.B. nasuser")
        nas_layout.addWidget(self.nas_user_edit, row, 1)

        row += 1
        nas_layout.addWidget(QLabel("DNS-Name:"), row, 0)
        self.nas_dns_edit = QLineEdit()
        self.nas_dns_edit.setPlaceholderText("z.B. NAS-Synology.local")
        nas_layout.addWidget(self.nas_dns_edit, row, 1)

        row += 1
        nas_layout.addWidget(QLabel("IP-Adresse:"), row, 0)
        ip_layout = QHBoxLayout()
        self.nas_ip_edit = QLineEdit()
        self.nas_ip_edit.setPlaceholderText("z.B. 192.168.1.100")
        ip_layout.addWidget(self.nas_ip_edit)

        find_ip_btn = QPushButton("🔍 IP finden")
        find_ip_btn.setObjectName("btn_find_ip")
        find_ip_btn.setToolTip("Automatisch die Server-IP im Netzwerk suchen")
        find_ip_btn.clicked.connect(self.find_server_ip)
        ip_layout.addWidget(find_ip_btn)
        nas_layout.addLayout(ip_layout, row, 1)

        row += 1
        nas_layout.addWidget(QLabel("MAC-Adresse:"), row, 0)
        mac_layout = QHBoxLayout()
        self.nas_mac_edit = QLineEdit()
        self.nas_mac_edit.setPlaceholderText("xx:xx:xx:xx:xx:xx")
        mac_layout.addWidget(self.nas_mac_edit)

        # Hilfe-Button statt Erkennungs-Button
        mac_help_btn = QPushButton("? Hilfe")
        mac_help_btn.setObjectName("btn_mac_help")
        mac_help_btn.setToolTip("Anleitung zum Finden der MAC-Adresse")
        mac_help_btn.clicked.connect(self.find_mac_address)
        mac_layout.addWidget(mac_help_btn)
        nas_layout.addLayout(mac_layout, row, 1)

        row += 1
        nas_layout.addWidget(QLabel("SSH-Key Pfad:"), row, 0)
        ssh_layout = QHBoxLayout()
        self.ssh_key_edit = QLineEdit()
        self.ssh_key_edit.setPlaceholderText("~/.ssh/id_rsa")
        ssh_layout.addWidget(self.ssh_key_edit)

        ssh_help_btn = QPushButton("? Hilfe")
        ssh_help_btn.setObjectName("btn_ssh_help")
        ssh_help_btn.clicked.connect(self.show_ssh_help)
        ssh_layout.addWidget(ssh_help_btn)
        nas_layout.addLayout(ssh_layout, row, 1)

        nas_group.setLayout(nas_layout)
        scroll_layout.addWidget(nas_group)

        # === Volumes Einstellungen ===
        volumes_group = QGroupBox("Volumes")
        volumes_layout = QVBoxLayout()

        self.volumes_text = QTextEdit()
        self.volumes_text.setMaximumHeight(100)
        self.volumes_text.setPlaceholderText("Ein Volume pro Zeile")
        volumes_layout.addWidget(QLabel("Volumes (ein Name pro Zeile):"))
        volumes_layout.addWidget(self.volumes_text)

        volumes_hint = QLabel(
            'Hinweis: "NAS Dokumente" wird automatisch als Haupt-Volume behandelt'
        )
        volumes_hint.setStyleSheet("color: #888888; font-size: 11px;")
        volumes_layout.addWidget(volumes_hint)

        volumes_group.setLayout(volumes_layout)
        scroll_layout.addWidget(volumes_group)

        # === Zeiteinstellungen ===
        time_group = QGroupBox("Zeiteinstellungen (Sekunden)")
        time_layout = QGridLayout()
        time_layout.setSpacing(10)

        row = 0
        time_layout.addWidget(QLabel("Auto-Shutdown Verzögerung:"), row, 0)
        self.auto_shutdown_spin = QSpinBox()
        self.auto_shutdown_spin.setRange(10, 600)
        self.auto_shutdown_spin.setSuffix(" s")
        time_layout.addWidget(self.auto_shutdown_spin, row, 1)

        row += 1
        time_layout.addWidget(QLabel("Auto-Start Verzögerung:"), row, 0)
        self.auto_start_spin = QSpinBox()
        self.auto_start_spin.setRange(10, 600)
        self.auto_start_spin.setSuffix(" s")
        time_layout.addWidget(self.auto_start_spin, row, 1)

        row += 1
        time_layout.addWidget(QLabel("WOL Wartezeit (max):"), row, 0)
        self.wol_wait_spin = QSpinBox()
        self.wol_wait_spin.setRange(30, 600)
        self.wol_wait_spin.setSuffix(" s")
        time_layout.addWidget(self.wol_wait_spin, row, 1)

        row += 1
        time_layout.addWidget(QLabel("SMB Wartezeit:"), row, 0)
        self.smb_wait_spin = QSpinBox()
        self.smb_wait_spin.setRange(5, 120)
        self.smb_wait_spin.setSuffix(" s")
        time_layout.addWidget(self.smb_wait_spin, row, 1)

        row += 1
        time_layout.addWidget(QLabel("Mount Wiederholungen:"), row, 0)
        self.mount_retries_spin = QSpinBox()
        self.mount_retries_spin.setRange(1, 10)
        time_layout.addWidget(self.mount_retries_spin, row, 1)

        time_group.setLayout(time_layout)
        scroll_layout.addWidget(time_group)

        # === Statusdatei ===
        status_group = QGroupBox("Statusdatei")
        status_layout = QHBoxLayout()
        self.status_file_edit = QLineEdit()
        self.status_file_edit.setPlaceholderText("~/Downloads/boQuitNASapp.txt")
        status_layout.addWidget(self.status_file_edit)
        status_group.setLayout(status_layout)
        scroll_layout.addWidget(status_group)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # === Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("btn_save")
        save_btn.clicked.connect(self.save_and_accept)
        button_layout.addWidget(save_btn)

        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        # Status-Label für Feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #888888; font-size: 11px; padding: 5px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # Dialog zentrieren
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            self.move(
                parent.x() + (parent.width() - self.width()) // 2,
                parent.y() + (parent.height() - self.height()) // 2,
            )

    def load_values(self):
        """Lädt die aktuellen Konfigurationswerte in die GUI."""
        self.nas_user_edit.setText(self.config.get("nas_user", ""))
        self.nas_dns_edit.setText(self.config.get("nas_dns", ""))
        self.nas_ip_edit.setText(self.config.get("nas_ip", ""))
        self.nas_mac_edit.setText(self.config.get("nas_mac", ""))
        self.ssh_key_edit.setText(self.config.get("ssh_key_path", ""))

        # Volumes als Text
        volumes = self.config.get("volume_list", [])
        self.volumes_text.setText("\n".join(volumes))

        # Zeiteinstellungen
        self.auto_shutdown_spin.setValue(self.config.get("auto_shutdown_delay", 120))
        self.auto_start_spin.setValue(self.config.get("auto_start_delay", 120))
        self.wol_wait_spin.setValue(self.config.get("wol_wait_time", 180))
        self.smb_wait_spin.setValue(self.config.get("smb_wait_time", 30))
        self.mount_retries_spin.setValue(self.config.get("mount_retries", 3))

        self.status_file_edit.setText(self.config.get("status_file_path", ""))

    def save_and_accept(self):
        """Speichert die Werte und schließt den Dialog."""
        # Werte aus GUI übernehmen
        self.config.set("nas_user", self.nas_user_edit.text().strip())
        self.config.set("nas_dns", self.nas_dns_edit.text().strip())
        self.config.set("nas_ip", self.nas_ip_edit.text().strip())
        self.config.set("nas_mac", self.nas_mac_edit.text().strip())
        self.config.set("ssh_key_path", self.ssh_key_edit.text().strip())

        # Volumes parsen (ein Name pro Zeile)
        volumes_text = self.volumes_text.toPlainText().strip()
        volumes = [v.strip() for v in volumes_text.split("\n") if v.strip()]
        if volumes:
            self.config.set("volume_list", volumes)

        # Zeiteinstellungen
        self.config.set("auto_shutdown_delay", self.auto_shutdown_spin.value())
        self.config.set("auto_start_delay", self.auto_start_spin.value())
        self.config.set("wol_wait_time", self.wol_wait_spin.value())
        self.config.set("smb_wait_time", self.smb_wait_spin.value())
        self.config.set("mount_retries", self.mount_retries_spin.value())

        self.config.set("status_file_path", self.status_file_edit.text().strip())

        self.config.save_config()
        self.accept()

    def reset_defaults(self):
        """Setzt alle Werte auf die Standardwerte zurück."""
        reply = QMessageBox.question(
            self,
            "Zurücksetzen",
            "Alle Einstellungen auf Standardwerte zurücksetzen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            for key, value in Config.DEFAULTS.items():
                if key not in ["logo_file", "app_icon_file"]:
                    self.config.set(key, value)
            self.load_values()

            QMessageBox.information(
                self,
                "Zurückgesetzt",
                "Alle Einstellungen wurden auf die Standardwerte zurückgesetzt.",
            )

    def show_ssh_help(self):
        """Zeigt Hilfe zum SSH-Key an."""
        help_text = """
        <h2>SSH-Key für NAS-Zugriff</h2>

        <p><b>Was ist ein SSH-Key?</b></p>
        <p>Ein SSH-Key ist ein digitaler Schlüssel, der eine sichere Verbindung
        zu Ihrem NAS-Server ermöglicht, ohne dass Sie jedes Mal ein Passwort
        eingeben müssen.</p>

        <p><b>So erstellen Sie einen SSH-Key:</b></p>
        <ol>
            <li>Öffnen Sie das Terminal</li>
            <li>Führen Sie aus: <code>ssh-keygen -t rsa -b 4096</code></li>
            <li>Drücken Sie Enter für den Standardpfad (~/.ssh/id_rsa)</li>
            <li>Geben Sie eine Passphrase ein (optional, aber empfohlen)</li>
        </ol>

        <p><b>So installieren Sie den Key auf dem NAS:</b></p>
        <ol>
            <li>Kopieren Sie den öffentlichen Key:
                <code>cat ~/.ssh/id_rsa.pub</code></li>
            <li>Fügen Sie ihn in die Datei ein:
                <code>~/.ssh/authorized_keys</code> auf dem NAS</li>
            <li>Oder verwenden Sie:
                <code>ssh-copy-id nasuser@NAS-Synology</code></li>
        </ol>

        <p><b>Wichtige Hinweise:</b></p>
        <ul>
            <li>Der private Key muss auf Ihrem Mac bleiben (id_rsa)</li>
            <li>Der öffentliche Key (id_rsa.pub) kommt auf den NAS</li>
            <li>Schützen Sie Ihren privaten Key immer gut!</li>
        </ul>
        """

        QMessageBox.information(self, "SSH-Key Hilfe", help_text)

    # ### MAC Adresse Finden

    def _is_synology_mac(self, mac):
        """Prüft ob die MAC-Adresse zu Synology gehört (OUI)."""
        # Synology OUI: 00:11:32, 00:17:42, 00:19:99, 00:25:90, 00:26:09, 00:26:2C, 00:50:8B
        synology_ouis = [
            "00:11:32",
            "00:17:42",
            "00:19:99",
            "00:25:90",
            "00:26:09",
            "00:26:2C",
            "00:50:8B",
            "00:0C:29",
            "00:1B:21",
        ]
        mac_upper = mac.upper()
        for oui in synology_ouis:
            if mac_upper.startswith(oui):
                return True
        return False

    ### ===================================
    ### MAC Adresse Finden
    ### ===================================

    def find_mac_address(self):
        """Zeigt eine Anleitung zum Finden der MAC-Adresse."""
        help_text = """
        <h2>So finden Sie die MAC-Adresse Ihres Synology NAS</h2>

        <p><b>Methode 1: Über die FRITZ!Box-Oberfläche (Empfohlen - Einfachste Methode)</b></p>
        <ol>
            <li>Öffnen Sie die FRITZ!Box-Oberfläche im Browser: <b>http://fritz.box</b></li>
            <li>Melden Sie sich mit Ihrem FRITZ!Box-Passwort an</li>
            <li>Gehen Sie zu <b>Heimnetz</b> → <b>Netzwerk</b></li>
            <li>Suchen Sie Ihr Synology NAS in der Geräteliste</li>
            <li>Die MAC-Adresse wird in der Spalte <b>MAC-Adresse</b> angezeigt</li>
        </ol>

        <p><b>Methode 2: Über die DSM-Oberfläche</b></p>
        <ol>
            <li>Öffnen Sie die DSM-Oberfläche Ihres NAS im Browser</li>
            <li>Gehen Sie zu <b>Systemsteuerung</b></li>
            <li>Wählen Sie <b>Netzwerk</b> → <b>Netzwerkschnittstelle</b></li>
            <li>Die MAC-Adresse wird dort angezeigt (Format: XX:XX:XX:XX:XX:XX)</li>
        </ol>

        <p><b>Methode 3: Über das Terminal (wenn SSH aktiviert ist)</b></p>
        <ol>
            <li>Öffnen Sie das Terminal</li>
            <li>Führen Sie aus: <code>ssh nasuser@IHRE-NAS-IP</code></li>
            <li>Geben Sie dann ein: <code>ifconfig | grep ether</code></li>
            <li>Die MAC-Adresse wird angezeigt</li>
        </ol>

        <p><b>Methode 4: Über die NAS-App (DS Finder)</b></p>
        <ul>
            <li>Öffnen Sie die DS Finder App auf Ihrem Smartphone</li>
            <li>Wählen Sie Ihr NAS aus</li>
            <li>Die MAC-Adresse wird in den Geräteinformationen angezeigt</li>
        </ul>

        <p><b>Methode 5: Auf dem NAS-Gehäuse</b></p>
        <ul>
            <li>Bei vielen NAS-Modellen ist die MAC auf einem Aufkleber auf der Rückseite</li>
        </ul>

        <p><b>Wichtige Hinweise:</b></p>
        <ul>
            <li>Die MAC-Adresse ist eine eindeutige Hardware-Kennung</li>
            <li>Sie besteht aus 12 Hexadezimal-Ziffern (0-9, A-F)</li>
            <li>Im Feld muss sie im Format <b>XX:XX:XX:XX:XX:XX</b> eingegeben werden</li>
            <li>Die MAC-Adresse ändert sich nie und ist fest mit der Hardware verbunden</li>
            <li>Bei der FRITZ!Box sehen Sie auch die aktuelle IP-Adresse des NAS</li>
        </ul>

        <p style="color: #FF6B00;"><b>💡 Tipp:</b> Schreiben Sie sich die MAC-Adresse auf,
        Sie benötigen sie nur einmal für die Einrichtung.</p>
        """

        QMessageBox.information(self, "MAC-Adresse finden", help_text)

    def find_server_ip(self):
        """Sucht automatisch die IP-Adresse des NAS im Netzwerk."""
        self.status_label.setText("🔍 Suche nach Server-IP...")
        self.status_label.setStyleSheet(
            "color: #FFA500; font-size: 12px; padding: 5px;"
        )
        QApplication.processEvents()

        try:
            ips_found = []
            nas_dns = self.nas_dns_edit.text().strip()

            # Methode 1: Bonjour/mDNS (funktioniert auch im Stand-by)
            if nas_dns:
                ip = self._resolve_mdns(nas_dns)
                if ip:
                    ips_found.append(ip)
                    self.logger.log_action(
                        "IP via Bonjour gefunden", f"{nas_dns} -> {ip}"
                    )

            # Methode 2: DNS-Auflösung
            if nas_dns and not ips_found:
                ip = self._resolve_dns(nas_dns)
                if ip:
                    ips_found.append(ip)
                    self.logger.log_action("IP via DNS gefunden", f"{nas_dns} -> {ip}")

            # Methode 3: ARP-Tabelle nach Synology durchsuchen
            if not ips_found:
                ip = self._find_synology_ip_in_arp()
                if ip:
                    ips_found.append(ip)
                    self.logger.log_action("IP via ARP gefunden", ip)

            # Methode 4: Ping-Sweep (nur wenn NAS nicht im Stand-by)
            if not ips_found:
                ip = self._scan_for_synology_ip()
                if ip:
                    ips_found.append(ip)
                    self.logger.log_action("IP via Scan gefunden", ip)

            if ips_found:
                ip = ips_found[0]
                self.nas_ip_edit.setText(ip)
                self.status_label.setText(f"✅ Server-IP gefunden: {ip}")
                self.status_label.setStyleSheet(
                    "color: #00FF00; font-size: 12px; padding: 5px;"
                )

                QMessageBox.information(
                    self,
                    "Server-IP gefunden",
                    f"Die Server-IP wurde erfolgreich ermittelt:\n\n{ip}\n\n"
                    "Die IP wurde in das Feld eingetragen.",
                )
            else:
                self.status_label.setText("❌ Server-IP konnte nicht gefunden werden")
                self.status_label.setStyleSheet(
                    "color: #FF0000; font-size: 12px; padding: 5px;"
                )

                QMessageBox.warning(
                    self,
                    "Server-IP nicht gefunden",
                    "Die Server-IP konnte nicht automatisch ermittelt werden.\n\n"
                    "Bitte geben Sie die IP-Adresse manuell ein.\n\n"
                    "Tipps:\n"
                    "• Prüfen Sie den DNS-Namen in den Einstellungen\n"
                    "• Stellen Sie sicher, dass der NAS eingeschaltet ist\n"
                    "• Die IP finden Sie in der DSM-Oberfläche unter 'System > Netzwerk'",
                )

        except Exception as e:
            self.logger.log_error("Fehler bei IP-Suche", str(e), e)
            self.status_label.setText(f"❌ Fehler bei der IP-Suche: {str(e)[:50]}")
            self.status_label.setStyleSheet(
                "color: #FF0000; font-size: 12px; padding: 5px;"
            )

    def _resolve_mdns(self, dns_name):
        """Löst über mDNS/Bonjour auf."""
        try:
            result = subprocess.run(
                ["dns-sd", "-G", "v4", dns_name],
                capture_output=True,
                text=True,
                timeout=3,
            )

            ip_match = re.search(r"(\d{1,3}\.){3}\d{1,3}", result.stdout)
            if ip_match:
                return ip_match.group(0)

            return None
        except Exception as e:
            self.logger.log_error(
                "mDNS-Auflösung fehlgeschlagen", f"{dns_name}: {e}", e
            )
            return None

    def _resolve_dns(self, dns_name):
        """Löst DNS-Namen auf."""
        try:
            # dig für schnelle Auflösung
            result = subprocess.run(
                ["dig", "+short", dns_name], capture_output=True, text=True, timeout=2
            )

            lines = result.stdout.splitlines()
            for line in lines:
                if re.match(r"(\d{1,3}\.){3}\d{1,3}", line.strip()):
                    return line.strip()

            return None
        except Exception as e:
            self.logger.log_error("DNS-Auflösung fehlgeschlagen", f"{dns_name}: {e}", e)
            return None

    def _find_synology_ip_in_arp(self):
        """Sucht in der ARP-Tabelle nach Synology-IPs."""
        try:
            result = subprocess.run(
                ["arp", "-a"], capture_output=True, text=True, timeout=3
            )

            # Synology OUI-Liste
            synology_ouis = [
                "00:11:32",
                "00:17:42",
                "00:19:99",
                "00:25:90",
                "00:26:09",
                "00:26:2C",
                "00:50:8B",
                "00:0C:29",
                "00:1B:21",
            ]

            for line in result.stdout.splitlines():
                # MAC suchen
                mac_match = re.search(
                    r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", line, re.IGNORECASE
                )
                if mac_match:
                    mac = mac_match.group(0).upper()
                    for oui in synology_ouis:
                        if mac.startswith(oui):
                            # IP aus der Zeile extrahieren
                            ip_match = re.search(r"(\d{1,3}\.){3}\d{1,3}", line)
                            if ip_match:
                                return ip_match.group(0)

            return None
        except Exception as e:
            self.logger.log_error("ARP-Suche fehlgeschlagen", str(e), e)
            return None

    def _scan_for_synology_ip(self):
        """Scannt das Netzwerk nach Synology-IPs (wenn NAS online)."""
        try:
            current_ip = self._get_current_ip()
            if not current_ip:
                return None

            network_parts = current_ip.split(".")
            if len(network_parts) != 4:
                return None

            base_ip = ".".join(network_parts[:3])

            self.status_label.setText("🔍 Scanne Netzwerk nach Synology...")
            QApplication.processEvents()

            # Synology OUI-Liste
            synology_ouis = [
                "00:11:32",
                "00:17:42",
                "00:19:99",
                "00:25:90",
                "00:26:09",
                "00:26:2C",
                "00:50:8B",
                "00:0C:29",
                "00:1B:21",
            ]

            # Nur die ersten 50 IPs scannen für Geschwindigkeit
            for i in range(1, 51):
                if i % 10 == 0:
                    self.status_label.setText(f"🔍 Scanne IP {base_ip}.{i}/50...")
                    QApplication.processEvents()

                ip = f"{base_ip}.{i}"

                # Schneller Ping
                result = subprocess.run(
                    ["ping", "-c", "1", "-t", "1", ip], capture_output=True, timeout=1
                )

                if result.returncode == 0:
                    # ARP für diese IP
                    mac = self._get_mac_from_arp(ip)
                    if mac:
                        mac_upper = mac.upper()
                        for oui in synology_ouis:
                            if mac_upper.startswith(oui):
                                self.status_label.setText(f"✅ Synology gefunden: {ip}")
                                return ip

                    # Hostname prüfen
                    try:
                        result = subprocess.run(
                            ["host", ip], capture_output=True, text=True, timeout=1
                        )
                        if result.returncode == 0:
                            hostname = result.stdout.strip().split()[-1].rstrip(".")
                            if hostname and (
                                "synology" in hostname.lower()
                                or "nas" in hostname.lower()
                            ):
                                return ip
                    except:
                        pass

            return None
        except Exception as e:
            self.logger.log_error("Netzwerk-Scan fehlgeschlagen", str(e), e)
            return None

    def _get_mac_from_arp(self, ip):
        """Holt MAC für eine IP aus der ARP-Tabelle."""
        try:
            result = subprocess.run(
                ["arp", "-a", ip], capture_output=True, text=True, timeout=2
            )

            mac_match = re.search(
                r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", result.stdout, re.IGNORECASE
            )
            if mac_match:
                return mac_match.group(0)

            return None
        except:
            return None

    def _get_current_ip(self):
        """Ermittelt die aktuelle IP-Adresse."""
        try:
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            ip = result.stdout.strip()
            if ip and re.match(r"(\d{1,3}\.){3}\d{1,3}", ip):
                return ip

            return None
        except Exception as e:
            self.logger.log_error("IP-Ermittlung fehlgeschlagen", str(e), e)
            return None


# =======================================
# HAUPTKLASSE: SyNasPy - Hauptfenster
# =======================================


class SyNasPy(QMainWindow):
    def __init__(self):
        """Initialisiert die Hauptanwendung."""
        super().__init__()

        # 1. ZUERST Konfiguration laden
        self.config = Config()

        # 2. DANACH Logger initialisieren
        self.logger = AppLogger()
        self.logger.log_system_info()
        self.logger.log("SyNasPy gestartet", "START")
        self.logger.log_config(self.config.config)

        # 3. GUI initialisieren
        self.initUI()

        # 4. Timer und Counter initialisieren (NOCH NICHT STARTEN!)
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.autoSelect)
        self.timeout_counter: int = 0

        # Stelle sicher, dass timeout_limit immer ein int ist
        shutdown_delay = self.config.get("auto_shutdown_delay")
        self.timeout_limit: int = (
            shutdown_delay if isinstance(shutdown_delay, int) else 120
        )

        # 5. Serverstatus prüfen (HIER wird server_online gesetzt)
        self.checkServerStatus()

        # 6. JETZT Timer starten (NACH der Status-Prüfung)
        self.auto_timer.start(1000)
        self.logger.log_action("Timer gestartet", f"Verzögerung: {self.timeout_limit}s")

        # 7. JETZT Sprachausgabe (NACH dem Timer-Start)
        self.say_timer_status()

        # 8. Tastenkürzel für Einstellungen
        self.settings_action = QAction("Einstellungen", self)
        self.settings_action.setShortcut("Ctrl+E")
        self.settings_action.triggered.connect(self.open_settings)
        self.addAction(self.settings_action)

        # 9. Am Ende alle Logs schreiben
        self.logger.flush()

    def initUI(self):
        """Initialisiert die Benutzeroberfläche."""
        self.setWindowTitle("NAS Management")
        self.setFixedSize(500, 520)

        # Stylesheet für modernes, dunkles Design
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #000000;
            }
            QLabel {
                color: #ffffff;
                font-family: Helvetica, Arial, sans-serif;
            }
            QLabel#status_label {
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                background-color: #1a1a1a;
                border-radius: 4px;
                margin: 5px;
                border: 1px solid #333;
            }
            QPushButton {
                font-size: 16px;
                padding: 6px 10px;
                margin: 2px;
                border-radius: 4px;
                border: 1px solid #333;
                font-weight: normal;
                min-height: 20px;
                min-width: 70px;
                background-color: #2a2a2a;
                color: white;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #007AFF;
            }
            QPushButton#btn_shutdown_both {
                background-color: #d32f2f;
            }
            QPushButton#btn_shutdown_nas {
                background-color: #f57c00;
            }
            QPushButton#btn_cancel {
                background-color: #555;
            }
            QPushButton#btn_select_all {
                background-color: #2a2a2a;
                font-size: 10px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QPushButton#btn_start {
                background-color: #007AFF;
            }
            QPushButton#btn_settings {
                background-color: transparent;
                border: none;
                font-size: 20px;
                color: #666;
                min-width: 30px;
                padding: 0;
            }
            QPushButton#btn_settings:hover {
                color: #007AFF;
                background-color: transparent;
                border: none;
            }
            QProgressBar {
                border: 1px solid #333;
                border-radius: 3px;
                background-color: #1a1a1a;
                height: 18px;
                margin: 5px;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 3px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                padding: 3px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #555;
                border-radius: 2px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #007AFF;
                border: 1px solid #007AFF;
            }
            QCheckBox::indicator:disabled {
                background-color: #333;
                border: 1px solid #444;
            }
            QFrame#volumes_frame {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 5px;
                margin: 8px;
            }
            QLabel#volumes_title {
                font-weight: bold;
                color: #cccccc;
            }
            QMenuBar {
                background-color: #1a1a1a;
                color: #ffffff;
                border-bottom: 1px solid #333;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #2a2a2a;
            }
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #333;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;
            }
        """)

        # Fenster zentrieren
        screen = QDesktopWidget().screenGeometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

        # Haupt-Widget und Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ==================================
        # HEADER-Bereich mit Logo und Titel
        # ==================================

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Linkes Logo - DIREKTEN Pfad verwenden
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "BinhDiez.png")
        # self.logger.log_action("Lade Logo", os.path.basename(logo_path))

        if os.path.exists(logo_path):
            try:
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    logo_label = QLabel()
                    logo_label.setPixmap(
                        pixmap.scaled(
                            80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    header_layout.addStretch()
                    header_layout.addWidget(logo_label)
                    header_layout.addStretch()
                    self.logger.log_action("Logo geladen", "Erfolgreich")
                else:
                    self.logger.log_error(
                        "Logo konnte nicht geladen werden", "QPixmap ist null"
                    )
            except Exception as e:
                self.logger.log_error("Fehler beim Laden des Logos", str(e), e)
        else:
            self.logger.log_error("Logo nicht gefunden", f"Pfad: {logo_path}")

        # Titel in der Mitte
        title_label = QLabel("Synology NAS Management")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Rechtes Icon
        icon_path = os.path.join(script_dir, "SyNasPy.png")

        if os.path.exists(icon_path):
            try:
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    icon_label = QLabel()
                    icon_label.setPixmap(
                        pixmap.scaled(
                            60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    header_layout.addStretch()
                    header_layout.addWidget(icon_label)
                    header_layout.addStretch()
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_action("Icon geladen", "Erfolgreich")
                        except:
                            pass
                else:
                    if hasattr(self, "logger"):
                        try:
                            self.logger.log_error(
                                "Icon konnte nicht geladen werden", "QPixmap ist null"
                            )
                        except:
                            pass
            except Exception as e:
                if hasattr(self, "logger"):
                    try:
                        self.logger.log_error("Fehler beim Laden des Icon", str(e), e)
                    except:
                        pass
        else:
            if hasattr(self, "logger"):
                try:
                    self.logger.log_error("Icon nicht gefunden", f"Pfad: {logo_path}")
                except:
                    pass

        main_layout.addLayout(header_layout)

        # =====================================
        # STATUS-Anzeige und Fortschrittsbalken
        # =====================================

        self.status_label = QLabel("Prüfe Serverstatus...")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # ==========================
        # HAUPTBUTTONS für Aktionen
        # ==========================

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        self.button1 = QPushButton("Mac & NAS")
        self.button1.setObjectName("btn_shutdown_both")
        self.button1.setToolTip("Fährt Mac und NAS in 2min herunter")

        self.button2 = QPushButton("NAS")
        self.button2.setObjectName("btn_shutdown_nas")
        self.button2.setToolTip("Fährt nur NAS herunter")

        self.button3 = QPushButton("Abbrechen")
        self.button3.setObjectName("btn_cancel")
        self.button3.setToolTip("Schließt die App")

        self.button4 = QPushButton("Start NAS")
        self.button4.setObjectName("btn_start")
        self.button4.setToolTip("Startet NAS über Wake-on-LAN")

        # Settings Button (Zahnrad)
        settings_btn = QPushButton("⚙")
        settings_btn.setStyleSheet(
            "font-size: 50px; font-weight: bold; color: #ffffff;"
        )
        settings_btn.setObjectName("btn_settings")
        settings_btn.setToolTip("Einstellungen (Cmd+E)")
        settings_btn.clicked.connect(self.open_settings)

        buttons_layout.addWidget(self.button1)
        buttons_layout.addWidget(self.button2)
        buttons_layout.addWidget(self.button3)
        buttons_layout.addWidget(self.button4)
        buttons_layout.addWidget(settings_btn)

        main_layout.addLayout(buttons_layout)
        main_layout.addSpacing(10)

        # ======================
        # VOLUME-Auswahlbereich
        # ======================
        self.volumes_frame = QFrame()
        self.volumes_frame.setObjectName("volumes_frame")
        self.volumes_frame.setVisible(False)

        volumes_layout = QVBoxLayout(self.volumes_frame)
        volumes_layout.setSpacing(6)
        volumes_layout.setContentsMargins(12, 12, 12, 12)

        # Titelzeile mit "Alle"-Button
        title_layout = QHBoxLayout()
        self.volumes_title_label = QLabel("Verfügbare Volumes")
        self.volumes_title_label.setObjectName("volumes_title")
        title_layout.addWidget(self.volumes_title_label)
        title_layout.addStretch()

        self.select_all_btn = QPushButton("Alle")
        self.select_all_btn.setObjectName("btn_select_all")
        self.select_all_btn.setCheckable(True)
        title_layout.addWidget(self.select_all_btn)
        volumes_layout.addLayout(title_layout)

        # Scrollbarer Bereich für Volume-Checkboxen
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        scroll_area.setMinimumHeight(120)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(3)

        # Liste aller verfügbaren Volumes aus Konfiguration
        self.volume_checkboxes = {}
        self.all_volumes = self.config.get_volumes()

        # Checkboxen für jedes Volume erstellen
        for volume_name in self.all_volumes:
            checkbox = QCheckBox(volume_name)
            if volume_name == "NAS Dokumente":
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
            self.volume_checkboxes[volume_name] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        volumes_layout.addWidget(scroll_area)
        main_layout.addWidget(self.volumes_frame)

        # =========================
        # TIMER für Auto-Aktionen
        # =========================
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.autoSelect)
        self.timeout_counter = 0
        self.timeout_limit = self.config.get(
            "auto_shutdown_delay", 120
        )  # pyright: ignore[reportAttributeAccessIssue]

        # ==========================
        # SIGNAL-SLOT Verbindungen
        # ==========================
        self.button1.clicked.connect(lambda: self.handleChoice("both"))
        self.button2.clicked.connect(lambda: self.handleChoice("nas_only"))
        self.button3.clicked.connect(lambda: self.handleChoice("cancel"))
        self.button4.clicked.connect(lambda: self.handleChoice("start_nas"))
        self.select_all_btn.clicked.connect(self.toggle_all_volumes)

        # Initial alle Buttons ausblenden
        self.hideAllButtons()

    def check_resources(self):
        """Prüft ob alle Ressourcen vorhanden sind."""
        self.logger.log_action("Prüfe Ressourcen")

        # Prüfe ob wir in einer eingefrorenen App sind
        if getattr(sys, "frozen", False):
            self.logger.log_action(
                "App läuft als eingefrorene App",
                f"_MEIPASS: {os.path.basename(sys._MEIPASS)}",  # pyright: ignore[reportAttributeAccessIssue]
            )
            try:
                files = os.listdir(sys._MEIPASS)  # type: ignore
                image_files = [
                    f for f in files if f.endswith((".png", ".jpg", ".jpeg", ".gif"))
                ]
                self.logger.log_action(
                    "Bild-Dateien im Ressourcen-Verzeichnis",
                    f"{len(image_files)} Bilder: {', '.join(image_files)}",
                )
            except Exception as e:
                self.logger.log_error("Fehler beim Auflisten der Ressourcen", str(e), e)
        else:
            self.logger.log_action(
                "App läuft im Entwicklungsmodus",
                f"Verzeichnis: {os.path.basename(os.path.dirname(os.path.abspath(__file__)))}",
            )

        # Prüfe ob die Bilder existieren
        logo_path = resource_path(self.config.get("logo_file"))
        icon_path = resource_path(self.config.get("app_icon_file"))

        # DIESE ZEILEN AUSKOMMENTIEREN:
        # self.logger.log_action(
        #     "Logo",
        #     f"existiert: {os.path.exists(logo_path)} - {os.path.basename(logo_path)}"
        # )
        # self.logger.log_action(
        #     "Icon",
        #     f"existiert: {os.path.exists(icon_path)} - {os.path.basename(icon_path)}"
        # )

        # Wenn Bilder nicht gefunden werden, zeige NUR Bild-Dateien
        if not os.path.exists(logo_path) or not os.path.exists(icon_path):
            try:
                base_dir = (
                    os.path.dirname(os.path.abspath(__file__))
                    if not getattr(sys, "frozen", False)
                    else sys._MEIPASS  # pyright: ignore[reportAttributeAccessIssue]
                )
                files = os.listdir(base_dir)
                image_files = [
                    f for f in files if f.endswith((".png", ".jpg", ".jpeg", ".gif"))
                ]
                # DIESE ZEILE AUSKOMMENTIEREN:
                # self.logger.log_action(
                #     "Bild-Dateien im Basis-Verzeichnis",
                #     f"{len(image_files)} Bilder: {', '.join(image_files)}"
                # )
            except Exception as e:
                self.logger.log_error(
                    "Fehler beim Auflisten des Basis-Verzeichnisses", str(e), e
                )

    def open_settings(self):
        """Öffnet den Einstellungsdialog."""
        # Timer stoppen
        if hasattr(self, "auto_timer") and self.auto_timer.isActive():
            self.auto_timer.stop()
            self.logger.log_action("Timer gestoppt für Einstellungen\n")
            self.say_message("Einstellungen geöffnet")
            self.status_label.setText("Einstellungen geöffnet - Timer gestoppt")
            self.status_label.setStyleSheet(
                "color: #FF6B00; font-weight: bold; padding: 10px;"
            )
            self.timeout_counter = 0
            QApplication.processEvents()

        # Dialog öffnen
        dialog = ConfigDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            # Konfiguration wurde geändert
            self.logger.log_action("Einstellungen gespeichert")
            self.refresh_ui()
            self.say_message("Einstellungen gespeichert")
            self.status_label.setText("Einstellungen gespeichert")
            self.logger.log_config(self.config.config)

            # Timer neu starten mit aktualisierten Werten
            self.timeout_limit = self.config.get("auto_shutdown_delay", 120)  # type: ignore
            self.auto_timer.start(1000)
            self.logger.log_action(
                "Timer neu gestartet", f"Verzögerung: {self.timeout_limit}s"
            )

            # JETZT die Timer-Sprachausgabe (NACH dem Neustart)
            self.say_timer_status()

        else:
            # Dialog abgebrochen - Timer neu starten
            self.logger.log_action("Einstellungen abgebrochen\n")
            self.auto_timer.start(1000)
            self.say_message("Einstellungen abgebrochen")

            # JETZT die Timer-Sprachausgabe (NACH dem Neustart)
            self.say_timer_status()

        self.logger.flush()

    def refresh_ui(self):
        """Aktualisiert die GUI nach Konfigurationsänderungen."""
        try:
            # Volume-Liste aktualisieren
            new_volumes = self.config.get_volumes()
            if new_volumes != self.all_volumes:
                self.all_volumes = new_volumes
                self.rebuild_volume_checkboxes()

            # Timer-Limit aktualisieren
            self.timeout_limit = self.config.get("auto_shutdown_delay", 120)  # type: ignore
            self.logger.log_action(
                "GUI aktualisiert", f"Neue Volumes: {len(self.all_volumes)}"
            )
        except Exception as e:
            self.logger.log_error("Fehler beim Aktualisieren der GUI", str(e), e)

    def rebuild_volume_checkboxes(self):
        """Baut die Volume-Checkboxen neu auf."""
        try:
            scroll_area = self.volumes_frame.findChild(QScrollArea)
            if not scroll_area:
                return

            scroll_content = scroll_area.widget()
            if not scroll_content:
                return

            for checkbox in self.volume_checkboxes.values():
                checkbox.deleteLater()
            self.volume_checkboxes.clear()

            layout = scroll_content.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            for volume_name in self.all_volumes:
                checkbox = QCheckBox(volume_name)
                if volume_name == "NAS Dokumente":
                    checkbox.setChecked(True)
                    checkbox.setEnabled(False)
                self.volume_checkboxes[volume_name] = checkbox
                layout.addWidget(checkbox)

            layout.addStretch()  # pyright: ignore[reportAttributeAccessIssue]
            self.logger.log_action(
                "Volume-Checkboxen neu erstellt", f"{len(self.all_volumes)} Volumes"
            )
        except Exception as e:
            self.logger.log_error(
                "Fehler beim Neuerstellen der Volume-Checkboxen", str(e), e
            )

    # ======================
    # HILFSMETHODEN
    # ======================

    def hideAllButtons(self):
        """Blendet alle Aktionsbuttons aus und zeigt Fortschrittsbalken."""
        try:
            self.button1.setVisible(False)
            self.button2.setVisible(False)
            self.button3.setVisible(False)
            self.button4.setVisible(False)
            self.progress_bar.setVisible(True)
            self.volumes_frame.setVisible(False)
            self.setFixedSize(500, 280)
        except Exception as e:
            self.logger.log_error("Fehler beim Ausblenden der Buttons", str(e), e)

    def showAllButtons(self):
        """Zeigt alle Buttons entsprechend dem Modus an."""
        try:
            if self.server_online:
                self.button1.setVisible(True)
                self.button2.setVisible(True)
                self.button3.setVisible(True)
                self.button4.setVisible(False)
                self.volumes_frame.setVisible(True)
                self.setFixedSize(500, 520)
            else:
                self.button1.setVisible(False)
                self.button2.setVisible(False)
                self.button3.setVisible(True)
                self.button4.setVisible(True)
                self.volumes_frame.setVisible(True)
                self.setFixedSize(500, 520)
        except Exception as e:
            self.logger.log_error("Fehler beim Anzeigen der Buttons", str(e), e)

    def say_message(self, message):
        """Spricht eine Nachricht über die macOS Text-to-Speech Funktion."""
        try:
            if hasattr(self, "_last_say_time"):
                elapsed = time.time() - self._last_say_time
                if elapsed < 1.5:
                    # Wenn zu kurz, überspringen wir diese Nachricht
                    self.logger.log_action(
                        "Sprachausgabe übersprungen (zu schnell)", message
                    )
                    return

            subprocess.Popen(["say", message])
            self._last_say_time = time.time()
            self.logger.log_action("Sprachausgabe", message)
        except Exception as e:
            self.logger.log_error("Fehler bei Sprachausgabe", str(e), e)

    def say_timer_status(self):
        """Spricht den aktuellen Timer-Status mit Verzögerung."""
        if self.server_online:
            message = f"Mac und NAS Auto Shutdown in {self.timeout_limit} Sekunden - Enter für nur NAS - Escape zum Abbrechen"
        else:
            message = f"Der NAS Server wird in {self.timeout_limit} Sekunden gestartet - Enter zum sofortigen Start"

        # Warte 2 Sekunden und verwende die normale say_message Methode
        QTimer.singleShot(2000, lambda: self.say_message(message))

    # ==========================
    # SERVERSTATUS und GUI-MODI
    # ==========================

    def checkServerStatus(self):
        """Prüft, ob der NAS-Server erreichbar ist."""
        try:
            self.logger.log_action(
                "Prüfe Serverstatus", f"IP: {self.config.get('nas_ip')}"
            )
            self.status_label.setText("Prüfe Serververbindung...")
            QApplication.processEvents()

            nas_ip = self.config.get("nas_ip")

            try:
                result = subprocess.run(
                    ["ping", "-c", "2", "-t", "2", nas_ip],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )  # pyright: ignore[reportCallIssue]

                if result.returncode == 0 and "bytes from" in result.stdout:
                    self.server_online = True
                    self.logger.log_action("Server online", f"IP: {nas_ip}")
                    self.handleOnline()
                else:
                    self.server_online = False
                    self.logger.log_action(
                        "Server offline", f"IP: {nas_ip} - kein Ping"
                    )
                    self.handleOffline()

            except Exception as e:
                self.server_online = False
                self.logger.log_error("Ping fehlgeschlagen", f"IP: {nas_ip}", e)
                self.handleOffline()

        except Exception as e:
            self.logger.log_error("Fehler bei Serverstatus-Prüfung", str(e), e)
            self.server_online = False
            self.handleOffline()

    def handleOnline(self):
        """Konfiguriert GUI für Online-Modus."""
        try:
            self.logger.log_action("Server online - Normalmodus aktiv")

            # 1. ZUERST die Statusmeldung
            self.say_message("NAS Server ist erreichbar")
            self.status_label.setText("NAS Server ist online ✓")
            self.status_label.setStyleSheet(
                "color: #4CAF50; font-size: 14px; font-weight: bold; padding: 10px;"
            )

            status_file = self.config.get("status_file_path")
            if os.path.exists(status_file):
                try:
                    os.remove(status_file)
                    self.logger.log_action("Statusdatei gelöscht", status_file)
                except Exception as e:
                    self.logger.log_error(
                        "Fehler beim Löschen der Statusdatei", str(e), e
                    )

            # 2. GUI aktualisieren
            self.volumes_title_label.setText("Verfügbare Volumes")
            self.volumes_title_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

            for volume_name, checkbox in self.volume_checkboxes.items():
                if volume_name != "NAS Dokumente":
                    checkbox.setEnabled(True)
                    checkbox.stateChanged.connect(
                        lambda state, v=volume_name: self.on_volume_checkbox_changed(
                            v, state
                        )
                    )

            self.select_all_btn.setEnabled(True)
            self.showAllButtons()
            self.button2.setFocus()
            self.update_checkbox_status()

            # 3. Timer-Limit für Auto-Shutdown setzen
            self.timeout_counter = 0
            self.timeout_limit = self.config.get("auto_shutdown_delay", 120)  # type: ignore

            self.logger.log_action(
                "Auto-Shutdown Timer-Limit gesetzt",
                f"Verzögerung: {self.timeout_limit}s",
            )

            # 4. JETZT die Timer-Sprachausgabe (NACH dem Setzen des Limits)
            self.say_timer_status()

        except Exception as e:
            self.logger.log_error("Fehler im Online-Modus", str(e), e)

    def handleOffline(self):
        """Konfiguriert GUI für Offline-Modus."""
        try:
            self.logger.log_action("Server offline - Workaround-Modus aktiv")
            status_file = self.config.get("status_file_path")
            if os.path.exists(status_file):
                os.remove(status_file)
                self.logger.log_action("Statusdatei gelöscht", status_file)
                self.say_message("Workaround Datei gelöscht")
                QTimer.singleShot(2000, self.close)
                return

            # 1. ZUERST die Statusmeldung
            self.say_message("NAS Server ist offline")
            self.status_label.setText("NAS Server ist offline")
            self.status_label.setStyleSheet(
                "color: #f44336; font-weight: bold; padding: 10px;"
            )

            # 2. GUI aktualisieren
            self.volumes_title_label.setText("Volumes bei Start mounten")
            self.volumes_title_label.setStyleSheet("font-weight: bold; color: #888888;")

            for volume_name, checkbox in self.volume_checkboxes.items():
                checkbox.setEnabled(True)
                if volume_name != "NAS Dokumente":
                    checkbox.setToolTip("Wird beim Serverstart automatisch gemountet")

            self.select_all_btn.setEnabled(True)
            self.select_all_btn.setStyleSheet("")
            self.select_all_btn.setToolTip("Alle Volumes für Start vorauswählen")

            self.showAllButtons()
            self.button4.setFocus()

            # 3. Timer-Limit für Auto-Start setzen
            self.timeout_counter = 0
            self.timeout_limit = self.config.get("auto_start_delay", 120)  # type: ignore

            self.logger.log_action(
                "Auto-Start Timer-Limit gesetzt", f"Verzögerung: {self.timeout_limit}s"
            )

            # 4. JETZT die Timer-Sprachausgabe (NACH dem Setzen des Limits)
            self.say_timer_status()

        except Exception as e:
            self.logger.log_error("Fehler im Offline-Modus", str(e), e)

    def autoSelect(self):
        """Wird jede Sekunde aufgerufen und löst Auto-Aktion nach Timeout aus."""
        try:
            self.timeout_counter += 1
            remaining = int(self.timeout_limit) - self.timeout_counter

            if self.server_online:
                self.status_label.setText(
                    f"Auto-Shutdown in {remaining} Sekunden - ENTER für nur NAS"
                )
                if self.timeout_counter >= self.timeout_limit:
                    self.auto_timer.stop()
                    self.logger.log_action(
                        "Auto-Shutdown ausgelöst", "Timeout erreicht"
                    )
                    self.handleChoice("both")
            else:
                self.status_label.setText(
                    f"Auto-Start in {remaining} Sekunden - ENTER für sofortigen Start"
                )
                if self.timeout_counter >= self.timeout_limit:
                    self.auto_timer.stop()
                    self.logger.log_action("Auto-Start ausgelöst", "Timeout erreicht")
                    self.handleChoice("start_nas")
        except Exception as e:
            self.logger.log_error("Fehler im Auto-Select Timer", str(e), e)

    def handleChoice(self, choice):
        """Verarbeitet Benutzeraktionen oder Auto-Aktionen."""
        try:
            self.logger.log_action(f"Benutzeraktion: {choice}")
            if hasattr(self, "auto_timer"):
                self.auto_timer.stop()

            self.hideAllButtons()
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)

            if choice == "both":
                self.logger.log_action("Starte Shutdown (Mac + NAS)")
                self.say_message("Herunterfahren gestartet")
                self.status_label.setText("Fahre NAS und Mac herunter...")
                self.createStatusFile()
                self.ejectNetworkDrives()
                self.progress_bar.setValue(25)
                QTimer.singleShot(
                    2000, lambda: [self.shutdownNAS(), self.progress_bar.setValue(50)]
                )
                QTimer.singleShot(
                    10000, lambda: [self.shutdownMac(), self.progress_bar.setValue(100)]
                )
                QTimer.singleShot(12000, self.close)

            elif choice == "nas_only":
                self.logger.log_action("Starte Shutdown (nur NAS)")
                self.say_message("NAS wird heruntergefahren")
                self.status_label.setText("Fahre NAS herunter...")
                self.ejectNetworkDrives()
                self.progress_bar.setValue(33)
                QTimer.singleShot(
                    2000, lambda: [self.shutdownNAS(), self.progress_bar.setValue(66)]
                )
                QTimer.singleShot(
                    5000, lambda: [self.progress_bar.setValue(100), self.close()]
                )

            elif choice == "start_nas":
                self.logger.log_action("Starte NAS via WOL")
                self.say_message("Starte NAS")
                self.status_label.setText("Starte NAS über Wake-on-LAN...")
                self.progress_bar.setValue(20)
                self.startup_volumes = []
                for volume_name, checkbox in self.volume_checkboxes.items():
                    if checkbox.isChecked():
                        self.startup_volumes.append(volume_name)
                self.startNAS()

            elif choice == "cancel":
                self.logger.log_action("Aktion abgebrochen")
                self.say_message("Abgebrochen")
                self.status_label.setText("Abgebrochen - App wird geschlossen")
                self.progress_bar.setValue(100)
                QTimer.singleShot(1000, self.close)

            self.logger.flush()
        except Exception as e:
            self.logger.log_error("Fehler bei handleChoice", str(e), e)

    # ==============================
    # WAKE-ON-LAN FUNKTIONALITÄT
    # ==============================

    def startNAS(self):
        """Startet den NAS-Server über Wake-on-LAN."""
        try:
            self.logger.log_action(
                "Starte NAS via WOL", f"MAC: {self.config.get('nas_mac')}"
            )
            self.status_label.setText("Sende Magic Packet...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(10)

            nas_mac = self.config.get("nas_mac")
            nas_ip = self.config.get("nas_ip")

            success = False
            methods_tried = []

            # Methode 1: Python reine WOL-Implementierung
            try:
                self.status_label.setText("Sende WOL-Paket...")
                QApplication.processEvents()
                self.send_wol_python(nas_mac, nas_ip)
                methods_tried.append("Python")
                success = True
                self.logger.log_action("WOL erfolgreich", "Python-Methode")
                self.status_label.setText("Magic Packet gesendet")
            except Exception as e:
                methods_tried.append(f"Python fehlgeschlagen: {str(e)[:50]}...")
                self.logger.log_error("WOL Python-Methode fehlgeschlagen", str(e), e)
                self.status_label.setText(
                    "Python-Methode fehlgeschlagen, versuche nächste..."
                )
                QApplication.processEvents()

            # Methode 2: wakeonlan-Befehl
            if not success:
                try:
                    self.status_label.setText("Versuche wakeonlan...")
                    QApplication.processEvents()
                    result = subprocess.run(
                        ["which", "wakeonlan"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if result.returncode == 0 and "wakeonlan" in result.stdout:
                        wol_result = subprocess.run(
                            ["wakeonlan", nas_mac],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )  # pyright: ignore[reportCallIssue]

                        if wol_result.returncode == 0:
                            methods_tried.append("wakeonlan")
                            success = True
                            self.logger.log_action(
                                "WOL erfolgreich", "wakeonlan-Befehl"
                            )
                            self.status_label.setText("Magic Packet gesendet")
                        else:
                            methods_tried.append("wakeonlan Befehl fehlgeschlagen")
                            self.logger.log_error(
                                "WOL wakeonlan fehlgeschlagen", wol_result.stderr
                            )
                    else:
                        methods_tried.append("wakeonlan nicht installiert")
                        self.logger.log_action("wakeonlan nicht installiert")

                except Exception as e:
                    methods_tried.append(
                        f"wakeonlan Ausführung fehlgeschlagen: {str(e)[:50]}..."
                    )
                    self.logger.log_error("WOL wakeonlan Exception", str(e), e)
                    self.status_label.setText(
                        "wakeonlan fehlgeschlagen, versuche nächste..."
                    )
                    QApplication.processEvents()

            # Methode 3: etherwake-Befehl
            if not success:
                try:
                    self.status_label.setText("Versuche etherwake...")
                    QApplication.processEvents()

                    interface = self.get_active_interface()

                    try:
                        ether_result = subprocess.run(
                            ["etherwake", "-i", interface, nas_mac],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )  # type: ignore

                        if ether_result.returncode == 0:
                            methods_tried.append("etherwake ohne sudo")
                            success = True
                            self.logger.log_action(
                                "WOL erfolgreich", "etherwake ohne sudo"
                            )
                            self.status_label.setText("Magic Packet gesendet")
                        else:
                            ether_result = subprocess.run(
                                ["sudo", "etherwake", "-i", interface, nas_mac],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                input=f"{getpass.getuser()}\n",
                            )  # pyright: ignore[reportCallIssue]

                            if ether_result.returncode == 0:
                                methods_tried.append("etherwake mit sudo")
                                success = True
                                self.logger.log_action(
                                    "WOL erfolgreich", "etherwake mit sudo"
                                )
                                self.status_label.setText("Magic Packet gesendet")
                            else:
                                methods_tried.append(
                                    "etherwake mit sudo fehlgeschlagen"
                                )
                                self.logger.log_error(
                                    "WOL etherwake mit sudo fehlgeschlagen",
                                    ether_result.stderr,
                                )

                    except Exception as e:
                        methods_tried.append(
                            f"etherwake Ausführung fehlgeschlagen: {str(e)[:50]}..."
                        )
                        self.logger.log_error("WOL etherwake Exception", str(e), e)

                except Exception as e:
                    methods_tried.append(f"etherwake Gesamtfehler: {str(e)[:50]}...")
                    self.logger.log_error("WOL etherwake Gesamtfehler", str(e), e)

            if success:
                self.logger.log_action(
                    "WOL erfolgreich", f"Methoden: {', '.join(methods_tried)}"
                )
                self.say_message("Warte auf Serverstart")
                self.status_label.setText("Warte auf Serverstart...")
                self.progress_bar.setValue(30)
                self.waitForServerStart()
            else:
                self.logger.log_error(
                    "WOL komplett fehlgeschlagen",
                    f"Methoden: {', '.join(methods_tried)}",
                )
                self.say_message("Fehler beim Senden")
                self.status_label.setText("WOL fehlgeschlagen")
                self.progress_bar.setValue(0)
                QTimer.singleShot(3000, self.close)

            self.logger.flush()
        except Exception as e:
            self.logger.log_error("Fehler bei startNAS", str(e), e)

    def send_wol_python(self, mac_address, nas_ip):
        """Sendet ein Wake-on-LAN Magic Packet über reine Python-Sockets."""
        try:
            mac_hex = mac_address.replace(":", "").replace("-", "")
            if len(mac_hex) != 12:
                raise ValueError(f"Ungültige MAC-Adresse: {mac_address}")

            mac_bytes = bytes.fromhex(mac_hex)
            magic_packet = b"\xff" * 6 + mac_bytes * 16

            broadcast_addresses = [
                "255.255.255.255",
                nas_ip.rsplit(".", 1)[0] + ".255",
                "192.168.1.255",
            ]

            wol_port = 9
            success = False

            for broadcast_addr in broadcast_addresses:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(2)
                    sock.sendto(magic_packet, (broadcast_addr, wol_port))
                    sock.close()
                    self.logger.log_action(
                        "WOL Python-Methode",
                        f"Packet an {broadcast_addr}:{wol_port} gesendet",
                    )
                    success = True
                    break
                except socket.error as e:
                    self.logger.log_error(
                        "WOL Python Socket-Fehler", f"{broadcast_addr}: {e}", e
                    )
                    continue

            if not success:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(2)
                    sock.sendto(magic_packet, (nas_ip, wol_port))
                    sock.close()
                    self.logger.log_action(
                        "WOL Python-Methode",
                        f"Packet direkt an {nas_ip}:{wol_port} gesendet",
                    )
                    success = True
                except socket.error as e:
                    self.logger.log_error(
                        "WOL Python direkter Socket-Fehler", str(e), e
                    )
                    raise Exception(f"WOL über Python-Sockets fehlgeschlagen: {e}")

            return success
        except Exception as e:
            self.logger.log_error("send_wol_python Fehler", str(e), e)
            raise

    def get_active_interface(self):
        """Ermittelt das aktive Netzwerkinterface für WOL."""
        try:
            result = subprocess.run(
                ["route", "get", "default"], capture_output=True, text=True
            )

            for line in result.stdout.splitlines():
                if "interface:" in line:
                    interface = line.split(":")[1].strip()
                    self.logger.log_action(
                        "Interface ermittelt", f"route get: {interface}"
                    )
                    return interface

        except Exception as e:
            self.logger.log_error(
                "Interface-Ermittlung route get fehlgeschlagen", str(e), e
            )

        try:
            result = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
            )

            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                if "Device:" in line and i + 1 < len(lines) and "en" in lines[i + 1]:
                    interface = lines[i + 1].split(":")[1].strip()
                    self.logger.log_action(
                        "Interface ermittelt", f"networksetup: {interface}"
                    )
                    return interface

        except Exception as e:
            self.logger.log_error(
                "Interface-Ermittlung networksetup fehlgeschlagen", str(e), e
            )

        self.logger.log_action("Interface default", "en0")
        return "en0"

    # ==============================
    # SERVERBEREITSCHAFT
    # ==============================

    def waitForServerStart(self):
        """Startet einen Thread, der auf Server-Start wartet."""
        self.wait_thread = threading.Thread(target=self._waitForServer)
        self.wait_thread.daemon = True
        self.wait_thread.start()

    def _waitForServer(self):
        """Thread-Funktion: Prüft regelmäßig, ob Server online ist."""
        try:
            nas_ip = self.config.get("nas_ip")
            total_wait = self.config.get("wol_wait_time", 180)
            check_interval = 10
            waited = 0

            self.logger.log_action("Warte auf Serverstart", f"Max: {total_wait}s")
            time.sleep(30)
            waited = 30
            QMetaObject.invokeMethod(
                self.progress_bar, "setValue", Qt.QueuedConnection, Q_ARG(int, 40)
            )

            while waited < total_wait:  # pyright: ignore[reportOperatorIssue]
                try:
                    result = subprocess.run(
                        ["ping", "-c", "2", "-t", "3", nas_ip],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )  # pyright: ignore[reportCallIssue]

                    if result.returncode == 0 and "bytes from" in result.stdout:
                        self.logger.log_action(
                            "Server startet", f"Erreichbar nach {waited}s"
                        )
                        QMetaObject.invokeMethod(
                            self, "serverIsUp", Qt.QueuedConnection
                        )
                        return
                except Exception as e:
                    self.logger.log_error(
                        "Ping während Wartezeit fehlgeschlagen", str(e), e
                    )

                progress = 40 + int(
                    (waited / total_wait) * 40  # pyright: ignore[reportOperatorIssue]
                )  # pyright: ignore[reportOperatorIssue]
                QMetaObject.invokeMethod(
                    self.progress_bar,
                    "setValue",
                    Qt.QueuedConnection,
                    Q_ARG(int, progress),
                )

                time.sleep(check_interval)
                waited += check_interval

            self.logger.log_error(
                "Serverstart timeout", f"Nach {total_wait}s nicht erreichbar"
            )
            QMetaObject.invokeMethod(self, "serverTimeout", Qt.QueuedConnection)
        except Exception as e:
            self.logger.log_error("Fehler im Wartethread", str(e), e)

    @pyqtSlot()
    def serverIsUp(self):
        """Wird aufgerufen, wenn Server erfolgreich gestartet wurde."""
        try:
            self.logger.log_action("Server erfolgreich gestartet")
            self.say_message("Server erreichbar")
            self.status_label.setText("Server online - warte auf SMB-Dienst...")

            # Typecast für den Type-Checker
            if self.progress_bar:
                self.progress_bar.setValue(70)

            smb_wait = self.config.get("smb_wait_time", 30)
            QTimer.singleShot(smb_wait * 1000, self._mountVolumesAfterDelay)
        except Exception as e:
            self.logger.log_error("Fehler in serverIsUp", str(e), e)

    @pyqtSlot()
    def serverTimeout(self):
        """Wird aufgerufen, wenn Server-Start timeoutet."""
        try:
            self.logger.log_action("Serverstart timeout")
            self.say_message("Server Start Zeitüberschreitung")
            self.status_label.setText("Timeout - Server konnte nicht gestartet werden")
            QTimer.singleShot(3000, self.close)
        except Exception as e:
            self.logger.log_error("Fehler in serverTimeout", str(e), e)

    # ========================================
    # VOLUME-MANAGEMENT
    # ========================================

    def on_volume_checkbox_changed(self, volume_name, state):
        """Wird aufgerufen, wenn Volume-Checkbox geändert wird."""
        try:
            if hasattr(self, "auto_timer"):
                self.auto_timer.stop()

            QTimer.singleShot(
                300, lambda: self.process_volume_change(volume_name, state)
            )
        except Exception as e:
            self.logger.log_error("Fehler in on_volume_checkbox_changed", str(e), e)

    def process_volume_change(self, volume_name, state):
        """Verarbeitet Volume-Änderungen (Mounten/Auswerfen)."""
        try:
            if state:
                self.logger.log_action("Volume mounten", volume_name)
                self.status_label.setText(f"Mounte {volume_name}...")
                success = self.mount_single_volume(volume_name)
                if not success:
                    self.volume_checkboxes[volume_name].setChecked(False)
                    self.logger.log_error("Volume mounten fehlgeschlagen", volume_name)
                    self.say_message("Fehler beim Mounten")
                    self.status_label.setText(
                        f"Fehler: {volume_name} konnte nicht gemountet werden"
                    )
                else:
                    self.logger.log_action("Volume gemountet", volume_name)
                    self.say_message(f"{volume_name} bereit")
                    self.status_label.setText(f"{volume_name} gemountet ✓")
            else:
                self.logger.log_action("Volume auswerfen", volume_name)
                self.say_message(f"Werfe {volume_name} aus")
                self.status_label.setText(f"Werfe {volume_name} aus...")
                success = self.unmount_single_volume(volume_name)
                if not success:
                    self.volume_checkboxes[volume_name].setChecked(True)
                    self.logger.log_error(
                        "Volume auswerfen fehlgeschlagen", volume_name
                    )
                    self.say_message("Fehler beim Auswerfen")
                    self.status_label.setText(
                        f"Fehler: {volume_name} konnte nicht ausgewerfen werden"
                    )
                else:
                    self.logger.log_action("Volume ausgewerfen", volume_name)
                    self.status_label.setText(f"{volume_name} ausgewerfen ✓")
        except Exception as e:
            self.logger.log_error("Fehler in process_volume_change", str(e), e)

    def toggle_all_volumes(self, checked):
        """Schaltet alle Volumes gleichzeitig um."""
        try:
            if checked:
                self.logger.log_action("Alle Volumes mounten")
                self.say_message("Mounte alle Volumes")
                self.status_label.setText("Mounte alle Volumes...")
                for volume_name, checkbox in self.volume_checkboxes.items():
                    if volume_name != "NAS Dokumente" and not checkbox.isChecked():
                        checkbox.setChecked(True)
                self.status_label.setText("Alle Volumes gemountet ✓")
            else:
                self.logger.log_action("Alle Volumes auswerfen")
                self.say_message("Werfe alle Volumes aus")
                self.status_label.setText("Werfe alle Volumes aus...")
                for volume_name, checkbox in self.volume_checkboxes.items():
                    if volume_name != "NAS Dokumente" and checkbox.isChecked():
                        checkbox.setChecked(False)
                self.status_label.setText("Alle Volumes ausgewerfen ✓")
        except Exception as e:
            self.logger.log_error("Fehler in toggle_all_volumes", str(e), e)

    def update_checkbox_status(self):
        """Aktualisiert Checkbox-Status basierend auf gemounteten Volumes."""
        try:
            mount_result = subprocess.run(["mount"], capture_output=True, text=True)
            mounted_text = mount_result.stdout

            for volume_name, checkbox in self.volume_checkboxes.items():
                if volume_name == "NAS Dokumente":
                    continue

                is_mounted = volume_name in mounted_text
                checkbox.blockSignals(True)
                checkbox.setChecked(is_mounted)
                checkbox.blockSignals(False)

            self.logger.log_action("Checkbox-Status aktualisiert")
        except Exception as e:
            self.logger.log_error("Fehler in update_checkbox_status", str(e), e)

    def _mountVolumesAfterDelay(self):
        """Mountet Volumes nach Verzögerung."""
        try:
            self.logger.log_action("Starte Volume-Mounting")
            self.status_label.setText("Mounte ausgewählte Volumes...")

            volumes_to_mount = ["NAS Dokumente"]
            for volume_name in self.startup_volumes:
                if volume_name != "NAS Dokumente":
                    volumes_to_mount.append(volume_name)

            success_count = 0
            self.progress_bar.setValue(70)
            successfully_mounted = []

            mount_retries = self.config.get("mount_retries", 3)

            for i, volume_name in enumerate(volumes_to_mount):
                self.status_label.setText(f"Mounte {volume_name}...")
                QApplication.processEvents()

                if volume_name == "NAS Dokumente":
                    time.sleep(5)

                success = self.mount_single_volume_with_retry(
                    volume_name, retries=mount_retries
                )
                if success:
                    success_count += 1
                    successfully_mounted.append(volume_name)
                    self.logger.log_action("Volume erfolgreich gemountet", volume_name)
                    self.say_message(f"{volume_name} bereit")
                else:
                    self.logger.log_error("Volume mounten fehlgeschlagen", volume_name)

                progress = 70 + int(((i + 1) / len(volumes_to_mount)) * 30)
                self.progress_bar.setValue(progress)
                time.sleep(3)

            self.progress_bar.setValue(100)
            if success_count > 0:
                self.logger.log_action(
                    "Volume-Mounting abgeschlossen",
                    f"{success_count} von {len(volumes_to_mount)} erfolgreich",
                )
                self.status_label.setText(
                    f"{success_count} von {len(volumes_to_mount)} Volumes gemountet ✓"
                )
            else:
                self.logger.log_error("Volume-Mounting komplett fehlgeschlagen")
                self.say_message("Keine Volumes gemountet")
                self.status_label.setText("Mounten fehlgeschlagen")

            QTimer.singleShot(2000, self.close)
        except Exception as e:
            self.logger.log_error("Fehler in _mountVolumesAfterDelay", str(e), e)

    def mount_single_volume(self, volume_name):
        """Mountet ein einzelnes Volume über SMB."""
        try:
            nas_user = self.config.get("nas_user")
            nas_ip = self.config.get("nas_ip")

            smb_url = f"smb://{nas_user}@{nas_ip}/{volume_name}"
            apple_script = f'try\n  mount volume "{smb_url}"\n  return "success"\non error err\n  return "error"\nend try'

            result = subprocess.run(
                ["osascript", "-e", apple_script],
                capture_output=True,
                text=True,
                timeout=30,
            )

            return "success" in result.stdout
        except Exception as e:
            self.logger.log_error(
                "mount_single_volume Fehler", f"{volume_name}: {e}", e
            )
            return False

    def mount_single_volume_with_retry(self, volume_name, retries=3):
        """Mountet ein Volume mit Wiederholungsversuchen."""
        nas_user = self.config.get("nas_user")
        nas_ip = self.config.get("nas_ip")

        for attempt in range(retries):
            try:
                if attempt > 0:
                    wait_time = 5 * attempt
                    self.logger.log_action(
                        "Volume-Mount Wiederholung",
                        f"{volume_name} Versuch {attempt+1}/{retries} nach {wait_time}s",
                    )
                    time.sleep(wait_time)

                smb_url = f"smb://{nas_user}@{nas_ip}/{volume_name}"
                apple_script = f'try\n  mount volume "{smb_url}"\n  return "success"\non error err\n  return "error"\nend try'

                result = subprocess.run(
                    ["osascript", "-e", apple_script],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if "success" in result.stdout:
                    time.sleep(2)
                    mount_check = subprocess.run(
                        ["mount"], capture_output=True, text=True
                    )
                    if volume_name in mount_check.stdout:
                        return True
                    else:
                        self.logger.log_error(
                            "Volume gemeldet aber nicht in mount-Liste", volume_name
                        )
                        continue

            except Exception as e:
                self.logger.log_error(
                    "Volume-Mount Versuch fehlgeschlagen",
                    f"{volume_name} Versuch {attempt+1}: {e}",
                    e,
                )
                continue

        return False

    def unmount_single_volume(self, volume_name):
        """Wirft ein einzelnes Volume aus."""
        try:
            mount_check = subprocess.run(["mount"], capture_output=True, text=True)
            if volume_name not in mount_check.stdout:
                return True

            apple_script = f"""
            try
                tell application "Finder"
                    eject disk "{volume_name}"
                end tell
                return "success"
            on error errMsg
                try
                    do shell script "diskutil unmount '/Volumes/{volume_name}'"
                    return "success"
                on error
                    return "error"
                end try
            end try
            """

            result = subprocess.run(
                ["osascript", "-e", apple_script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if "success" in result.stdout:
                time.sleep(1)
                mount_check = subprocess.run(["mount"], capture_output=True, text=True)
                return volume_name not in mount_check.stdout
            else:
                safe_name = volume_name.replace(" ", r"\ ")
                mount_point = f"/Volumes/{safe_name}"

                result = subprocess.run(
                    ["diskutil", "unmount", "force", mount_point],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    time.sleep(1)
                    mount_check = subprocess.run(
                        ["mount"], capture_output=True, text=True
                    )
                    return volume_name not in mount_check.stdout
                else:
                    subprocess.run(
                        ["umount", "-f", mount_point],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        timeout=5,
                    )
                    time.sleep(1)
                    mount_check = subprocess.run(
                        ["mount"], capture_output=True, text=True
                    )
                    return volume_name not in mount_check.stdout

        except Exception as e:
            self.logger.log_error(
                "unmount_single_volume Fehler", f"{volume_name}: {e}", e
            )
            return False

    # =====================================
    # HERUNTERFAHREN und SYSTEMOPERATIONEN
    # =====================================

    def ejectNetworkDrives(self):
        """Wirft alle Netzwerklaufwerke aus."""
        try:
            self.logger.log_action("Starte Auswerfen aller Netzwerklaufwerke")
            all_volumes = ["NAS Dokumente"] + list(self.volume_checkboxes.keys())

            mount_check = subprocess.run(["mount"], capture_output=True, text=True)
            mounted_volumes = []

            for volume_name in all_volumes:
                if volume_name in mount_check.stdout:
                    mounted_volumes.append(volume_name)
                    self.logger.log_action("Volume ist gemountet", volume_name)

            if not mounted_volumes:
                self.logger.log_action("Keine Volumes zum Auswerfen gefunden")
                return True

            self.logger.log_action(
                "Versuche Volumes auszuwerfen", f"{len(mounted_volumes)} Volumes"
            )

            applescript_cmd = """
            tell application "Finder"
                set ejectedVolumes to {}
                try
            """

            for volume_name in mounted_volumes:
                applescript_cmd += f'\n        eject disk "{volume_name}"'

            applescript_cmd += """
                    set ejectedVolumes to "success"
                on error errMsg
                    set ejectedVolumes to "error: " & errMsg
                end try
                return ejectedVolumes
            end tell
            """

            try:
                result = subprocess.run(
                    ["osascript", "-e", applescript_cmd],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.logger.log_action("AppleScript Auswerfen", result.stdout)
            except Exception as e:
                self.logger.log_error("AppleScript Auswerfen fehlgeschlagen", str(e), e)

            time.sleep(2)
            mount_check = subprocess.run(["mount"], capture_output=True, text=True)
            remaining_volumes = []

            for volume_name in mounted_volumes:
                if volume_name in mount_check.stdout:
                    remaining_volumes.append(volume_name)

            for volume_name in remaining_volumes:
                try:
                    safe_name = volume_name.replace(" ", r"\ ")
                    mount_point = f"/Volumes/{safe_name}"

                    self.logger.log_action(
                        "Versuche Volume mit diskutil auszuwerfen", volume_name
                    )
                    result = subprocess.run(
                        ["diskutil", "unmount", "force", mount_point],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode == 0:
                        self.logger.log_action(
                            "Volume mit diskutil ausgewerfen", volume_name
                        )
                    else:
                        self.logger.log_action(
                            "diskutil fehlgeschlagen, versuche umount -f", volume_name
                        )
                        subprocess.run(
                            ["umount", "-f", mount_point],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            timeout=5,
                        )
                        self.logger.log_action(
                            "Volume mit umount -f ausgewerfen", volume_name
                        )

                except Exception as e:
                    self.logger.log_error(
                        "Fehler beim Auswerfen von Volume", f"{volume_name}: {e}", e
                    )

            time.sleep(2)
            mount_check = subprocess.run(["mount"], capture_output=True, text=True)
            still_mounted = []

            for volume_name in mounted_volumes:
                if volume_name in mount_check.stdout:
                    still_mounted.append(volume_name)

            if still_mounted:
                self.logger.log_error(
                    "Volumes konnten nicht ausgewerfen werden",
                    f"{len(still_mounted)}: {', '.join(still_mounted)}",
                )
                return False
            else:
                self.logger.log_action("Alle Volumes erfolgreich ausgewerfen")
                return True

        except Exception as e:
            self.logger.log_error("ejectNetworkDrives Fehler", str(e), e)
            return False

    def shutdownNAS(self):
        """Fährt den NAS-Server über SSH herunter."""
        try:
            self.logger.log_action(
                "Starte NAS-Shutdown", f"IP: {self.config.get('nas_ip')}"
            )
            self.status_label.setText("Fahre NAS über SSH herunter...")
            QApplication.processEvents()

            nas_user = self.config.get("nas_user")
            nas_ip = self.config.get("nas_ip")
            ssh_key = self.config.get("ssh_key_path")

            cmd = [
                "ssh",
                "-i",
                ssh_key,
                "-o",
                "ConnectTimeout=10",
                "-o",
                "BatchMode=yes",
                f"{nas_user}@{nas_ip}",
                "sudo shutdown -h now",
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.logger.log_action("NAS-Shutdown-Befehl gesendet")
            self.status_label.setText("NAS-Shutdown-Befehl gesendet ✓")
        except Exception as e:
            self.logger.log_error("shutdownNAS Fehler", str(e), e)
            self.status_label.setText("Fehler beim NAS-Shutdown")

    def shutdownMac(self):
        """Fährt den lokalen Mac herunter."""
        try:
            self.logger.log_action("Starte Mac-Shutdown")
            self.status_label.setText("Fahre Mac herunter...")
            QTimer.singleShot(
                2000, lambda: subprocess.run(["sudo", "shutdown", "-h", "now"])
            )
        except Exception as e:
            self.logger.log_error("shutdownMac Fehler", str(e), e)

    def createStatusFile(self):
        """Erstellt Statusdatei für Workaround."""
        status_file = self.config.get("status_file_path")

        # Prüfen ob der Pfad existiert
        if not status_file:
            self.logger.log_error(
                "createStatusFile Fehler",
                "status_file_path nicht in der Konfiguration gefunden",
            )
            return

        try:
            with open(status_file, "w") as f:
                f.write(f"NAS App gestoppt am {datetime.now()}\n")
            os.chmod(status_file, 0o644)
            self.logger.log_action("Statusdatei erstellt", status_file)
        except Exception as e:
            self.logger.log_error("createStatusFile Fehler", str(e), e)

    # =====================
    # TASTATUR-HANDLING
    # =====================

    def keyPressEvent(self, event):
        """Behandelt Tastaturengaben."""
        if event.key() == Qt.Key_Escape:
            self.logger.log_action("ESC gedrückt - App wird geschlossen")
            self.status_label.setText("ESC gedrückt - App wird geschlossen")
            QTimer.singleShot(500, self.close)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            focused_widget = self.focusWidget()
            if isinstance(focused_widget, QPushButton):
                focused_widget.click()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Wird beim Schließen der App aufgerufen."""
        try:
            self.logger.log("=== SYNASPY BEENDET ===", "STOP")
            self.logger.flush()
            event.accept()
        except:
            event.accept()


# ======================
# HAUPTFUNKTION
# ======================


def main():
    """Hauptfunktion der Anwendung."""
    app = QApplication(sys.argv)

    # App-Icon setzen - DIREKT aus dem aktuellen Verzeichnis
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "SyNasPy.png")

    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    app.setStyle("Fusion")
    window = SyNasPy()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
