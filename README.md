# SyNasPy -- Synology-NAS-Management-Tool


SyNasPy is a powerful macOS GUI application for managing Synology NAS servers with Wake‑on‑LAN, shutdown, volume management, and full multi‑server support.

---

✨ Features

🚀 Core Functionality

· Wake‑on‑LAN (WOL): Start your NAS remotely with one click.
· Smart Shutdown: Gracefully shut down NAS and/or Mac with configurable delays.
· Auto‑Start / Auto‑Shutdown: Automatic actions with individual timeouts.
· Volume Management: Mount / unmount selected SMB volumes via checkboxes.
· SSH Integration: Secure communication using SSH keys (no passwords stored).

🎯 Multi‑Server & Advanced

· Multiple Server Profiles: Manage any number of Synology NAS devices.
· Quick Profile Switching: Drop‑down menu in the main window.
· Profile Management: Create, duplicate, rename, delete, and activate profiles.
· 17 Languages: Full UI translation (Deutsch, English, Español, Français, Ελληνικά, Italiano, Nederlands, Norsk, Polski, Português, Русский, Suomi, Svenska, Türkçe, Tiếng Việt, Čeština, العربية).
· Automatic IP Detection: Find NAS via Bonjour/mDNS, DNS, ARP, or network scan.
· SSH Key Assistant: Open .ssh folder, create a new key pair (does not overwrite id_rsa) with optional passphrase.
· Update Checker: Integrated manual and background update notifications.

🎨 User Interface

· Modern Dark Theme: Easy on the eyes with a professional look.
· Keyboard Shortcuts: Cmd+E for settings, ESC to cancel, Enter to confirm.
· Voice Feedback: Audio confirmation of actions (macOS only).
· Progress Indication: Visual feedback with progress bar and percentage.
· Timer Pause: Pause / resume auto‑countdown with a single button.

---

📋 Requirements

· Operating System: macOS 10.15 (Catalina) or later (Intel / Apple Silicon).
· Python: 3.9 or higher.
· Dependencies: PyQt5 (see requirements.txt).
· Synology NAS with:
  · SSH access enabled (for shutdown)
  · SMB file sharing (for volume mounting)
  · Wake‑on‑LAN capability

---

🔧 Installation

From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/SyNasPy.git
cd SyNasPy

# Install dependencies
pip install -r requirements.txt

# Run the application
python SyNasPy.py
```

Build as macOS App (optional)

```bash
# Install PyInstaller
pip install pyinstaller

# Build the app
pyinstaller --windowed --name "SyNasPy" --icon SyNasPy.icns SyNasPy.py

