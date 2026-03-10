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
