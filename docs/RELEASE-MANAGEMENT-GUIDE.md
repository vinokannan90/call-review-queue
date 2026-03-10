# Enterprise Release Management Guide

## Overview
This guide covers the complete process for managing releases in an enterprise environment, from versioning to deployment.

## 1. Version Numbering Strategy

### Semantic Versioning (SemVer)
Format: `MAJOR.MINOR.PATCH`

```
Example: 1.2.3
         │ │ │
         │ │ └─ PATCH: Bug fixes (1.2.3 → 1.2.4)
         │ └─── MINOR: New features, backward-compatible (1.2.0 → 1.3.0)
         └───── MAJOR: Breaking changes (1.2.0 → 2.0.0)
```

### When to Increment

**MAJOR (x.0.0)**
- Database schema breaking changes
- API endpoint changes that break clients
- Removal of features
- Major architectural changes
- **Example**: Adding required fields, changing authentication

**MINOR (1.x.0)**
- New features (backward-compatible)
- New API endpoints
- UI enhancements
- Performance improvements
- **Example**: Adding optional fields, new dashboard features

**PATCH (1.0.x)**
- Bug fixes
- Security patches
- Documentation updates
- Minor UI tweaks
- **Example**: Fixing validation logic, correcting typos

### Pre-release Versions
- `1.0.0-alpha.1` - Early testing
- `1.0.0-beta.1` - Feature complete, testing
- `1.0.0-rc.1` - Release candidate
- `1.0.0` - Production release

## 2. Release Process Steps

### Step 1: Version Decision
```
Current Release: 0.1.0 (PoC)
New Features: Manual assignment, QA submission, DB schema changes
Breaking Changes: YES (database schema)
Decision: MAJOR release → 1.0.0
```

### Step 2: Update Version File
```powershell
# Update VERSION file
echo "1.0.0" > VERSION
```

### Step 3: Update CHANGELOG.md
```markdown
## [1.0.0] - 2026-03-09
### Added
- Feature descriptions
### Changed
- Modification descriptions
### Fixed
- Bug fix descriptions
```

### Step 4: Create Release Notes
```powershell
# Create RELEASE-NOTES.md for this version
# Include user-facing changes, migration guides
```

### Step 5: Update Application Code
```python
# In app.py or __init__.py
__version__ = "1.0.0"

# Or read from VERSION file
with open('VERSION', 'r') as f:
    __version__ = f.read().strip()
```

### Step 6: Run Tests
```powershell
# Run all tests before release
pytest tests/
python -m unittest discover

# Manual testing checklist
# - All roles work
# - Database migrations succeed
# - No console errors
```

### Step 7: Create Git Tag
```bash
# Commit all changes
git add .
git commit -m "Release v1.0.0 - Manual assignment feature"

# Create annotated tag
git tag -a v1.0.0 -m "Release v1.0.0: Manual CallerID assignment feature

Major features:
- Drag-and-drop CallerID assignment
- Reserved queue system
- QA role enhancements

Breaking changes:
- Database schema changes - migration required
"

# Push commits and tags
git push origin main
git push origin v1.0.0
```

### Step 8: Create GitHub/Azure DevOps Release

**GitHub Release:**
```bash
# Via GitHub CLI
gh release create v1.0.0 \
  --title "v1.0.0 - Manual Assignment Feature" \
  --notes-file RELEASE-NOTES.md

# Or use GitHub web interface:
# Releases → Draft a new release → Choose tag v1.0.0
```

**Azure DevOps:**
- Go to Repos → Tags → Create tag
- Go to Pipelines → Releases → Create release
- Attach artifacts and release notes

### Step 9: Database Migration Planning
```powershell
# For production deployment:

# 1. Backup existing database
pg_dump callreview_prod > backup_v0.1.0_$(date +%Y%m%d).sql

# 2. Plan migration strategy
# Option A: Fresh start (PoC → Production)
python reset_db.py
python seed.py

# Option B: Migration script (Production → Production)
python migrate_v0_to_v1.py  # Custom script
```

### Step 10: Deployment Checklist
```
□ Version number updated in all files
□ CHANGELOG.md updated
□ RELEASE-NOTES.md created
□ Git tag created and pushed
□ Tests passing
□ Documentation updated
□ Database migration tested
□ Rollback plan documented
□ Team notified
□ Release published
```

## 3. Branch Strategy

