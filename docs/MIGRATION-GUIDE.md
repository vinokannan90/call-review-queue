# Migration Guide

## v0.4.0 → v0.4.1 (Patch - No Database Changes)

### Overview
Simple code update with UX improvements for timer persistence and admin reset controls.

✅ **No Breaking Changes**: Code-only update, no database schema changes required.

### What's New in v0.4.1
- Timer display persists after team member signs off
- Admin can reset working/break timers via dashboard buttons
- CSS linter errors fixed in admin_reports.html

### Migration Steps

#### Step 1: Update Code
```powershell
# Pull latest code
git pull origin main

# OR checkout tag
git checkout v0.4.1
```

#### Step 2: Restart Application
```powershell
# Stop current Flask app (CTRL+C)

# Start updated version
python app.py
```

#### Step 3: Verify Changes
1. Login as admin
2. Navigate to admin dashboard
3. Verify time tracking displays for signed-off members
4. Test reset buttons next to working/break timers
5. Check Reports page for CSS display issues (should be clean)

**Total Downtime**: < 10 seconds (app restart only)

---

# Migration Guide: v0.3.0 → v0.4.0

## Overview
This guide helps you upgrade from v0.3.0 (Security Hardening) to v0.4.0 (Time Tracking & Performance Reports) with comprehensive attendance monitoring and reporting features.

⚠️ **BREAKING CHANGES**: This release requires database schema update with new `attendance_logs` table. **All existing data will be lost** when resetting the database.

## ⚠️ Breaking Changes Summary
1. **Database schema change** - New `attendance_logs` table added (requires reset)
2. **Data loss** - Existing CallerIDs, assignments, QA reviews, and attendance will be lost
3. **Automatic time tracking** - All complaint team members now tracked automatically
4. **No backward compatibility** - Cannot rollback to v0.3.0 without database restore

## Prerequisites
- Python environment activated (`.venv`)
- Application stopped
- `.env` file configured (from v0.3.0)
- **BACKUP**: If you have production data you need to preserve, backup the database first

## Migration Steps

### Step 1: Backup Current Database (CRITICAL for Production)
```powershell
# For SQLite (default PoC setup)
Copy-Item callreview_poc.db callreview_poc.db.backup_v0.3.0

# For PostgreSQL (production)
pg_dump callreview_prod > backup_v0.3.0_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Verify backup was created
dir *backup*
```

**⚠️ WARNING**: Step 4 will delete all data. This backup is your only recovery option.

### Step 2: Stop the Application
```powershell
# Stop Flask app if running
# Press CTRL+C in terminal where app is running
# Or kill the process
Get-Process python | Where-Object {$_.Path -like "*call-review-queue*"} | Stop-Process
```

### Step 3: Update Code
```powershell
# Pull latest code
git fetch origin
git checkout v0.4.0

# OR pull from branch
git pull origin main
```

### Step 4: Reset Database (⚠️ **DATA LOSS**)
```powershell
# This will DELETE all data and recreate schema with new table
python reset_db.py

# When prompted:
# "Are you sure you want to reset the database? (yes/no):"
# Type: yes
```

**Expected output:**
```
Database reset successfully.
Tables created: users, team_members, caller_ids, assignments, qa_reviews, attendance_logs
```

### Step 5: Reseed Demo Data
```powershell
# Populate with fresh demo data including users and test CallerIDs
python seed.py
```

**Expected output:**
```
Seeding database...
Created X users
Created X team members
Created X CallerIDs
Database seeded successfully!
```

### Step 6: Verify Installation
```powershell
# Start application
python app.py
```

**Expected output:**
```
2026-03-09 22:51:01 [WARNING] __main__: Starting application in DEVELOPMENT mode (debug enabled)
 * Running on http://127.0.0.1:5000
```

### Step 7: Test Time Tracking Features
Open http://127.0.0.1:5000 in browser and test:

#### ✅ Test 1: Clock-In Tracking
```
1. Login as complaint member (tom.harris/Complaint@123)
2. Click "Present" button
3. Verify clock-in time appears (should show current time)
4. Note: Timer won't show initially - requires admin approval first
```

