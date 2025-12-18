"""
Update checker for LCICPMS-ui
Checks GitHub Releases for new versions
"""

import requests
from packaging import version as pkg_version
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import webbrowser

# Configuration
GITHUB_REPO = "deweycw/LCICPMS-ui"  # Update with your GitHub username
CURRENT_VERSION = "1.0.1"  # This should match setup.py version


class UpdateCheckThread(QThread):
    """Background thread for checking updates without blocking UI"""
    update_found = pyqtSignal(dict)
    check_complete = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTerminationEnabled(True)

    def run(self):
        """Check for updates in background"""
        try:
            update_info = check_for_updates()
            if update_info['update_available']:
                self.update_found.emit(update_info)
            self.check_complete.emit(True)
        except Exception as e:
            print(f"Error checking for updates: {e}")
            self.check_complete.emit(False)


def check_for_updates():
    """
    Check GitHub Releases API for new versions

    Returns:
        dict: Update information with keys:
            - update_available (bool): Whether an update is available
            - version (str): Latest version number
            - url (str): Download URL
            - release_url (str): GitHub release page URL
            - notes (str): Release notes
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        headers = {'Accept': 'application/vnd.github.v3+json'}

        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        latest_release = response.json()
        latest_version = latest_release['tag_name'].lstrip('v')

        # Compare versions
        if pkg_version.parse(latest_version) > pkg_version.parse(CURRENT_VERSION):
            # Find appropriate asset for current platform
            import sys
            platform_suffix = {
                'win32': 'windows.exe',
                'darwin': 'macos.dmg',
                'linux': 'linux.tar.gz',
            }.get(sys.platform, 'linux.tar.gz')

            download_url = latest_release['html_url']  # Default to release page
            for asset in latest_release.get('assets', []):
                if platform_suffix in asset['name'].lower():
                    download_url = asset['browser_download_url']
                    break

            return {
                'update_available': True,
                'version': latest_version,
                'current_version': CURRENT_VERSION,
                'url': download_url,
                'release_url': latest_release['html_url'],
                'notes': latest_release.get('body', 'No release notes available.'),
                'published_at': latest_release.get('published_at', ''),
            }

        return {
            'update_available': False,
            'current_version': CURRENT_VERSION,
        }

    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")
        return {
            'update_available': False,
            'error': str(e),
        }
    except Exception as e:
        print(f"Unexpected error checking for updates: {e}")
        return {
            'update_available': False,
            'error': str(e),
        }


class UpdateDialog(QDialog):
    """Custom dialog for displaying update information"""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._create_ui()

    def _create_ui(self):
        """Create the update dialog UI"""
        layout = QVBoxLayout()

        # Title
        title = QLabel(f"<h2>New Version Available: {self.update_info['version']}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Current version info
        current_info = QLabel(f"Current Version: {self.update_info['current_version']}")
        current_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(current_info)

        # Release notes
        notes_label = QLabel("<b>Release Notes:</b>")
        layout.addWidget(notes_label)

        notes_text = QTextEdit()
        notes_text.setReadOnly(True)
        notes_text.setPlainText(self.update_info['notes'])
        notes_text.setMaximumHeight(200)
        layout.addWidget(notes_text)

        # Buttons
        button_layout = QHBoxLayout()

        download_btn = QPushButton("Download Update")
        download_btn.clicked.connect(self._download_update)
        download_btn.setDefault(True)
        button_layout.addWidget(download_btn)

        later_btn = QPushButton("Remind Me Later")
        later_btn.clicked.connect(self.reject)
        button_layout.addWidget(later_btn)

        skip_btn = QPushButton("Skip This Version")
        skip_btn.clicked.connect(self._skip_version)
        button_layout.addWidget(skip_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _download_update(self):
        """Open download URL in browser"""
        webbrowser.open(self.update_info['release_url'])
        self.accept()

    def _skip_version(self):
        """Mark this version as skipped (could save to settings)"""
        # TODO: Save skipped version to config file
        self.reject()


def show_update_dialog(update_info, parent=None):
    """
    Show update dialog if update is available

    Args:
        update_info (dict): Update information from check_for_updates()
        parent (QWidget): Parent widget for dialog

    Returns:
        bool: True if user chose to download, False otherwise
    """
    if not update_info.get('update_available'):
        return False

    dialog = UpdateDialog(update_info, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def check_updates_on_startup(parent=None, silent=False):
    """
    Check for updates on application startup

    Args:
        parent (QWidget): Parent widget for dialog
        silent (bool): If True, only show dialog if update is available

    Returns:
        UpdateCheckThread: The update check thread (can be used to connect signals)
    """
    thread = UpdateCheckThread(parent)

    def on_update_found(update_info):
        show_update_dialog(update_info, parent)

    def on_check_complete(success):
        if not silent and success:
            # Could show "You're up to date" message
            pass
        # Clean up thread after completion
        thread.deleteLater()

    thread.update_found.connect(on_update_found)
    thread.check_complete.connect(on_check_complete)
    thread.finished.connect(thread.deleteLater)  # Ensure cleanup
    thread.start()

    return thread
