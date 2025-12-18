# Building and Distributing LCICPMS-ui

This guide explains how to build standalone executables and distribute updates to users.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Building](#local-building)
3. [Creating a Release](#creating-a-release)
4. [Automated Builds with GitHub Actions](#automated-builds-with-github-actions)
5. [Update System](#update-system)
6. [PyUpdater Advanced Setup](#pyupdater-advanced-setup)

---

## Prerequisites

### Required Tools

- **Python 3.12+**
- **PyInstaller**: `pip install pyinstaller`
- **Git**: For version control and releases

### Platform-Specific Requirements

**Windows:**
- No additional requirements

**macOS:**
- Xcode Command Line Tools: `xcode-select --install`
- (Optional) create-dmg for DMG creation: `brew install create-dmg`

**Linux:**
- System dependencies:
  ```bash
  sudo apt-get install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
  ```

---

## Local Building

### Quick Build

Use the provided build scripts:

**Linux/macOS:**
```bash
./build.sh
```

**Windows:**
```cmd
build.bat
```

### Manual Build

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build executable
pyinstaller lcicpms-ui.spec

# Executable will be in dist/ folder
# - Linux: dist/LCICPMS-ui
# - macOS: dist/LCICPMS-ui.app
# - Windows: dist/LCICPMS-ui.exe
```

### Testing the Build

Run the executable directly:

```bash
# Linux/macOS
./dist/LCICPMS-ui

# Windows
dist\LCICPMS-ui.exe
```

---

## Creating a Release

### 1. Update Version Number

Update version in `setup.py`:

```python
setup(
    name='lcicpms-ui',
    version='0.3.0',  # <-- Update this
    ...
)
```

Also update in `uiGenerator/utils/update_checker.py`:

```python
CURRENT_VERSION = "0.3.0"  # <-- Update this
```

### 2. Commit Changes

```bash
git add .
git commit -m "Release v0.3.0"
git push
```

### 3. Create Git Tag

```bash
git tag v0.3.0
git push origin v0.3.0
```

### 4. GitHub Actions Automatic Build

Once you push a tag starting with `v`, GitHub Actions will automatically:

1. Build executables for Windows, macOS, and Linux
2. Create a GitHub Release
3. Upload all executables to the release

**Note:** The first time you push a tag, you may need to configure repository permissions:
- Go to Settings → Actions → General
- Under "Workflow permissions", select "Read and write permissions"

### 5. Manual Release (Alternative)

If you prefer manual releases:

```bash
# Build for your platform
./build.sh  # or build.bat

# Create GitHub release
gh release create v0.3.0 \
    --title "Release v0.3.0" \
    --notes "Release notes here" \
    dist/LCICPMS-ui-v0.3.0-*
```

---

## Automated Builds with GitHub Actions

The `.github/workflows/build-release.yml` workflow automatically builds executables when you push a version tag.

### Workflow Triggers

- **Push tag**: `git push origin v0.3.0`
- **Manual trigger**: From GitHub Actions tab

### Build Process

1. **Checkout code**
2. **Set up Python 3.12**
3. **Install dependencies**
4. **Build with PyInstaller**
5. **Create distribution archives**
6. **Upload to GitHub Releases**

### Customizing Builds

Edit `.github/workflows/build-release.yml` to:
- Change Python version
- Add/remove platforms
- Modify build steps
- Add code signing (recommended for production)

---

## Update System

### How It Works

1. **On Startup**: App checks GitHub Releases API for new versions
2. **Version Comparison**: Compares current version with latest release
3. **Update Dialog**: Shows release notes and download link if update available
4. **User Action**: User can download, skip version, or be reminded later

### Update Checker Configuration

Located in `uiGenerator/utils/update_checker.py`:

```python
GITHUB_REPO = "deweycw/LCICPMS-ui"  # Your GitHub repo
CURRENT_VERSION = "0.2.0"  # Current app version
```

### Update Check Flow

```
App Startup (500ms delay)
    ↓
Check GitHub API for latest release
    ↓
Version newer? → YES → Show Update Dialog
              ↓
             NO → Silent (no notification)
```

### Disabling Update Checks

Comment out in `uiGenerator/controllers/main_controller.py`:

```python
# QTimer.singleShot(500, self._check_for_updates)
```

---

## PyUpdater Advanced Setup

PyUpdater provides automatic download and installation of updates.

### Installation

```bash
pip install pyupdater[s3]  # For S3 hosting
# or
pip install pyupdater[all]  # All backends
```

### Initialize PyUpdater

```bash
pyupdater init

# Follow prompts:
# - App name: LCICPMS-ui
# - Company: LCICPMS
# - Update URLs: (configure based on hosting)
```

### Generate Signing Keys

```bash
pyupdater keys --create
# This generates public/private key pair for code signing
```

### Build with PyUpdater

```bash
pyupdater build --app-version 0.3.0 lcicpms-ui.spec
```

### Sign and Upload

```bash
# Process build
pyupdater pkg --process --sign

# Upload to server (e.g., S3)
pyupdater upload --service s3
```

### Client Integration

Add to your app (in main_controller.py):

```python
from pyupdater.client import Client, ClientConfig

def check_for_updates_pyupdater(self):
    client_config = ClientConfig()
    client_config.APP_NAME = 'LCICPMS-ui'
    client_config.COMPANY_NAME = 'LCICPMS'
    client_config.UPDATE_URLS = ['https://your-update-server.com/']
    client_config.PUBLIC_KEY = 'your-public-key-here'

    client = Client(client_config)
    app_update = client.update_check('LCICPMS-ui', '0.2.0')

    if app_update:
        app_update.download()
        if app_update.is_downloaded():
            app_update.extract_restart()
```

---

## Code Signing (Recommended for Production)

### Windows

Use SignTool:

```cmd
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\LCICPMS-ui.exe
```

### macOS

Use codesign:

```bash
codesign --deep --force --verify --verbose --sign "Developer ID" dist/LCICPMS-ui.app
```

Then notarize:

```bash
xcrun notarytool submit dist/LCICPMS-ui.app --wait
```

### Linux

Use gpg for signing:

```bash
gpg --detach-sign dist/LCICPMS-ui
```

---

## Troubleshooting

### Build fails with "Module not found"

Add missing module to `hiddenimports` in `lcicpms-ui.spec`:

```python
hiddenimports=[
    'PyQt6.QtCore',
    'your_missing_module',  # Add here
]
```

### Executable is too large

Exclude unnecessary packages in spec file:

```python
excludes=[
    'IPython',
    'notebook',
    'matplotlib.tests',
]
```

### Update checker doesn't work

- Check internet connection
- Verify `GITHUB_REPO` is correct
- Ensure releases exist on GitHub

### GitHub Actions fails

- Check repository permissions (Settings → Actions)
- Verify secrets are configured (if using code signing)
- Check workflow logs for specific errors

---

## Release Checklist

- [ ] Update version in `setup.py`
- [ ] Update version in `uiGenerator/utils/update_checker.py`
- [ ] Update CHANGELOG.md
- [ ] Test builds locally on all platforms
- [ ] Commit and push changes
- [ ] Create and push version tag
- [ ] Verify GitHub Actions build succeeds
- [ ] Test update mechanism
- [ ] Announce release to users

---

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyUpdater Documentation](https://www.pyupdater.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Code Signing Guide](https://github.com/electron/electron/blob/main/docs/tutorial/code-signing.md)