### GitFlow (Enterprise Standard)
```
main (production)
  └─ develop (integration)
       ├─ feature/manual-assignment
       ├─ feature/qa-submission
       └─ bugfix/auto-refresh-issue
```

### Release Branch Workflow
```bash
# Create release branch from develop
git checkout develop
git pull
git checkout -b release/1.0.0

# Final testing and version updates on release branch
# Update VERSION, CHANGELOG, etc.
git commit -m "Prepare for release v1.0.0"

# Merge to main
git checkout main
git merge --no-ff release/1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"

# Merge back to develop
git checkout develop
git merge --no-ff release/1.0.0

# Delete release branch
git branch -d release/1.0.0
```

## 4. Release Artifacts

### What to Include
```
release-v1.0.0/
├── source-code.zip          # Complete source
├── RELEASE-NOTES.md         # User-facing notes
├── CHANGELOG.md             # Technical changes
├── MIGRATION-GUIDE.md       # Upgrade instructions
├── requirements.txt         # Dependencies
├── database-schema.sql      # Schema dump
└── migration-scripts/       # DB migration scripts
    ├── upgrade_v0_to_v1.sql
    └── rollback_v1_to_v0.sql
```

## 5. Communication

### Internal Team (Technical)
```
Subject: Release v1.0.0 - Manual Assignment Feature

Team,

We're releasing v1.0.0 with manual CallerID assignment feature.

Key Points:
- BREAKING CHANGE: Database schema updated
- Migration required before deployment
- Deploy window: Friday 6 PM - 8 PM
- Rollback plan: Restore from backup

Technical Details: See CHANGELOG.md
Migration Guide: See docs/MIGRATION-GUIDE.md

Let me know if you have questions.
```

### Users (Non-Technical)
```
Subject: New Feature: Manual CallerID Assignment

Hello Team,

We're excited to announce Call Review Queue v1.0.0!

What's New:
✨ Admins can now drag-and-drop CallerIDs to specific team members
📋 QA team can submit CallerIDs directly
🎯 See your personal reserved queue

Training: Tuesday 10 AM (calendar invite sent)
Documentation: Updated in SharePoint

Questions? Contact support team.
```

## 6. Post-Release

### Monitor
```
□ Application logs for errors
□ Performance metrics
□ User feedback tickets
□ Database queries performance
□ Error rates in monitoring dashboard
```

### Document Lessons Learned
```markdown
## Post-Release Review - v1.0.0

### What Went Well
- Smooth database migration
- No critical bugs reported
- Users adopted drag-and-drop quickly

### What Could Improve
- Need better staging environment
- Migration took longer than expected
- Should have more automated tests

### Action Items
- [ ] Set up CI/CD pipeline
- [ ] Add integration tests
- [ ] Document disaster recovery
```

## 7. Version File in Code

### Option A: Separate VERSION File (Recommended)
```python
# app.py
import os

def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    with open(version_file, 'r') as f:
        return f.read().strip()

__version__ = get_version()
```

### Option B: In Python __init__.py
```python
# __init__.py
__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
```

### Option C: In setup.py
```python
# setup.py
from setuptools import setup

setup(
    name="call-review-queue",
    version="1.0.0",
    # ...
)
```

## 8. Automation

### CI/CD Pipeline Example (Azure DevOps)
```yaml
# azure-pipelines.yml
trigger:
  tags:
    include:
    - v*

pool:
  vmImage: 'ubuntu-latest'

steps:
- script: |
    # Extract version from tag
    VERSION=$(git describe --tags --abbrev=0 | sed 's/v//')
    echo "##vso[task.setvariable variable=VERSION]$VERSION"
  displayName: 'Get Version from Tag'

- script: |
    pip install -r requirements.txt
    pytest tests/
  displayName: 'Run Tests'

- task: GitHubRelease@1
  inputs:
    gitHubConnection: 'GitHub'
    action: 'create'
    tagSource: 'gitTag'
    releaseNotesFilePath: 'RELEASE-NOTES.md'
```

## Summary

For your current release (v1.0.0), I've created:
1. ✅ VERSION file (1.0.0)
2. ✅ CHANGELOG.md (structured change history)
3. ✅ RELEASE-NOTES.md (user-facing documentation)
4. ✅ Updated README.md (version badge)

**Next Steps**:
1. Review and adjust version files as needed
2. Commit all changes
3. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
4. Push: `git push && git push --tags`
5. Create release in GitHub/Azure DevOps
6. Deploy to production environment
