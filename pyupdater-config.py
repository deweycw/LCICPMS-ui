"""
PyUpdater Configuration

This file configures PyUpdater for automatic app updates.
Run `pyupdater init` to initialize, then use this configuration.
"""

# Application name
APP_NAME = 'LCICPMS-ui'

# Company/Author name
COMPANY_NAME = 'LCICPMS'

# Update URLs - Configure based on your hosting
# Options: S3, GitHub Releases, or custom server
UPDATE_URLS = [
    'https://github.com/deweycw/LCICPMS-ui/releases/download/latest/',
]

# Public key for code signing (generated during pyupdater init)
# This will be populated after running: pyupdater keys --create
PUBLIC_KEY = ''

# Maximum download retries
MAX_DOWNLOAD_RETRIES = 3

# Example client configuration for the app
CLIENT_CONFIG = {
    'APP_NAME': APP_NAME,
    'COMPANY_NAME': COMPANY_NAME,
    'UPDATE_URLS': UPDATE_URLS,
    'PUBLIC_KEY': PUBLIC_KEY,
}
