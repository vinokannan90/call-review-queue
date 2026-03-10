# Migration Guide: v0.1.0 → v0.2.0

## Overview
This guide helps you upgrade from the initial PoC (v0.1.0) to v0.2.0 with manual assignment features.

## ⚠️ Breaking Changes
- **Database schema changes** - New columns added to `caller_ids` table
- **Data loss warning** - Existing assignments will be lost during migration

## Prerequisites
- Backup of existing database (if needed)
- Python environment activated
- Application stopped

## Migration Steps

### Step 1: Backup Current Data (Optional)
```powershell
# If you need to preserve data
# For SQLite
Copy-Item instance\callreview_poc.db instance\callreview_poc.db.backup

# For PostgreSQL
pg_dump callreview_prod > backup_v0.1.0_$(Get-Date -Format "yyyyMMdd").sql
```

### Step 2: Stop the Application
```powershell
# Stop Flask app if running
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force
```

### Step 3: Update Code
```powershell
# Pull latest code
git fetch origin
git checkout v1.0.0

# OR pull from branch
git pull origin main
```

### Step 4: Update Dependencies
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Update packages (if any new dependencies)
pip install -r requirements.txt
```

### Step 5: Reset Database
```powershell
# Reset database schema to include new columns
python reset_db.py
# Type 'yes' when prompted
```

### Step 6: Seed Demo Data
```powershell
# Populate with fresh demo data
python seed.py
```

### Step 7: Verify Installation
```powershell
# Start application
python app.py

# Open browser to http://localhost:5000
# Test login with admin/Admin@123
```

### Step 8: Test New Features
```
□ Login as admin (admin/Admin@123)
□ Login as complaint member (tom.harris/Complaint@123) in another tab
□ Have complaint member click "Present"
□ Admin approves the member
□ Drag a CallerID from queue to the team member card
□ Verify it appears in "Reserved" section
□ Login as complaint member and check "My Reserved Queue"
```

## New Features in v0.2.0

### For Administrators
- **Drag & Drop Assignment**: Drag CallerIDs onto team member cards
- **Reservation Management**: Up to 3 CallerIDs per member
- **Visual Indicators**: See reservation status at a glance
- **Unreserve Function**: Click X on badge to remove reservation

### For Complaint Team
- **My Reserved Queue**: See CallerIDs manually assigned to you
- **Priority Processing**: Reserved CallerIDs processed first
- **Auto-clear on Sign-off**: Reservations returned to queue

### For QA Team
- **Direct Submission**: Submit CallerIDs through QA dashboard
- **Submission History**: Track submitted CallerIDs
- **No Auto-refresh**: Form inputs no longer disappear

## Database Schema Changes

### New Columns in `caller_ids` Table
```sql
ALTER TABLE caller_ids
ADD COLUMN reserved_for_member_id INTEGER NULL REFERENCES team_members(id);

ALTER TABLE caller_ids
ADD COLUMN reserved_at TIMESTAMP NULL;

ALTER TABLE caller_ids
ADD COLUMN reserved_by_id INTEGER NULL REFERENCES users(id);
```

## Production Migration Strategy

### Option A: Fresh Start (Recommended for PoC)
Best for PoC environment where data preservation isn't critical.

```powershell
# 1. Backup (if needed)
pg_dump production_db > backup.sql

# 2. Reset schema
python reset_db.py

# 3. Create production users (custom script)
python create_production_users.py
```

### Option B: Data Preservation (Advanced)
For preserving existing CallerIDs and assignments.

```sql
-- 1. Add new columns (run in production DB)
ALTER TABLE caller_ids ADD COLUMN reserved_for_member_id INTEGER NULL;
ALTER TABLE caller_ids ADD COLUMN reserved_at TIMESTAMP NULL;
ALTER TABLE caller_ids ADD COLUMN reserved_by_id INTEGER NULL;

-- 2. Add foreign key constraints
ALTER TABLE caller_ids 
ADD CONSTRAINT fk_reserved_for_member 
FOREIGN KEY (reserved_for_member_id) REFERENCES team_members(id);

ALTER TABLE caller_ids 
ADD CONSTRAINT fk_reserved_by 
FOREIGN KEY (reserved_by_id) REFERENCES users(id);

-- 3. Create indexes
CREATE INDEX idx_caller_ids_reserved_for ON caller_ids(reserved_for_member_id);
```

## Rollback Plan

If issues occur, rollback to v0.1.0:

```powershell
# 1. Stop application
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force

# 2. Checkout previous version
git checkout v0.1.0

# 3. Restore database backup
# For SQLite
Copy-Item instance\callreview_poc.db.backup instance\callreview_poc.db

# For PostgreSQL
psql production_db < backup_v0.1.0.sql

# 4. Restart application
python app.py
```

## Troubleshooting

### Issue: "AmbiguousForeignKeysError" on startup
**Solution**: Database schema hasn't been updated. Run `python reset_db.py`

### Issue: Drag and drop not working
**Cause**: Browser compatibility
**Solution**: Use Chrome, Edge, or Firefox (modern browsers)

### Issue: Reserved CallerIDs not showing
**Cause**: Database not properly seeded
**Solution**: Run `python seed.py` again

### Issue: Old database structure
**Symptoms**: Missing columns errors
**Solution**: 
```powershell
# Force reset
Remove-Item instance\callreview_poc.db -Force
python reset_db.py
python seed.py
```

## Configuration Changes

### No changes to `.env` required
The environment configuration remains the same:
```
DATABASE_URL=sqlite:///callreview_poc.db
SECRET_KEY=your-secret-key
```

## Training Resources

### Updated Documentation
- [README.md](../README.md) - Updated with v0.2.0 features
- [RELEASE-NOTES.md](../RELEASE-NOTES.md) - Complete feature list
- [CHANGELOG.md](../CHANGELOG.md) - Technical changes

### User Training
- **Admin Training**: 15 minutes
  - Drag-and-drop demo
  - Reservation limits
  - Unreserve function
  
- **Complaint Team Training**: 10 minutes
  - Reserved queue overview
  - Priority processing
  - Sign-off behavior

- **QA Training**: 5 minutes
  - New submission form
  - Form fields and validation

## Support

For migration assistance:
- Review troubleshooting section above
- Check application logs: `logs/app.log`
- Contact development team
- File issue on GitHub/Azure DevOps

## Post-Migration Checklist

```
□ Application starts without errors
□ All users can login
□ Admin can drag-and-drop CallerIDs
□ Complaint members see reserved queue
□ QA can submit CallerIDs
□ Auto-assignment works correctly
□ Sign-off clears reservations
□ No console errors in browser
□ Database connections stable
□ Performance acceptable
```

## Next Steps

After successful migration:
1. Monitor application logs for 24-48 hours
2. Gather user feedback
3. Address any usability concerns
4. Plan for v0.3.0 enhancements or v1.0.0 production release

---

**Migration Time Estimate**: 15-30 minutes  
**Downtime Required**: 5-10 minutes  
**Risk Level**: Low (PoC environment)  
**Rollback Time**: 5 minutes
