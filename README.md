# SyNasPy

**A modern macOS application for managing Synology NAS servers.**

Wake up your NAS, shut it down safely, mount SMB volumes, manage multiple servers, and automate common tasks — all from a clean and intuitive macOS interface.

---

## 📸 Screenshots

| Main Window | Settings |
|-------------|----------|
| <img width="420" alt="Server Offline" src="https://github.com/user-attachments/assets/2598c7c9-7256-4ea4-94f7-800d95f60989"> | <img width="420" alt="Settings" src="https://github.com/user-attachments/assets/514809e4-b9a4-48c7-bb67-4d7039fc147c"> |

---

# ✨ Features

## 🚀 NAS Management

- Wake-on-LAN (WOL) support
- Safe NAS shutdown
- Optional Mac shutdown after NAS shutdown
- Automatic startup and shutdown timers
- Configurable countdown delays
- Pause and resume active timers

---

## 💾 Volume Management

- Mount SMB network volumes
- Unmount selected volumes
- Individual volume selection
- Automatic volume handling after NAS startup

---

## 🖥️ Multi-Server Support

- Unlimited server profiles
- Fast profile switching
- Create new profiles
- Duplicate existing profiles
- Rename profiles
- Delete profiles
- Set default profile

---

## 🔐 Security

- SSH key authentication
- No passwords stored
- Secure SSH communication
- Optional SSH key generation assistant
- Open the local `.ssh` directory directly from the application

---

## 🌐 Network Features

- Automatic IP detection
- Bonjour / mDNS discovery
- DNS lookup
- ARP lookup
- Network scanning fallback
- Manual IP configuration

---

## 🌍 Languages

SyNasPy currently supports **17 languages**.

- العربية
## 🌍 Languages

| | |
|---|---|
| Arabic | Greek |
| Czech | Italian |
| Dutch | Norwegian |
| English | Polish |
| Finnish | Portuguese |
| French | Russian |
| German | Spanish |
| Swedish | Turkish |
| Vietnamese | |

---

## 🎨 User Experience

- Native macOS interface
- Modern dark appearance
- Voice feedback (macOS)
- Progress indicator with percentage
- Keyboard shortcuts
- Automatic update checker
- Background update notifications
- Responsive user interface

---

# ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ⌘ E | Open Settings |
| Enter | Confirm |
| Esc | Cancel |

---

# ⚙️ Requirements

- macOS
- Synology NAS
- SSH enabled on the NAS
- SMB file sharing enabled (for volume management)
- Wake-on-LAN enabled (recommended)

---

# 🔒 Privacy & Security

SyNasPy communicates directly with your Synology NAS.

The application:

- never stores your passwords
- uses SSH key authentication
- keeps private SSH keys on your Mac
- does not require cloud services
- performs all communication locally between your Mac and NAS

---

# 🚀 Typical Workflow

1. Launch SyNasPy.
2. Select your NAS profile.
3. Wake your NAS using Wake-on-LAN.
4. Wait until the NAS becomes available.
5. Automatically mount selected SMB volumes.
6. Work as usual.
7. Shut down the NAS safely when finished.
8. Optionally shut down your Mac afterwards.

---

# ⭐ Highlights

- Designed specifically for Synology NAS
- Native macOS experience
- Multiple NAS profiles
- Intelligent network detection
- SSH key authentication
- Automatic volume management
- Timer automation
- 17 interface languages
- No subscription
- No telemetry
- No cloud dependency

---

# 📦 Installation

1. Download the latest release.
2. Move **SyNasPy.app** to the **Applications** folder.
3. Launch the application.
4. Configure your NAS profile.
5. Enjoy.

---

# 🛠️ Built With

- Swift
- SwiftUI
- Apple Network Framework
- SSH
- Bonjour / mDNS
- SMB

---

# 🤝 Contributing

Contributions, bug reports, feature requests, and pull requests are welcome.

If you find a bug or have an idea for improving SyNasPy, please open an issue.

---

# 📄 License

This project is licensed under the MIT License.

---

**SyNasPy makes managing your Synology NAS on macOS simple, secure, and efficient.**

###########################

SyNasPy is a powerful macOS GUI application for managing Synology NAS servers with Wake‑on‑LAN, shutdown, volume management, and full multi‑server support.

<img width="522" height="653" alt="server_offline" src="https://github.com/user-attachments/assets/2598c7c9-7256-4ea4-94f7-800d95f60989" />
<img width="696" height="789" alt="settings_tab_1" src="https://github.com/user-attachments/assets/514809e4-b9a4-48c7-bb67-4d7039fc147c" />
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