#### ✅ Test 2: Admin Dashboard Timers
```
1. Open new browser tab/window (or use incognito)
2. Login as admin (admin/Admin@123)
3. Find tom.harris card in Team Availability section
4. Click "Approve" button
5. Verify time tracking info appears:
   - Clock In: [current time]
   - Working: 00:00:XX (running timer)
   - Break: 00:00:00
   - Processed: 0
6. Wait 10 seconds and verify timer is updating
```

#### ✅ Test 3: Break Time Tracking
```
1. Switch back to tom.harris tab
2 Click "Break" button
3. Switch to admin tab
4. Verify "Working" timer stopped updating
5. Verify "Break" timer is now running
6. Switch back to tom.harris tab
7. Click "Present" button to return from break
8. Switch to admin tab
9. Verify "Working" timer resumed
10. Verify "Break" shows accumulated time
```

#### ✅ Test 4: Performance Counter
```
1. As tom.harris, wait for a CallerID assignment (or manually assign via admin)
2. Complete the assignment (dismiss or raise)
3. Switch to admin tab
4. Verify "Processed" counter incremented to 1
```

#### ✅ Test 5: Reports Page
```
1. As admin, click "Reports" button (in page header)
2. Verify reports page loads
3. Select "Today" filter
4. Click "Generate Report"
5. Verify tom.harris appears with:
   - Total Processed: 1 (from Test 4)
   - Working Time: [time worked]
   - Raised/Dismissed breakdown
6. Test other filters (This Week, This Month)
```

#### ✅ Test 6: Custom Date Range
```
1. On reports page, select "Custom Range" radio button
2. Set start date = today
3. Set end date = today
4. Click "Generate Report"
5. Verify same data as "Today" filter
6. Try setting end date 15 days ahead
7. Verify error: "Date range cannot exceed 14 days"
```

### Step 8: Sign Off Test
```
1. As tom.harris, click "Sign Off" button
2. Confirm dialog
3. Switch to admin tab
4. Verify tom.harris card shows "SIGNED OFF" badge
5. Verify time tracking section disappeared
6. Check reports page again
7. Verify working time frozen at sign-off time
```

## New Features Available in v0.4.0

### For Administrators
- **Real-time monitoring**: Live timers showing team activity
- **Performance reports**: Comprehensive analytics by date range
- **Attendance tracking**: Clock-in, clock-out, break times
- **Productivity metrics**: CallerIDs processed counts
- **Raised item analysis**: Detailed breakdown of escalated calls

### For Complaint Team Members
- **Automatic tracking**: No manual time entry required
- **Transparent system**: Know that activity is monitored
- **Fair break tracking**: All break time properly recorded

## Troubleshooting

### Issue: "Table 'attendance_logs' doesn't exist" error
**Solution**:
1. Verify you ran `python reset_db.py`
2. Check database file was recreated
3. Look for error messages during reset
4. Try deleting database file manually and running reset again

### Issue: Timers not updating on admin dashboard
**Solution**:
1. Check browser console (F12) for JavaScript errors
2. Verify page loaded completely
3. Hard refresh (Ctrl+Shift+R or Ctrl+F5)
4. Ensure team member is clocked in (marked Present)

### Issue: No data in reports
**Solution**:
1. Verify team members have clocked in today
2. Check selected date range includes today
3. Ensure some CallerIDs were processed
4. Check database for attendance_logs: `SELECT * FROM attendance_logs;`

### Issue: Reports show 0 working time
**Solution**:
1. Member must mark "Present" to clock in
2. Admin must approve member
3. Wait at least a few seconds for time to accumulate
4. Refresh page to see updated times

### Issue: Database reset fails
**Solution**:
1. Ensure app is stopped (no python processes running)
2. Check file permissions
3. Try manually deleting `callreview_poc.db` file
4. Re-run `python reset_db.py`

## Rollback Procedure (If Needed)

If you encounter critical issues and need to rollback:

