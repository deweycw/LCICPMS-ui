# Distribution Quick Start Guide

This guide gets you started quickly with building and distributing LCICPMS-ui.

## For First-Time Setup

### 1. Install Build Dependencies

```bash
pip install pyinstaller requests packaging
```

### 2. Test Local Build

```bash
# Linux/macOS
./build.sh

# Windows
build.bat
```

This creates an executable in `dist/`.

### 3. Configure GitHub Repository

1. Go to your repository **Settings → Actions → General**
2. Under "Workflow permissions", select **"Read and write permissions"**
3. Click **Save**

## Creating Your First Release

### Method 1: Automatic (Recommended)

```bash
# 1. Update version numbers
# Edit setup.py line 17: version='0.3.0'
# Edit uiGenerator/utils/update_checker.py line 13: CURRENT_VERSION = "0.3.0"

# 2. Commit and tag
git add .
git commit -m "Release v0.3.0"
git tag v0.3.0
git push origin main
git push origin v0.3.0

# 3. GitHub Actions automatically builds and creates release!
# Check: https://github.com/YOUR_USERNAME/LCICPMS-ui/actions
```

### Method 2: Manual

```bash
# 1. Build locally
./build.sh  # Creates archive in current directory

# 2. Create release manually
gh release create v0.3.0 \
    --title "Version 0.3.0" \
    --notes "Release notes here" \
    LCICPMS-ui-v0.3.0-*.tar.gz
```

## How Users Get Updates

### Automatic Update Notification

When users start the app:

1. **Background check** (500ms after startup)
2. **If newer version exists**:
   - Dialog appears with release notes
   - Users click "Download Update"
   - Opens GitHub release page
3. **If already up-to-date**:
   - Silent (no notification)

### Update Checker Features

- **Non-intrusive**: Runs in background thread
- **Smart versioning**: Uses semantic version comparison
- **Platform-aware**: Shows correct download for Windows/macOS/Linux
- **Release notes**: Displays what's new
- **User control**: Skip version, remind later, or download

## File Structure

```
LCICPMS-ui/
├── lcicpms-ui.spec          # PyInstaller configuration
├── build.sh                  # Linux/macOS build script
├── build.bat                 # Windows build script
├── pyupdater-config.py       # PyUpdater configuration (advanced)
├── BUILDING.md               # Detailed build documentation
├── DISTRIBUTION.md           # This file
├── CHANGELOG.md              # Version history
│
├── .github/
│   └── workflows/
│       └── build-release.yml # GitHub Actions workflow
│
└── uiGenerator/
    └── utils/
        └── update_checker.py # Update checking logic
```

## Quick Reference

### Build Executable
```bash
./build.sh  # or build.bat
```

### Create Release
```bash
git tag v0.X.Y && git push origin v0.X.Y
```

### Check Build Status
Visit: `https://github.com/YOUR_USERNAME/LCICPMS-ui/actions`

### Test Update Check
```bash
# Temporarily change CURRENT_VERSION to older version
# in uiGenerator/utils/update_checker.py
# Run app → update dialog should appear
```

## Common Tasks

### Update Version Number

Edit **2 files**:

1. `setup.py`:
   ```python
   version='0.3.0',  # Line 17
   ```

2. `uiGenerator/utils/update_checker.py`:
   ```python
   CURRENT_VERSION = "0.3.0"  # Line 13
   ```

### Add Release Notes

Edit `CHANGELOG.md`, then use in release:

```bash
gh release create v0.3.0 --notes-file <(sed -n '/## \[0.3.0\]/,/## \[/p' CHANGELOG.md)
```

### Disable Update Checks

Comment out in `uiGenerator/controllers/main_controller.py`:

```python
# QTimer.singleShot(500, self._check_for_updates)
```

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Build failed"
Check console output for missing dependencies, then add to `lcicpms-ui.spec`:
```python
hiddenimports=['missing_module_name']
```

### "GitHub Actions not running"
- Check repository Settings → Actions permissions
- Verify `.github/workflows/build-release.yml` exists
- Check tag format (must start with 'v')

### "Update checker not working"
- Verify internet connection
- Check `GITHUB_REPO` value in `update_checker.py`
- Ensure releases exist on GitHub

## Next Steps

- Read full documentation: `BUILDING.md`
- Set up code signing for production
- Configure PyUpdater for auto-install (advanced)
- Customize GitHub Actions workflow

## Support

- **Issues**: https://github.com/deweycw/LCICPMS-ui/issues
- **Discussions**: https://github.com/deweycw/LCICPMS-ui/discussions
- **Documentation**: See `BUILDING.md`
