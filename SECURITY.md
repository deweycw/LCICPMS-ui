# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the maintainer directly rather than opening a public issue.

**Please include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work to release a patch as quickly as possible.

## Security Best Practices

### For Users

**Running from Source (Recommended)**

The safest way to use this application is to run it from source:

```bash
git clone https://github.com/deweycw/LCICPMS-ui.git
cd LCICPMS-ui
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python run_lcicpms.py
```

Benefits:
- Full transparency - you can inspect all code
- No executable warnings from antivirus/SmartScreen
- Easy to verify checksums of dependencies
- Simple to keep updated with `git pull`

**If Using Pre-built Executables**

When pre-built executables become available:

1. **Only download from official sources**:
   - GitHub Releases: https://github.com/deweycw/LCICPMS-ui/releases
   - Do not download from third-party sites

2. **Verify checksums**:
   ```bash
   # Download the checksums file from the release
   # On Linux/macOS:
   sha256sum -c checksums.txt

   # On Windows (PowerShell):
   Get-FileHash LCICPMS-ui.exe -Algorithm SHA256
   # Compare with value in checksums.txt
   ```

3. **Understand SmartScreen warnings**:
   - Windows SmartScreen may warn about "unknown publisher"
   - This is normal for applications without code-signing certificates
   - Code-signing certificates cost $200-500/year
   - If concerned, run from source instead

4. **Antivirus false positives**:
   - PyInstaller executables sometimes trigger false positives
   - This is common with Python-packaged applications
   - Verify checksums and scan with VirusTotal
   - When in doubt, run from source

### For Developers

**Contributing Securely**

1. **Never commit sensitive data**:
   - No API keys, passwords, or tokens
   - No real experimental data with PII
   - Use `.gitignore` for local configuration

2. **Dependencies**:
   - Only use well-maintained, trusted packages
   - Pin versions in `requirements.txt`
   - Regularly update dependencies for security patches

3. **Code review**:
   - All changes go through pull request review
   - Check for security issues before merging

**Building Executables**

When building executables:

1. Build in a clean environment
2. Use virtual environments
3. Document all build steps
4. Provide checksums for all binaries
5. Sign binaries when possible (code signing certificate)

## Known Security Considerations

### Application Permissions

This application requires:
- **File system access**: To read CSV data files and write results
- **Network access**: Optional, for update checks only (can be disabled)

The application does NOT:
- Send your data to external servers
- Make network requests except for update checks
- Access system files outside selected directories
- Require administrative privileges

### Data Privacy

- All data processing is performed locally on your machine
- No telemetry or usage data is collected
- No data is transmitted over the network
- CSV files are only accessed when explicitly selected by the user

### Third-Party Dependencies

This application depends on several third-party packages:
- PyQt6: Official Qt bindings for Python
- PyQtGraph: Scientific plotting library
- Pandas: Data manipulation library
- Matplotlib: Plotting library
- NumPy: Numerical computing library
- Seaborn: Statistical visualization

All dependencies are open-source and widely used in the scientific Python community.

## Security Checklist for Users

Before running this application:

- [ ] Downloaded from official GitHub releases page
- [ ] Verified SHA256 checksum (if using executable)
- [ ] Reviewed source code (if security-critical use case)
- [ ] Running in isolated/virtual environment
- [ ] Comfortable with required file system permissions
- [ ] Updated to latest version

## Updates and Patches

**Automatic Updates** (if enabled in settings):
- Application checks for updates on startup
- You control when to install updates
- Updates are downloaded from GitHub releases only

**Manual Updates**:
```bash
# For source installations
cd LCICPMS-ui
git pull
pip install -r requirements.txt --upgrade
```

## Contact

For security concerns or questions:
- Email: [Your contact email]
- GitHub Issues: https://github.com/deweycw/LCICPMS-ui/issues (for non-sensitive issues)

## Transparency

This project is:
- **Open source**: All code is publicly visible
- **Actively maintained**: Regular updates and security patches
- **Community-driven**: Contributions welcome
- **Documented**: Comprehensive build and usage instructions

We believe in transparency and user control over their computing environment.
