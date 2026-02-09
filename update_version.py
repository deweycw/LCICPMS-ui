#!/usr/bin/env python3
"""
Version update script for LCICPMS-ui

Usage:
    python update_version.py 1.0.8
    python update_version.py --show   # Show current version
"""

import re
import sys
import os

# Files that contain version strings and their patterns
VERSION_FILES = [
    {
        'path': 'uiGenerator/__init__.py',
        'pattern': r"__version__ = '[^']+'",
        'replacement': "__version__ = '{version}'",
    },
    {
        'path': 'uiGenerator/utils/update_checker.py',
        'pattern': r'CURRENT_VERSION = "[^"]+"',
        'replacement': 'CURRENT_VERSION = "{version}"  # This should match setup.py version',
    },
    {
        'path': 'setup.py',
        'pattern': r"version='[^']+'",
        'replacement': "version='{version}'",
    },
]


def get_script_dir():
    """Get the directory containing this script."""
    return os.path.dirname(os.path.abspath(__file__))


def get_current_version():
    """Read the current version from __init__.py."""
    script_dir = get_script_dir()
    init_path = os.path.join(script_dir, 'uiGenerator/__init__.py')

    with open(init_path, 'r') as f:
        content = f.read()

    match = re.search(r"__version__ = '([^']+)'", content)
    if match:
        return match.group(1)
    return None


def update_version(new_version):
    """Update version in all files."""
    script_dir = get_script_dir()
    updated_files = []

    for file_info in VERSION_FILES:
        file_path = os.path.join(script_dir, file_info['path'])

        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check if pattern exists
        if not re.search(file_info['pattern'], content):
            print(f"Warning: Pattern not found in {file_info['path']}")
            continue

        # Replace version
        new_content = re.sub(
            file_info['pattern'],
            file_info['replacement'].format(version=new_version),
            content
        )

        with open(file_path, 'w') as f:
            f.write(new_content)

        updated_files.append(file_info['path'])
        print(f"Updated: {file_info['path']}")

    return updated_files


def validate_version(version):
    """Validate version string format (e.g., 1.0.7)."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_version.py <new_version>")
        print("       python update_version.py --show")
        print("\nExample: python update_version.py 1.0.8")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--show':
        current = get_current_version()
        if current:
            print(f"Current version: {current}")
        else:
            print("Could not determine current version")
        sys.exit(0)

    new_version = arg

    if not validate_version(new_version):
        print(f"Error: Invalid version format '{new_version}'")
        print("Version must be in format: X.Y.Z (e.g., 1.0.7)")
        sys.exit(1)

    current = get_current_version()
    print(f"Current version: {current}")
    print(f"New version: {new_version}")
    print()

    updated = update_version(new_version)

    if updated:
        print(f"\nSuccessfully updated {len(updated)} file(s) to version {new_version}")
    else:
        print("\nNo files were updated")
        sys.exit(1)


if __name__ == '__main__':
    main()