# The app will be in the dist/ folder
```

requirements.txt

```
PyQt5>=5.15.0
requests>=2.28.0      # for update checking
packaging>=21.0       # for version comparison
```

---

🚀 Quick Start

1. First Launch: The app creates default configuration and a default profile.
2. Open Settings: Click the gear icon (⚙) or press Cmd+E.
3. Configure a Profile:
   · Enter NAS username, DNS/IP, MAC address.
   · Set SSH key path (or create a new key with the 🔑 Erstellen button).
   · Define your SMB volumes (one per line; the first volume becomes the main volume and cannot be disabled).
   · Adjust timing values as needed.
4. Save: Click Save – your profile is stored.
5. Main Window:
   · Mac & NAS: Shut down both devices (with configurable delay between them).
   · NAS: Shut down only the NAS.
   · Start NAS: Wake the NAS via WOL.
   · Cancel: Close the app.

---

⚙️ Configuration

Settings Dialog Tabs

Tab Content
General Language selection, NAS credentials, SSH key path (with folder open and key creation buttons).
Volumes List of SMB volumes (one per line). The first volume is the main volume and cannot be unchecked.
Timing Auto‑shutdown delay, auto‑start delay, WOL wait, SMB wait, mount retries, and delay between NAS‑ and Mac‑shutdown (0–30 seconds).
Server Profiles Manage all profiles: create, duplicate, rename, delete, and set the active profile.

Configuration Files

All settings are stored in ~/.SyNasPy/:

· synaspy_config.json – global settings (language, logo, etc.).
· server_profiles.json – all server profiles (including the active profile ID).

Log Files

Logs are written to ~/Library/Application Support/SyNasPy/Logs/ with automatic rotation (max 5 files).

---

⌨️ Keyboard Shortcuts

Shortcut Action
Cmd+E Open Settings Dialog
ESC Cancel current operation / close app
Enter Trigger the focused button
Tab Navigate through controls

---

🔒 Security

· Uses SSH key authentication only (no passwords stored).
· Keys remain in the user’s home directory.
· No sensitive data is transmitted over the network.
· All operations use macOS system APIs.

---

🐛 Troubleshooting

NAS Not Found

· Use the 🔍 Find IP button in settings.
· Verify the NAS is powered on and connected to the network.

WOL Not Working

· Check the MAC address in settings.
· Ensure the NAS supports WOL and it is enabled.
· Try different WOL methods (the app tries Python‑based, wakeonlan, and etherwake).

Volume Mount Fails

· Confirm the NAS is online and SMB service is running.
· Increase the Mount Retries value in settings.
· Verify volume names are correct (case‑sensitive).

SSH Connection / Shutdown Issues

· If the app asks for a password or fails, run ssh-add ~/.ssh/id_rsa once (or use the 🔑 Erstellen button to create a dedicated key).
· Make sure your SSH key is copied to the NAS (ssh‑copy‑id).
· For sudo shutdown, ensure the user has NOPASSWD for /sbin/shutdown, /sbin/poweroff, and /usr/syno/bin/synopoweroff in /etc/sudoers.

---

🏗️ Architecture

```
SyNasPy/
├── SyNasPy.py             # Main application
├── requirements.txt       # Dependencies
├── README.md              # This file
├── LICENSE                # MIT License
├── BinhDiez.png           # Application logo
├── SyNasPy.png            # Application icon
└── .gitignore
```

Key Components

· LanguageManager – Multi‑language support (11 languages).
· ServerProfile / ServerProfileManager – Profile data and persistence.
· Config – Central configuration (merges global and profile settings).
· SyNasPy – Main window and core logic.
· ConfigDialog – Settings interface (with profile management).
· InfoDialog – About window with version, licenses, and update checker.
· AppLogger – Logging with buffering and rotation.

---

🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch (git checkout -b feature/YourFeature).
3. Make your changes and commit.
4. Push to your fork and open a pull request.

Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/SyNasPy.git
cd SyNasPy

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

📄 License

This project is licensed under the MIT License.
Copyright (c) 2026 BinhDiez64.

PyQt5 Notice: This application uses PyQt5, which is licensed under the GNU General Public License v3 (GPLv3).
Copyright (c) Riverbank Computing Limited.
Full license text: https://www.gnu.org/licenses/gpl-3.0.html

---

🙏 Acknowledgments

· Synology – For their excellent NAS hardware and DSM.
· PyQt Team – For the amazing Qt bindings.
· macOS Community – For helpful system integration tips.

---

📞 Support

· Issues: GitHub Issues
· Discussions: GitHub Discussions

---

🔄 Changelog

Version 2.0.0 (Current)

· Multi‑Server Profiles: Manage any number of NAS devices.
· 17 Languages: Full UI translation.
· Profile Management: Create, duplicate, rename, delete, activate.
· SSH Key Assistant: Open folder, create new key (does not overwrite id_rsa) with optional passphrase.
· Configurable Shutdown Delay: Adjustable delay between NAS‑ and Mac‑shutdown (0‑30 s).
· Update Checker: Integrated manual and background update notifications.
· Improved Shutdown Logic: More reliable NAS shutdown with fallback methods.
· Removed Obsolete Status File: The boQuitNASapp.txt workaround is no longer used.
· Enhanced Progress Bar: Shows percentage outside the bar.

Version 1.0.0 (Legacy)

· Single NAS management.
· Basic WOL, shutdown, volume mounting.
· Initial settings dialog.

---

Made with ❤️ for the NAS community.
