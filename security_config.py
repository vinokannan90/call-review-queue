"""
Security configuration and utilities for Call Review Queue application.
Implements enterprise-grade security controls for PoC demonstration.
"""

import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import request, abort, flash, redirect, url_for

# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

class InputValidator:
    """Centralized input validation with security-focused rules."""
    
    # Regex patterns for validation
    CALLER_ID_PATTERN = re.compile(r'^[0-9\-\+\(\)\s]{3,50}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]{3,80}$')
    CORE_ID_PATTERN = re.compile(r'^[A-Z0-9\-]{3,100}$', re.IGNORECASE)
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    # Length limits
    MAX_CALLER_ID_LENGTH = 50
    MAX_USERNAME_LENGTH = 80
    MAX_NAME_LENGTH = 120
    MAX_URL_LENGTH = 500
    MAX_REASON_LENGTH = 500
    MAX_COMMENT_LENGTH = 2000
    MAX_JUSTIFICATION_LENGTH = 2000
    MAX_CORE_ID_LENGTH = 100
    
    @staticmethod
    def validate_caller_id(caller_id: str) -> tuple[bool, Optional[str]]:
        """Validate CallerID format and length."""
        if not caller_id or not isinstance(caller_id, str):
            return False, "CallerID is required"
        
        caller_id = caller_id.strip()
        
        if len(caller_id) < 3:
            return False, "CallerID must be at least 3 characters"
        
        if len(caller_id) > InputValidator.MAX_CALLER_ID_LENGTH:
            return False, f"CallerID cannot exceed {InputValidator.MAX_CALLER_ID_LENGTH} characters"
        
        if not InputValidator.CALLER_ID_PATTERN.match(caller_id):
            return False, "CallerID contains invalid characters (allowed: digits, +, -, (), spaces)"
        
        return True, None
    
    @staticmethod
    def validate_url(url: str, required: bool = False) -> tuple[bool, Optional[str]]:
        """Validate URL format and length."""
        if not url:
            if required:
                return False, "URL is required"
            return True, None
        
        if not isinstance(url, str):
            return False, "Invalid URL format"
        
        url = url.strip()
        
        if len(url) > InputValidator.MAX_URL_LENGTH:
            return False, f"URL cannot exceed {InputValidator.MAX_URL_LENGTH} characters"
        
        if not InputValidator.URL_PATTERN.match(url):
            return False, "Invalid URL format (must start with http:// or https://)"
        
        return True, None
    
    @staticmethod
    def validate_text_field(text: str, field_name: str, max_length: int, 
                          required: bool = False) -> tuple[bool, Optional[str]]:
        """Generic text field validation."""
        if not text:
            if required:
                return False, f"{field_name} is required"
            return True, None
        
        if not isinstance(text, str):
            return False, f"Invalid {field_name} format"
        
        text = text.strip()
        
        if required and len(text) == 0:
            return False, f"{field_name} cannot be empty"
        
        if len(text) > max_length:
            return False, f"{field_name} cannot exceed {max_length} characters"
        
        return True, None
    
    @staticmethod
    def validate_core_id(core_id: str) -> tuple[bool, Optional[str]]:
        """Validate CORE ID format."""
        if not core_id or not isinstance(core_id, str):
            return False, "CORE ID is required"
        
        core_id = core_id.strip()
        
        if len(core_id) < 3:
            return False, "CORE ID must be at least 3 characters"
        
        if len(core_id) > InputValidator.MAX_CORE_ID_LENGTH:
            return False, f"CORE ID cannot exceed {InputValidator.MAX_CORE_ID_LENGTH} characters"
        
        if not InputValidator.CORE_ID_PATTERN.match(core_id):
            return False, "CORE ID contains invalid characters (allowed: letters, numbers, hyphens)"
        
        return True, None
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize string input by stripping and truncating."""
        if not text:
            return ""
        
        text = str(text).strip()
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Truncate to max length
        return text[:max_length]


# ---------------------------------------------------------------------------
# Rate Limiting (Simple In-Memory Implementation)
# ---------------------------------------------------------------------------

class SimpleRateLimiter:
    """
    Simple in-memory rate limiter for PoC.
    For production, use Redis-backed solution (Flask-Limiter with Redis).
    """
    
    def __init__(self):
        self._attempts = {}  # IP -> [(timestamp, endpoint), ...]
        self._cleanup_interval = 300  # Clean up every 5 minutes
        self._last_cleanup = datetime.now()
    
    def is_allowed(self, identifier: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            identifier: Unique identifier (IP address, username, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = datetime.now()
        
        # Periodic cleanup
        if (now - self._last_cleanup).seconds > self._cleanup_interval:
            self._cleanup_old_attempts()
        
        # Get attempts for this identifier
        if identifier not in self._attempts:
            self._attempts[identifier] = []
        
        # Remove attempts outside the window
        cutoff = now - timedelta(seconds=window_seconds)
        self._attempts[identifier] = [
            (ts, ep) for ts, ep in self._attempts[identifier] if ts > cutoff
        ]
        
        # Check if limit exceeded
        if len(self._attempts[identifier]) >= limit:
            return False
        
        # Record this attempt
        self._attempts[identifier].append((now, request.endpoint))
        return True
    
    def _cleanup_old_attempts(self):
        """Remove old attempts to prevent memory bloat."""
        cutoff = datetime.now() - timedelta(hours=1)
        for identifier in list(self._attempts.keys()):
            self._attempts[identifier] = [
                (ts, ep) for ts, ep in self._attempts[identifier] if ts > cutoff
            ]
            if not self._attempts[identifier]:
                del self._attempts[identifier]
        
        self._last_cleanup = datetime.now()
    
    def reset(self, identifier: str):
        """Reset rate limit for an identifier (e.g., after successful login)."""
        if identifier in self._attempts:
            del self._attempts[identifier]


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


# ---------------------------------------------------------------------------
# Security Decorators
# ---------------------------------------------------------------------------

def rate_limit(limit: int = 60, window_seconds: int = 60):
    """
    Rate limiting decorator.
    
    Args:
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP address as identifier
            identifier = request.remote_addr
            
            if not rate_limiter.is_allowed(identifier, limit, window_seconds):
                # Log rate limit violation
                print(f"[SECURITY] Rate limit exceeded for {identifier} on {request.endpoint}")
                abort(429)  # Too Many Requests
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(*allowed_roles):
    """
    Authorization decorator to restrict access by role.
    
    Usage:
        @require_role('admin', 'qa')
        def some_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            if current_user.role not in allowed_roles:
                flash('Access denied. You do not have permission to access this resource.', 'danger')
                print(f"[SECURITY] Unauthorized access attempt by {current_user.username} "
                      f"(role: {current_user.role}) to {request.endpoint}")
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ---------------------------------------------------------------------------
# Security Headers Configuration
# ---------------------------------------------------------------------------

def get_security_headers():
    """
    Return security headers for HTTP responses.
    
    These headers protect against common web vulnerabilities:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME sniffing
    - Information disclosure
    """
    return {
        # Prevent XSS attacks (CSP)
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        ),
        # Prevent clickjacking
        'X-Frame-Options': 'DENY',
        # Prevent MIME sniffing
        'X-Content-Type-Options': 'nosniff',
        # Enable XSS filter in browsers
        'X-XSS-Protection': '1; mode=block',
        # Control referrer information
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        # Enforce HTTPS (for production)
        # Uncomment in production: 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        # Disable features via Permissions Policy
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }


# ---------------------------------------------------------------------------
# Configuration Validation
# ---------------------------------------------------------------------------

def validate_security_config(app):
    """
    Validate critical security configurations on app startup.
    Raises warnings or errors for insecure configurations.
    """
    issues = []
    
    # Check SECRET_KEY
    secret_key = app.config.get('SECRET_KEY', '')
    if not secret_key or secret_key == 'dev-only-secret-change-in-prod':
        issues.append("CRITICAL: SECRET_KEY is not set or using default value")
    elif len(secret_key) < 32:
        issues.append("WARNING: SECRET_KEY should be at least 32 characters")
    
    # Check database configuration
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite:///' in db_uri and app.config.get('FLASK_ENV') == 'production':
        issues.append("WARNING: Using SQLite in production (use PostgreSQL)")
    
    # Check session security
    if not app.config.get('SESSION_COOKIE_HTTPONLY', True):
        issues.append("WARNING: SESSION_COOKIE_HTTPONLY should be True")
    
    if app.config.get('SESSION_COOKIE_SECURE', False) and not app.config.get('FLASK_ENV') == 'development':
        if 'localhost' in request.host or '127.0.0.1' in request.host:
            issues.append("INFO: SESSION_COOKIE_SECURE requires HTTPS")
    
    # Check debug mode
    if app.debug and app.config.get('FLASK_ENV') == 'production':
        issues.append("CRITICAL: Debug mode enabled in production")
    
    return issues
