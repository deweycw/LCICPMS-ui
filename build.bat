@echo off
REM Build script for LCICPMS-ui on Windows
REM Creates standalone executable using PyInstaller

echo ===============================================
echo Building LCICPMS-ui
echo ===============================================

REM Check if pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the executable
echo Building executable...
pyinstaller lcicpms-ui.spec

REM Check if build was successful
if exist "dist\LCICPMS-ui.exe" (
    echo.
    echo ===============================================
    echo Build successful!
    echo Executable location: dist\LCICPMS-ui.exe
    echo ===============================================

    REM Optional: Create distribution archive
    set /p CREATE_ZIP="Create distribution ZIP? (y/n): "
    if /i "%CREATE_ZIP%"=="y" (
        REM Get version from setup.py
        for /f "tokens=2 delims='" %%a in ('findstr /r "version=" setup.py') do set VERSION=%%a

        echo Creating ZIP archive...
        cd dist
        powershell Compress-Archive -Path LCICPMS-ui.exe -DestinationPath ..\LCICPMS-ui-v%VERSION%-windows.zip -Force
        cd ..
        echo Created: LCICPMS-ui-v%VERSION%-windows.zip
    )
) else (
    echo.
    echo ===============================================
    echo Build failed!
    echo ===============================================
    exit /b 1
)

pause
