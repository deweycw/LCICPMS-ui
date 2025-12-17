#!/bin/bash
# Build script for LCICPMS-ui
# Creates standalone executable using PyInstaller

set -e  # Exit on error

echo "==============================================="
echo "Building LCICPMS-ui"
echo "==============================================="

# Check if pyinstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the executable
echo "Building executable..."
pyinstaller lcicpms-ui.spec

# Check if build was successful
if [ -f "dist/LCICPMS-ui" ] || [ -d "dist/LCICPMS-ui.app" ]; then
    echo ""
    echo "==============================================="
    echo "Build successful!"
    echo "Executable location: dist/"
    echo "==============================================="
else
    echo ""
    echo "==============================================="
    echo "Build failed!"
    echo "==============================================="
    exit 1
fi

# Optional: Create distribution archive
read -p "Create distribution archive? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    VERSION=$(grep "version=" setup.py | cut -d"'" -f2)
    PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')

    cd dist
    if [ "$PLATFORM" == "darwin" ]; then
        # macOS: Create DMG (requires create-dmg)
        if command -v create-dmg &> /dev/null; then
            create-dmg \
                --volname "LCICPMS-ui" \
                --window-pos 200 120 \
                --window-size 600 400 \
                --icon-size 100 \
                --app-drop-link 425 120 \
                "../LCICPMS-ui-v${VERSION}-macos.dmg" \
                "LCICPMS-ui.app"
            echo "Created: LCICPMS-ui-v${VERSION}-macos.dmg"
        else
            echo "create-dmg not found. Install with: brew install create-dmg"
            tar -czf "../LCICPMS-ui-v${VERSION}-macos.tar.gz" "LCICPMS-ui.app"
            echo "Created: LCICPMS-ui-v${VERSION}-macos.tar.gz"
        fi
    else
        # Linux: Create tar.gz
        tar -czf "../LCICPMS-ui-v${VERSION}-linux.tar.gz" LCICPMS-ui
        echo "Created: LCICPMS-ui-v${VERSION}-linux.tar.gz"
    fi
    cd ..
fi