```powershell
# Stop application
# Press CTRL+C

# Checkout previous version
git checkout v0.3.0

# Restore database backup
Copy-Item callreview_poc.db.backup_v0.3.0 callreview_poc.db -Force

# For PostgreSQL:
# psql callreview_prod < backup_v0.3.0_YYYYMMDD_HHMMSS.sql

# Restart application
python app.py
```

**Note**: You will lose all v0.4.0 features (time tracking, reports) when rolling back.

## Database Schema Changes

### New Table: attendance_logs

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| team_member_id | INTEGER | FK to team_members (indexed) |
| log_date | DATE | Date of attendance (indexed) |
| clock_in_time | DATETIME | When marked Present |
| clock_out_time | DATETIME | When marked Sign Off (nullable) |
| total_break_seconds | INTEGER | Accumulated break time |
| current_break_start | DATETIME | If on break now (nullable) |
| callers_processed | INTEGER | Total completed today |
| callers_dismissed | INTEGER | Dismissed count |
| callers_raised | INTEGER | Raised count |
| last_updated | DATETIME | Last modification time |

**Constraints:**
- UNIQUE(team_member_id, log_date) - One log per member per day

## Production Deployment Notes

For production environments:

### Use Database Migrations (Alembic)
```powershell
# Install Alembic
pip install alembic

# Initialize (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add attendance_logs table"

# Apply migration
alembic upgrade head
```

### Data Preservation Strategy
If you have production data to preserve:
1. Export existing data to CSV/JSON
2. Apply migration (creates new table, preserves old data)
3. Map old data to new schema if needed
4. Import preserved data

### High-Availability Considerations
- Schedule migration during maintenance window
- Use blue-green deployment if possible
- Test migration on staging environment first
- Have rollback plan ready

## Configuration Changes

### No .env Changes Required
This release uses existing configuration from v0.3.0:
- SECRET_KEY remains the same
- All session/security settings unchanged
- No new environment variables

### Optional: Adjust Rate Limits
If reports generation causes performance issues:
```python
# In app.py, add rate limit to reports route
@app.route('/admin/reports')
@rate_limit(limit=10, window_seconds=60)  # 10 reports per minute
```

## Performance Considerations

### Database Size
- Each team member generates 1 attendance_log per working day
- With 10 members working 250 days/year = 2,500 rows/year
- Minimal storage impact for typical PoC usage

### Report Query Performance
- Indexed fields (log_date, team_member_id) ensure fast queries
- 14-day limit on custom ranges prevents expensive queries
- Aggregation done in Python (consider SQL aggregation for large datasets)

### Timer Updates
- JavaScript timer updates are client-side only
- No server requests for timer display
- No performance impact on server

## Security Notes

- Time tracking data is sensitive employee information
- Ensure proper access controls (only admins can view reports)
- Consider data retention policies for compliance
- Audit logs track when reports are accessed (existing logging)

## Getting Help

- **Configuration Issues**: Check `.env` file and restart app
- **Database Errors**: Review error messages during reset
- **Feature Questions**: See RELEASE-NOTES.md for feature descriptions
- **Bug Reports**: Include error messages and steps to reproduce

---

# Migration Guide: v0.2.0 → v0.3.0

## Overview
This guide helps you upgrade from v0.2.0 (Manual Assignment PoC) to v0.3.0 (Security Hardening Release) with enterprise-grade security controls.

⚠️ **BREAKING CHANGES**: This release requires Flask-WTF installation and mandatory `.env` configuration.

## ⚠️ Breaking Changes Summary
1. **Flask-WTF dependency** - Required for CSRF protection (all forms now require CSRF tokens)
2. **Environment configuration** - SECRET_KEY must be set in `.env` file
3. **Rate limiting** - Excessive requests will be blocked (may impact automated scripts)
4. **Session security** - Enhanced cookie settings (HTTPOnly, SameSite)
5. **No database changes** - Existing data preserved

## Prerequisites
- Python environment activated (`.venv`)
- Application stopped
- Write access to create `.env` file

## Migration Steps

### Step 1: Backup Current Configuration (Optional)
```powershell
# If you have any custom configurations
Copy-Item app.py app.py.backup
```

