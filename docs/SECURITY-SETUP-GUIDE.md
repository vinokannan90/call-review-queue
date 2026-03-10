# Security Setup Guide

This guide explains how to configure and deploy the Call Review Queue application securely.

---

## 🔧 Initial Setup

### 1. Install Dependencies

```powershell
# Navigate to project directory
cd c:\source\call-review-queue

# Install required packages
pip install -r requirements.txt
```

**New Security Packages:**
- `Flask-WTF==1.2.1` - CSRF protection

---

### 2. Environment Configuration

Create a `.env` file in the project root:

```powershell
# Copy example file
cp .env.example .env

# Edit with your secure values
notepad .env
```

**Critical Configuration Values:**

```ini
# REQUIRED: Generate a strong secret key
SECRET_KEY=your-secret-key-here-generate-with-python-secrets

# Database (SQLite for PoC, PostgreSQL for production)
DATABASE_URL=sqlite:///callreview_poc.db

# Security Settings
SESSION_COOKIE_SECURE=False  # Set True in production with HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600  # 1 hour

# Environment
FLASK_ENV=development  # Change to 'production' for deployment
```

---

### 3. Generate Secure SECRET_KEY

**Generate a cryptographically strong secret key:**

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example output:**
```
a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**⚠️ IMPORTANT:** Never commit your SECRET_KEY to version control!

---

## 🔒 Security Checklist

### For Development/PoC Environment

- [x] Created `.env` file with SECRET_KEY
- [x] Added `.env` to `.gitignore`
- [x] Verified FLASK_ENV=development
- [x] SESSION_COOKIE_SECURE=False (no HTTPS in dev)
- [x] Database connection working

### For Production Deployment

- [ ] Generated strong SECRET_KEY (64+ chars)
- [ ] Set FLASK_ENV=production
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Configured PostgreSQL database
- [ ] Enabled HTTPS/TLS on web server
- [ ] Set up Redis for rate limiting (optional)
- [ ] Configured log forwarding
- [ ] Reviewed and updated CSP policy
- [ ] Implemented Azure AD authentication (recommended)
- [ ] Set up monitoring/alerting

---

## 🚀 Running the Application Securely

### Development Mode

```powershell
python app.py
```

**Security Warnings on Startup:**
```
============================================================
SECURITY CONFIGURATION WARNINGS:
============================================================
  • WARNING: Using default SECRET_KEY
  • INFO: SESSION_COOKIE_SECURE requires HTTPS
============================================================
```

Access at: http://127.0.0.1:5000

### Production Mode

```powershell
# Set environment to production
$env:FLASK_ENV="production"

# Use WSGI server (not Flask development server)
pip install gunicorn  # Linux/Azure App Service
pip install waitress  # Windows alternative

# Run with Gunicorn (Linux)
gunicorn -w 4 -b 0.0.0.0:8000 app:app

# Run with Waitress (Windows)
waitress-serve --port=8000 app:app
```

---

## 🛡️ Security Features Explained

### 1. CSRF Protection

**How it Works:**
All HTML forms automatically include a hidden CSRF token. Flask-WTF validates tokens on POST requests.

**In Templates:**
Templates already include CSRF protection. No changes needed.

**For AJAX Requests:**
AJAX endpoints verify `X-Requested-With: XMLHttpRequest` header.

### 2. Rate Limiting

**Current Configuration:**

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 10 | 5 minutes |
| Submit CallerID | 30 | 1 minute |
| Admin actions | 60 | 1 minute |
| Drag-drop | 120 | 1 minute |

**Upgrade for Production:**
Replace in-memory rate limiter with Redis-backed solution:

```python
# Install Flask-Limiter with Redis
pip install Flask-Limiter redis

# In app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

### 3. Session Security

**Configuration Options:**

```python
# .env file
SESSION_COOKIE_HTTPONLY=True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE=Lax   # CSRF protection
SESSION_COOKIE_SECURE=True    # HTTPS only (production)
PERMANENT_SESSION_LIFETIME=3600  # 1 hour timeout
```

**Session Expiry:**
Sessions expire after 1 hour of inactivity (configurable).

### 4. Input Validation

**Automatically Validated:**
- CallerID numbers (3-50 chars, alphanumeric + phone symbols)
- URLs (RFC-compliant validation)
- CORE IDs (3-100 chars, alphanumeric + hyphens)
- Text fields (length limits enforced)

