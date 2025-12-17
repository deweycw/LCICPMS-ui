# Quick Start - Building Your First Release

## ✅ Everything is Ready!

Your application now has:
- ✅ Standalone executable builds
- ✅ Automatic update checking
- ✅ GitHub Actions CI/CD
- ✅ Complete documentation

## 🚀 Create Your First Release (5 Minutes)

### Step 1: Update Version Numbers

Edit **2 files**:

**File 1:** `setup.py` (line 17)
```python
version='0.2.0',  # Change to your version
```

**File 2:** `uiGenerator/utils/update_checker.py` (line 14)
```python
CURRENT_VERSION = "0.2.0"  # Must match setup.py
```

### Step 2: Test Local Build

```bash
# Build the executable
source env/bin/activate
pyinstaller lcicpms-ui.spec

# Test it runs
./dist/LCICPMS-ui
```

**Success?** You should see your app open! ✅

### Step 3: Configure GitHub (One-Time)

1. Go to your repository on GitHub
2. Click **Settings** → **Actions** → **General**
3. Under "Workflow permissions", select **"Read and write permissions"**
4. Click **Save**

### Step 4: Create the Release

```bash
# Commit your changes
git add .
git commit -m "Release v0.2.0"

# Create and push tag
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

**That's it!** GitHub Actions will now:
1. Build executables for Windows, macOS, and Linux
2. Create a GitHub Release
3. Upload all executables

### Step 5: Check Build Status

Visit: `https://github.com/YOUR_USERNAME/LCICPMS-ui/actions`

Watch the build progress (takes ~10 minutes)

### Step 6: Share with Users!

Once the build completes, your release will be available at:
```
https://github.com/YOUR_USERNAME/LCICPMS-ui/releases/latest
```

Users can download and run without installing Python!

---

## 🎯 What Happens Next?

### For Users

When they start your app:
1. App checks for updates automatically (background)
2. If new version exists → Shows dialog with release notes
3. They can download, skip, or be reminded later

### For You (Next Release)

```bash
# 1. Update version in 2 files
# 2. Update CHANGELOG.md
# 3. Commit and tag
git tag v0.3.0
git push origin v0.3.0

# Done! GitHub Actions handles the rest
```

---

## 📋 Pre-Flight Checklist

Before creating your first release:

- [ ] Updated `GITHUB_REPO` in `update_checker.py` (line 13)
- [ ] Versions match in `setup.py` and `update_checker.py`
- [ ] Tested local build with `pyinstaller lcicpms-ui.spec`
- [ ] GitHub Actions permissions configured
- [ ] Updated `CHANGELOG.md` with release notes

---

## 🆘 Troubleshooting

### Build Fails Locally
```bash
# Clean and rebuild
rm -rf build dist
source env/bin/activate
pip install -r requirements.txt
pyinstaller lcicpms-ui.spec
```

### GitHub Actions Fails
- Check Settings → Actions → Permissions
- Verify tag format (must start with 'v')
- Review Actions logs for errors

### Update Checker Not Working
Edit `uiGenerator/utils/update_checker.py` line 13:
```python
GITHUB_REPO = "YOUR_USERNAME/LCICPMS-ui"  # Update this!
```

---

## 📚 Next Steps

Once your first release is working:

1. **Read the docs**:
   - `DISTRIBUTION.md` - Distribution guide
   - `BUILDING.md` - Detailed build instructions
   - `DEPLOYMENT_SUMMARY.md` - Complete overview

2. **Set up code signing** (production):
   - Windows: SignTool + certificate
   - macOS: Developer ID + notarization

3. **Add app icons**:
   - Create `assets/icon.ico` (Windows)
   - Create `assets/icon.icns` (macOS)

4. **Customize build**:
   - Edit `lcicpms-ui.spec`
   - Exclude unnecessary packages
   - Reduce executable size

---

## 🎉 Success Checklist

You'll know it's working when:

- [ ] Local build creates `dist/LCICPMS-ui`
- [ ] Executable runs without Python
- [ ] Pushing tag triggers GitHub Actions
- [ ] GitHub Actions creates release
- [ ] Executables are attached to release
- [ ] App shows update dialog when new version exists

---

## 💡 Pro Tips

**Use build script:**
```bash
./build.sh  # Automated build + archive creation
```

**Test update system:**
```bash
# Temporarily change CURRENT_VERSION to "0.1.0"
# Run app → update dialog should appear
```

**Skip update check during development:**
Comment out in `main_controller.py`:
```python
# QTimer.singleShot(500, self._check_for_updates)
```

---

## 📞 Get Help

- **Full docs**: See `BUILDING.md` and `DISTRIBUTION.md`
- **Issues**: https://github.com/deweycw/LCICPMS-ui/issues
- **GitHub Actions logs**: Check for build errors

---

**You're ready to go!** 🚀

Build your first release and let users download your app without Python!
