#!/bin/bash
# Quick script to push project to GitHub
# Run this after creating your GitHub repository

echo "🚀 Setting up Git and pushing to GitHub..."
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files (respecting .gitignore)
echo "Adding files to git..."
git add .

# Check what will be committed
echo ""
echo "Files to be committed:"
git status --short | head -20

echo ""
read -p "Continue with commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create initial commit
echo ""
echo "Creating initial commit..."
git commit -m "Initial commit: Visitor Management System

- Complete VMS with Register_App, Admin, and Webcam components
- Face recognition with dlib
- AI chatbot with Gemini
- Sentiment analysis
- Cleaned up ~4,900 lines of commented code"

# Instructions for adding remote
echo ""
echo "✅ Commit created successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Create a repository on GitHub.com"
echo "2. Run these commands (replace with your GitHub URL):"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "   Or use the GitHub CLI:"
echo "   gh repo create YOUR_REPO_NAME --public --source=. --remote=origin --push"
echo ""