### Step 2: Stop the Application
```powershell
# Stop Flask app if running
# Press CTRL+C in terminal where app is running
```

### Step 3: Update Code
```powershell
# Pull latest code
git fetch origin
git checkout v0.3.0

# OR pull from branch
git pull origin main
```

### Step 4: Install New Dependencies
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install Flask-WTF and all dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Collecting Flask-WTF==1.2.1
Installing collected packages: Flask-WTF
Successfully installed Flask-WTF-1.2.1
```

### Step 5: Generate SECRET_KEY
```powershell
# Generate a secure random SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

**Output example:**
```
890c30bd777711e9d6ed1e84d2adb65bd880446f1440b7edae60e3ae55a9b16e
```

**⚠️ Save this key** - You'll need it in the next step.

### Step 6: Create Environment Configuration
```powershell
# Copy template to .env
Copy-Item .env.example .env

# Edit .env file and update SECRET_KEY with generated key
notepad .env
```

**Required changes in `.env`:**
```ini
SECRET_KEY=YOUR_GENERATED_KEY_FROM_STEP_5

# For development (current state)
SESSION_COOKIE_SECURE=False
FLASK_ENV=development

# For production deployment (update these later)
# SESSION_COOKIE_SECURE=True
# FLASK_ENV=production
```

**All other settings can remain as default.**

### Step 7: Verify Installation
```powershell
# Start application
python app.py
```

**Expected output:**
```
2026-03-09 22:51:01 [WARNING] __main__: Starting application in DEVELOPMENT mode (debug enabled)
 * Running on http://127.0.0.1:5000
```

**⚠️ If you see errors:**
- `ModuleNotFoundError: No module named 'flask_wtf'` → Repeat Step 4
- Warning about SECRET_KEY → Check `.env` file exists and SECRET_KEY is set

### Step 8: Test Security Features
Open http://127.0.0.1:5000 in browser and test:

#### ✅ Test 1: CSRF Protection
```
1. Login as admin (admin/Admin@123)
2. Forms should submit successfully
3. Check browser DevTools → Network → Form Data → csrf_token present
```

#### ✅ Test 2: Rate Limiting
```
1. Logout
2. Try logging in with wrong password 11 times
3. 11th attempt should show "Too many requests" error
4. Wait 5 minutes for reset
```

#### ✅ Test 3: Security Headers
```
1. Open browser DevTools → Network tab
2. Click any page
3. Check Response Headers for:
   - Content-Security-Policy
   - X-Frame-Options
   - X-Content-Type-Options
```

#### ✅ Test 4: Role-Based Access
```
1. Login as regular user (jsmith/User@123)
2. Try accessing http://127.0.0.1:5000/admin/dashboard
3. Should redirect with "Access denied" message
```

#### ✅ Test 5: Input Validation
```
1. Login as user
2. Try submitting CallerID with invalid format (e.g., "abc" or very long string)
3. Should show validation error
```

### Step 9: Review Security Documentation
Read the comprehensive security documentation:

```powershell
# Open documentation in browser or text editor
code docs/SECURITY-HARDENING-REPORT.md    # Complete audit report
code docs/SECURITY-SETUP-GUIDE.md         # Production setup guide
code docs/SECURITY-SUMMARY.md             # Demo quick reference
```

## New Features Available in v0.3.0

### For All Users
- **CSRF Protection**: All forms protected against Cross-Site Request Forgery
- **Rate Limiting**: Prevents brute force attacks
- **Enhanced Security**: Multiple security layers working together

### For Administrators
- **Audit Logging**: All admin actions logged with timestamps and IP addresses
- **Security Monitoring**: Track failed login attempts and authorization failures

### For Developers/Operators
- **Environment Configuration**: Centralized `.env` file for all settings
- **Security Headers**: Modern browser protections automatically applied
- **Error Handling**: Improved error pages that don't leak sensitive information
- **Logging System**: Comprehensive logging for security events and errors

## Rollback Procedure (If Needed)

If you encounter issues and need to rollback:

