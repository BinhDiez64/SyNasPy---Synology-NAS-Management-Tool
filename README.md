# SyNasPy -- Synology-NAS-Management-Tool

A powerful macOS GUI application for managing Synology NAS servers with Wake-on-LAN, shutdown, and volume management capabilities.

<img width="514" height="562" alt="server_offline" src="https://github.com/user-attachments/assets/1e5c0d36-5e32-49d1-9e5b-a6b62f7e4e12" /><img width="514" height="565" alt="server_online" src="https://github.com/user-attachments/assets/353732b1-2485-42a6-87eb-a75c067a6215" />


✨ Features

🚀 Core Functionality

· Wake-on-LAN (WOL): Start your NAS remotely with a single click
· Smart Shutdown: Gracefully shut down NAS and/or Mac with configurable delays
· Auto-Start/Shutdown: Automatic actions with configurable timeouts
· Volume Management: Mount/unmount network volumes with ease
· SSH Integration: Secure NAS communication using SSH keys

🎯 Advanced Features

· Volume Selection: Choose specific volumes to mount/unmount
· Smart Auto-Detection: Automatically finds NAS IP and MAC addresses
· Multi-Protocol Support: Uses mDNS/Bonjour, DNS, ARP, and network scanning
· Configurable Timeouts: Customize all waiting periods and retry counts
· Status File System: Creates status files for workflow automation
· Logging System: Comprehensive logging with rotation (max 5 files)

🎨 User Interface

· Modern Dark Theme: Easy on the eyes with a professional look
· Keyboard Shortcuts: Cmd+E for settings, ESC to cancel
· Voice Feedback: Audio confirmation of actions (macOS only)
· Progress Indication: Visual feedback for all operations
· Quick Actions: One-click operations for common tasks

📋 Requirements

· Operating System: macOS 10.15 (Catalina) or later
· Python: 3.9 or higher
· Dependencies: PyQt5, Python standard libraries
· NAS: Synology NAS with:
  · SSH access enabled
  · SMB file sharing
  · Wake-on-LAN capability

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

Build as macOS App

```bash
# Install PyInstaller
pip install pyinstaller

# Build the app
pyinstaller --windowed --name "SyNasPy" --icon SyNasPy.icns SyNasPy.py

# The app will be in the dist/ folder
```

Requirements.txt

```txt
PyQt5>=5.15.0
pyinstaller>=5.0.0  # Optional, for building
```

🚀 Quick Start

1. First Launch: The app will create default configuration
2. Configure NAS: Click the gear icon (⚙) or press Cmd+E
3. Enter NAS Details:
   · Username, DNS/IP, MAC address
   · SSH key path (default: ~/.ssh/id_rsa)
   · Volume list (one per line)
4. Save Settings: Click "Save" to store configuration
5. Main Window:
   · "Mac & NAS": Shut down both
   · "NAS": Shut down only the NAS
   · "Start NAS": Wake the NAS
   · "Cancel": Close the app

⚙️ Configuration

Settings Dialog

Section Settings Description
NAS Server Username SSH/SMB username for NAS
 DNS Name Bonjour/DNS name (e.g., NAS-Synology.local)
 IP Address Static IP of your NAS
 MAC Address Network hardware address
 SSH Key Path Path to private SSH key
Volumes Volume List List of network volumes to manage
Timing Auto-Shutdown Delay Time before automatic shutdown (10-600s)
 Auto-Start Delay Time before automatic start (10-600s)
 WOL Wait Time Maximum WOL wait time (30-600s)
 SMB Wait Time Wait time for SMB service (5-120s)
 Mount Retries Number of mount attempts (1-10)
Status Status File Path Path to status file for workflow automation

Configuration Files

· JSON: ~/Library/Application Support/SyNasPy/synaspy_config.json
· QSettings: Platform-specific settings (overrides JSON)

Log Files

Logs are stored in ~/Library/Application Support/SyNasPy/Logs/ with automatic rotation (max 5 files).

⌨️ Keyboard Shortcuts

Shortcut Action
Cmd+E Open Settings Dialog
ESC Cancel operation / Close app
Enter Trigger focused button
Tab Navigate through controls

🔒 Security

· SSH key authentication only (no password storage)
· Keys stored in user's home directory
· No sensitive data transmitted over network
· All operations use macOS system APIs

🐛 Troubleshooting

NAS Not Found

· Issue: NAS not detected
· Solution: Use the "Find IP" button in settings or enter IP manually
· Check: Verify NAS is powered on and network connected

WOL Not Working

· Issue: NAS doesn't wake up
· Solution:
  1. Verify MAC address in settings
  2. Check if NAS supports WOL
  3. Try different WOL methods (Python/etherwake)
  4. Check network interface settings

Volume Mount Fails

· Issue: Network volumes won't mount
· Solution:
  1. Verify NAS is online
  2. Check SMB service is running
  3. Increase mount retries in settings
  4. Verify volume names are correct

SSH Connection Issues

· Issue: Can't connect via SSH
· Solution:
  1. Generate SSH key: ssh-keygen -t rsa -b 4096
  2. Copy key to NAS: ssh-copy-id user@nas-ip
  3. Test connection: ssh -i ~/.ssh/id_rsa user@nas-ip

🏗️ Architecture

SyNasPy/
├── SyNasPy.py          # Main application
├── requirements.txt    # Dependencies
├── README.md          # This file
├── LICENSE            # MIT License
├── BinhDiez.png       # Application logo
├── SyNasPy.png        # Application icon
└── build/             # Build artifacts


Key Components

· AppLogger: Logging system with buffer and rotation
· Config: Central configuration management
· ConfigDialog: Settings interface
· SyNasPy: Main application window
· Utilities: SSH, WOL, volume management helpers

🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/SyNasPy.git
cd SyNasPy

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt

# Run tests (if available)
python -m unittest discover tests/
```

📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments

· Synology - For their excellent NAS hardware and DSM
· PyQt Team - For the amazing Qt bindings
· macOS Community - For the helpful system integration tips

📞 Support

· Issues: GitHub Issues
· Discussions: GitHub Discussions
· Wiki: Project Wiki

🔄 Changelog

Version 1.0.0 (Current)

· Initial release
· Core functionality (WOL, shutdown, volume management)
· Settings dialog with all configurations
· Logging system with rotation
· macOS native integration

Planned Features

· Multi-NAS support
· Notification center integration
---

SyNasPy - Making Synology NAS management on macOS simple and elegant.

Made with ❤️ for the NAS community
