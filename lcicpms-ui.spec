# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LCICPMS-ui
Builds standalone executable for Windows, macOS, and Linux
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules
hiddenimports = [
    'uiGenerator',
    'uiGenerator.ui',
    'uiGenerator.controllers',
    'uiGenerator.models',
    'uiGenerator.plotting',
    'uiGenerator.utils',
    'lcicpms',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pyqtgraph',
    'numpy',
    'pandas',
    'matplotlib',
    'seaborn',
    'sklearn',
    'scipy',
]

# Collect all submodules from key packages
hiddenimports += collect_submodules('pyqtgraph')
hiddenimports += collect_submodules('sklearn')

# Collect data files
datas = []
datas += collect_data_files('pyqtgraph')

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LCICPMS-ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LCICPMS-ui',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LCICPMS-ui.app',
        icon=None,
        bundle_identifier='com.deweycw.lcicpms-ui',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
    )
