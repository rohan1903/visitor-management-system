# GitHub Setup Guide

Follow these steps to push your project to GitHub and access it on your Windows laptop.

## Step 1: Create a GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in (or create an account)
2. Click the **"+"** icon in the top right → **"New repository"**
3. Name your repository (e.g., `visitor-management-system` or `major-project`)
4. **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **"Create repository"**
6. **Copy the repository URL** (e.g., `https://github.com/yourusername/visitor-management-system.git`)

## Step 2: Initialize Git and Push to GitHub

### On Linux (Current Machine):

```bash
# Navigate to project directory
cd /home/rohan/major-project

# Initialize git repository
git init

# Add all files (respecting .gitignore)
git add .

# Create initial commit
git commit -m "Initial commit: Visitor Management System"

# Add your GitHub repository as remote (replace with your actual URL)
git remote add origin https://github.com/yourusername/your-repo-name.git

# Rename default branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Note:** You'll be prompted for your GitHub username and password. For password, use a **Personal Access Token** (not your GitHub password):
- Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate new token with `repo` permissions
- Use this token as your password

## Step 3: Clone on Windows Laptop

### Option A: Using GitHub Desktop (Easiest)

1. Download [GitHub Desktop](https://desktop.github.com/)
2. Install and sign in with your GitHub account
3. Click **"Clone a repository from the Internet"**
4. Select your repository
5. Choose a local path (e.g., `C:\Users\YourName\Documents\major-project`)
6. Click **"Clone"**

### Option B: Using Command Line

```cmd
# Open Command Prompt or PowerShell
# Navigate to where you want the project
cd C:\Users\YourName\Documents

# Clone the repository
git clone https://github.com/yourusername/your-repo-name.git

# Navigate into the project
cd your-repo-name
```

## Step 4: Setup on Windows

After cloning, you need to:

1. **Create `.env` files** in each component directory:
   - Copy `.env.example` to `Register_App/.env`
   - Copy `.env.example` to `Admin/.env`
   - Copy `.env.example` to `Webcam/.env`
   - Fill in your actual values

2. **Add Firebase credentials**:
   - Copy `firebase_credentials.json` to each component directory
   - **OR** download from Firebase Console and place in each directory

3. **Install dependencies** (see README.md for detailed instructions)

## Important Notes

### Files NOT in Git (Protected by .gitignore):
- ✅ `.env` files (environment variables)
- ✅ `firebase_credentials.json` (Firebase keys)
- ✅ `venv/` (virtual environments)
- ✅ `__pycache__/` (Python cache)
- ✅ `uploads/` (test images)

### Files IN Git:
- ✅ All source code (`.py` files)
- ✅ Templates (`.html` files)
- ✅ Requirements files
- ✅ Model files (`.pkl`, `.dat`, `.onnx`)
- ✅ README.md and documentation

### Security Reminder:
- **NEVER** commit `.env` files or `firebase_credentials.json` to Git
- If you accidentally commit them, remove them immediately:
  ```bash
  git rm --cached path/to/file
  git commit -m "Remove sensitive file"
  git push
  ```

## Updating the Repository

### On Linux (after making changes):
```bash
git add .
git commit -m "Description of changes"
git push
```

### On Windows (after making changes):
```cmd
git add .
git commit -m "Description of changes"
git push
```

### Pulling Latest Changes:
```cmd
# On Windows (to get changes from Linux)
git pull
```

## Troubleshooting

### If you get "repository not found" error:
- Check the repository URL is correct
- Verify you have access to the repository
- Make sure you're using a Personal Access Token (not password)

### If you get "permission denied" error:
- Generate a new Personal Access Token with `repo` scope
- Use the token instead of your password

### If files are too large:
- GitHub has a 100MB file size limit
- Large model files might need Git LFS (Large File Storage)
- Or exclude them from git and download separately

## Alternative: Using GitHub CLI

If you prefer command line:
```bash
# Install GitHub CLI first, then:
gh repo create visitor-management-system --public --source=. --remote=origin --push
```

---

**Next Steps:** After cloning on Windows, follow the setup instructions in `README.md`