```powershell
# Stop application
# Press CTRL+C

# Checkout previous version
git checkout v0.2.0

# Restore backup if you made one
Copy-Item app.py.backup app.py -Force

# Restart application
python app.py
```

**Note**: No database changes in v0.3.0, so database remains compatible.

## Production Deployment Checklist

When deploying to production with v0.3.0:

### Required Changes
- [ ] Generate new SECRET_KEY for production (never reuse development key)
- [ ] Set `SESSION_COOKIE_SECURE=True` in `.env`
- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR` in `.env`
- [ ] Configure HTTPS (use nginx reverse proxy with SSL/TLS)
- [ ] Set proper `MAX_CONTENT_LENGTH` for your use case

### Recommended Changes
- [ ] Use PostgreSQL instead of SQLite (update `DATABASE_URL`)
- [ ] Implement Redis-based rate limiting for multi-instance deployments
- [ ] Configure log aggregation (e.g., ELK stack, Azure Monitor)
- [ ] Set up monitoring for rate limit violations
- [ ] Review and customize Content-Security-Policy for your domain

### Security Review
- [ ] Review all security settings in `.env`
- [ ] Test rate limiting thresholds
- [ ] Verify HTTPS is working
- [ ] Test session timeout (default: 1 hour)
- [ ] Review audit logs for any issues
- [ ] Run security scan (OWASP ZAP, Burp Suite)

## Configuration Reference

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | (none) | Cryptographic key for session encryption |
| `DATABASE_URL` | No | `sqlite:///callreview_poc.db` | Database connection string |
| `SESSION_COOKIE_HTTPONLY` | No | `True` | Prevent JavaScript access to session cookie |
| `SESSION_COOKIE_SAMESITE` | No | `Lax` | CSRF protection at cookie level |
| `SESSION_COOKIE_SECURE` | No | `False` | Require HTTPS for cookies (production: `True`) |
| `PERMANENT_SESSION_LIFETIME` | No | `3600` | Session timeout in seconds (1 hour) |
| `MAX_CONTENT_LENGTH` | No | `16777216` | Max request size in bytes (16MB) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FLASK_ENV` | No | `development` | Environment (development, production) |

### Rate Limit Defaults

These are hardcoded in `app.py` but can be customized:
- Login: 10 attempts per 5 minutes
- Submissions: 30 per minute
- Admin operations: 60 per minute
- Manual assignments: 120 per minute

## Troubleshooting

### Issue: "CSRF token is missing" error
**Solution**: 
1. Clear browser cookies
2. Restart application
3. Try logging in again
4. Verify CSRF tokens in HTML source (View Source → search for `csrf_token`)

### Issue: Forms not submitting
**Solution**:
1. Check browser console for JavaScript errors
2. Verify CSRF token is present in form
3. Check app logs for validation errors

### Issue: Rate limit blocking legitimate users
**Solution**:
1. Increase rate limits in `app.py` (search for `@rate_limit` decorators)
2. Restart application
3. Or wait for automatic reset (window expires)

### Issue: Can't access admin routes after login
**Solution**:
1. Verify login was successful (check for flash messages)
2. Check user role in database: `SELECT username, role FROM users;`
3. Review audit log in terminal output

### Issue: Application won't start (SECRET_KEY warning)
**Solution**:
1. Verify `.env` file exists in project root
2. Check SECRET_KEY is set (not empty)
3. Ensure no extra quotes around SECRET_KEY value

## Getting Help

- **Security Documentation**: See `docs/SECURITY-*.md` files
- **GitHub Issues**: Report bugs or issues
- **Configuration**: Check `.env.example` for all available settings

## Notes for Enterprise Customers

This release implements security controls aligned with:
- **OWASP Top 10 2021** - All major vulnerabilities addressed
- **SOC 2 Type II** - Audit logging and access controls ready
- **ISO 27001** - Security controls framework implemented
- **NIST Cybersecurity Framework** - Defense-in-depth architecture

For production deployments requiring compliance certifications, review `docs/SECURITY-HARDENING-REPORT.md` for detailed control documentation.

---

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
