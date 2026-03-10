# Git Commands for v0.2.0 Release

## Quick Reference

### 1. Check Current Status
```powershell
# See what files have changed
git status

# See what branches you're on
git branch
```

### 2. Commit All Changes
```powershell
# Stage all modified and new files
git add .

# Commit with descriptive message
git commit -m "Release v1.0.0 - Manual CallerID assignment feature

- Added drag-and-drop assignment interface
- Added QA role CallerID submission
- Added reserved queue system
- Fixed auto-refresh issues
- Updated database schema with manual assignment fields"
```

### 3. Create Git Tag
```powershell
# Create annotated tag (recommended)
git tag -a v0.2.0 -m "Release v0.2.0: Manual CallerID Assignment (PoC Enhancement)

Major Features:
- Drag-and-drop CallerID assignment
- Reserved queue system (up to 3 per member)
- QA role enhancements
- Priority assignment logic

Breaking Changes:
- Database schema changes - migration required

See RELEASE-NOTES.md for details"

# Or create lightweight tag (simpler)
git tag v0.2.0
```

### 4. View Tags
```powershell
# List all tags
git tag

# Show specific tag details
git show v0.2.0
```

### 5. Push to Remote
```powershell
# Push commits to main branch
git push origin main

# Push tags to remote
git push origin v0.2.0

# Or push all tags at once
git push origin --tags

# Combine: push commits and tags together
git push origin main --tags
```

### 6. If Using GitHub/Azure DevOps

After pushing the tag, create a release:

**GitHub:**
```powershell
# Using GitHub CLI (if installed)
gh release create v0.2.0 `
  --title "v0.2.0 - Manual Assignment Feature (PoC)" `
  --notes-file RELEASE-NOTES.md

# Or via web interface:
# 1. Go to repository on GitHub
# 2. Click "Releases" tab
# 3. Click "Draft a new release"
# 4. Select tag: v0.2.0
# 5. Add title and description from RELEASE-NOTES.md
# 6. Publish release
```

**Azure DevOps:**
```powershell
# Via web interface:
# 1. Go to Repos → Tags
# 2. Verify v0.2.0 tag exists
# 3. Go to Pipelines → Releases
# 4. Create new release
# 5. Link artifacts and add release notes
```

## Complete Workflow

### First Time Setup (If Not Done)
```powershell
# Configure git user (one-time)
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"

# Initialize repository (if not already done)
git init
git remote add origin <repository-url>
```

### Standard Release Process
```powershell
# 1. Make sure you're on main/master branch
git checkout main

# 2. Pull latest changes
git pull origin main

# 3. Stage all changes
git add .

# 4. Check what will be committed
git status

# 5. Commit with detailed message
git commit -m "Release v0.2.0 - Manual assignment feature (PoC enhancement)

Includes:
- Drag-and-drop UI for admin
- Reserved queue for complaint team
- QA submission form
- Database schema updates
- Bug fixes for auto-refresh

Breaking changes: Database migration required"

# 6. Create version tag
git tag -a v0.2.0 -m "Release v0.2.0 - See RELEASE-NOTES.md"

# 7. Push everything
git push origin main --tags

# 8. Verify on remote
git ls-remote --tags origin
```

## Useful Commands

### View History
```powershell
# See recent commits
git log --oneline -10

# See commits with tags
git log --oneline --decorate

# See tag details
git show v0.2.0
```

### Undo/Fix Mistakes

```powershell
# Forgot to add files before commit?
git add forgotten-file.txt
git commit --amend --no-edit

# Wrong commit message?
git commit --amend -m "Corrected message"

# Delete a tag (local)
git tag -d v0.2.0

# Delete a tag (remote) - BE CAREFUL
git push origin --delete v0.2.0

# Undo last commit (keep changes)
git reset --soft HEAD~1
```

### Branch Management (If Using)
```powershell
# Create release branch
git checkout -b release/1.0.0

# Switch back to main
git checkout main

# Merge release branch
git merge --no-ff release/1.0.0

# Delete branch after merge
git branch -d release/1.0.0
```

## Common Scenarios

### Scenario 1: Simple Release (No Branches)
```powershell
git add .
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags
```

### Scenario 2: Release from Feature Branch
```powershell
# On feature branch
git checkout feature/manual-assignment
git add .
git commit -m "Complete manual assignment feature"
git push origin feature/manual-assignment

# Switch to main
git checkout main
git pull origin main

# Merge feature
git merge --no-ff feature/manual-assignment

# Tag and push
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags
```

### Scenario 3: Hotfix After Release
```powershell
# Create hotfix tag
git tag -a v0.2.1 -m "Hotfix: Fixed drag-and-drop bug"
git push origin v0.2.1

# Update VERSION file
echo "0.2.1" > VERSION
git add VERSION
git commit -m "Bump version to 1.0.1"
git push origin main
```

## Tag Naming Conventions

```
v1.0.0          ← Production release
v0.2.0          ← PoC enhancement
v0.2.0-rc.1     ← Release candidate
v0.2.0-beta.1   ← Beta testing
v0.2.0-alpha.1  ← Early testing
```

## Verification

```powershell
# Verify tag was created locally
git tag -l

# Verify tag was pushed to remote
git ls-remote --tags origin

# Verify commit was pushed
git log origin/main --oneline -5

# Check remote URL
git remote -v
```

## Troubleshooting

### Issue: "Remote already exists"
```powershell
# Update remote URL
git remote set-url origin <new-url>
```

### Issue: "Authentication failed"
```powershell
# For HTTPS, use personal access token
# GitHub: Settings → Developer settings → Personal access tokens
# Azure DevOps: User settings → Personal access tokens

# Or use SSH instead of HTTPS
git remote set-url origin git@github.com:user/repo.git
```

### Issue: "Permission denied"
```powershell
# Make sure you have push access to the repository
# Contact repository admin
```

### Issue: Tag already exists
```powershell
# Delete local tag
git tag -d v0.2.0

# Delete remote tag
git push origin --delete v0.2.0

# Recreate tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

## Summary for Your Release

Run these commands in order:

```powershell
# 1. Commit all your changes
git add .
git commit -m "Release v0.2.0 - Manual assignment and QA enhancements (PoC)"

# 2. Create version tag
git tag -a v0.2.0 -m "Release v0.2.0 - See RELEASE-NOTES.md for details"

# 3. Push to remote repository
git push origin main --tags

# 4. Verify
git tag -l
git log --oneline --decorate -5
```

Done! Your v0.2.0 release is now tagged and pushed.