**Custom Validation:**
```python
from security_config import InputValidator

# Validate CallerID
is_valid, error_msg = InputValidator.validate_caller_id(caller_id)
if not is_valid:
    flash(error_msg, 'danger')
```

---

## 🔍 Security Monitoring

### Audit Logging

**Log File Location:**
Logs print to console by default. For production, configure file logging:

```python
# In .env
LOG_LEVEL=INFO
LOG_FILE=logs/application.log
```

**Key Events Logged:**
- Successful/failed logins
- Administrative actions
- Security violations (rate limits, unauthorized access)
- Application errors

**Log Format:**
```
2026-03-09 14:23:15 [INFO] app: Successful login - User: admin.user - IP: 192.168.1.100
```

### Monitoring Failed Logins

```powershell
# Search logs for failed logins
Select-String -Path "logs/application.log" -Pattern "Failed login"

# Count failed attempts per IP
Get-Content logs/application.log | Select-String "Failed login" | 
  ForEach-Object { ($_ -split "IP: ")[1] } | Group-Object | 
  Sort-Object Count -Descending
```

---

## 🌐 HTTPS/TLS Configuration

### Development (Self-Signed Certificate)

```powershell
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Run with HTTPS
python app.py --cert=cert.pem --key=key.pem
```

### Production (Let's Encrypt)

**Azure App Service:**
SSL/TLS configured automatically with Azure-managed certificates.

**Custom Server:**
```bash
# Install Certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Configure web server (Nginx/Apache)
```

---

## 🔐 Database Security

### SQLite (PoC Only)

```python
DATABASE_URL=sqlite:///callreview_poc.db
```

**Security Notes:**
- File-based, no network exposure
- Suitable for PoC/development only
- **Do NOT use in production**

### PostgreSQL (Production)

```python
DATABASE_URL=postgresql://username:password@hostname:5432/database
```

**Security Best Practices:**
- Use Azure SQL Database with managed identity
- Enable SSL connection: `?sslmode=require`
- Restrict firewall to application servers only
- Use strong passwords (20+ chars)
- Enable audit logging
- Regular backups

**Connection String Security:**
```ini
# Azure SQL with SSL
DATABASE_URL=postgresql://user@server:pass@server.postgres.database.azure.com:5432/db?sslmode=require
```

---

## 🛠️ Security Maintenance

### Monthly Tasks

```powershell
# Check for vulnerable dependencies
pip install pip-audit
pip-audit

# Update dependencies
pip list --outdated
pip install --upgrade Flask Flask-Login Flask-SQLAlchemy Flask-WTF
```

### Quarterly Tasks

- Review security logs for anomalies
- Update SECRET_KEY (rotate every 90 days)
- Review user access and roles
- Test disaster recovery procedures

### Annual Tasks

- Penetration testing
- Security audit
- Compliance review (SOC 2, ISO 27001)

---

## 🚨 Security Incident Response

### If You Suspect a Breach

1. **Immediate Actions:**
   ```powershell
   # Stop the application
   taskkill /F /IM python.exe
   
   # Backup logs
   cp logs/application.log logs/incident-$(Get-Date -Format 'yyyy-MM-dd-HHmmss').log
   
   # Backup database
   cp callreview_poc.db callreview_poc-incident.db
   ```

2. **Rotate Secrets:**
   ```powershell
   # Generate new SECRET_KEY
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Update .env file
   # Restart application
   ```

3. **Investigate:**
   - Review logs for suspicious activity
   - Check for unauthorized access attempts
   - Identify compromised accounts

---

## 📞 Support & Resources

**Security Questions:**
- Review [SECURITY-HARDENING-REPORT.md](SECURITY-HARDENING-REPORT.md)
- Check Flask security documentation: https://flask.palletsprojects.com/en/3.0.x/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/

**Reporting Security Issues:**
- Email: security@yourcompany.com
- Create private security advisory on GitHub

---

## ✅ Security Verification

### Quick Security Check

```powershell
# 1. Verify SECRET_KEY is set
$env:SECRET_KEY -ne "dev-only-secret-change-in-prod"

# 2. Check FLASK_ENV
$env:FLASK_ENV

# 3. Test application startup
python app.py
# Should show no CRITICAL warnings

# 4. Test login rate limiting
# Try logging in 11 times with wrong password - should be blocked

# 5. Verify CSRF protection
# Try submitting form without CSRF token - should fail
```

---

**Last Updated**: March 9, 2026  
**Version**: 0.2.0 (Security Hardened)
