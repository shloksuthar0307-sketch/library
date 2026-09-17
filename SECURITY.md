# Security Procedures & Documentation

This document outlines the security architecture and procedures for the Library Management System.

## Production Requirements

Before deploying this application to the internet, the following must be configured:

1. **HTTPS and SSL/TLS**
   The application strictly requires HTTPS in production. Ensure your reverse proxy (Nginx/Cloudflare) terminates SSL correctly. HSTS (HTTP Strict Transport Security) is enabled and will instruct browsers to refuse unencrypted connections.

2. **Environment Variables (.env)**
   Never hardcode credentials. Ensure the `.env` file contains:
   - `SECRET_KEY`: A cryptographically secure random string.
   - `DEBUG`: Must be omitted or explicitly set to `False`.
   - `ALLOWED_HOSTS`: Set to your production domains (comma-separated).
   - `DATABASE_URL`: Your PostgreSQL/MySQL connection string.

## Threat Protections Enabled

*   **Brute-Force Protection (`django-axes`)**: The system automatically locks out IP addresses after 5 failed login attempts. To reset a lockout, an administrator must run `python manage.py axes_reset` or unlock via the Django Admin panel.
*   **Rate Limiting (`django-ratelimit`)**: API endpoints and expensive operations (like generating PDF exports) are rate-limited per user to prevent Denial-of-Service attacks.
*   **CSV Formula Injection**: All exported CSV files sanitize strings beginning with `=`, `+`, `-`, or `@` by prepending an apostrophe.
*   **File Upload Safety**: Uploaded files (like book covers and logos) are automatically renamed to cryptographically secure UUIDs, preventing path traversal and execution of malicious files.
*   **Secure Headers & Cookies**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `X-Content-Type-Options: nosniff` are strictly enforced.

## Administrator Guidelines

*   **Two-Factor Authentication (2FA)**: We highly recommend configuring 2FA for all Superuser accounts.
*   **Secret Rotation**: If the `.env` file or `SECRET_KEY` is accidentally committed to source control, it must be rotated immediately.

## Incident Response
In the event of a suspected breach:
1. Immediately change the `SECRET_KEY` in `.env` and restart the application (this invalidates all active sessions).
2. Review the `axes` tables in the database for anomalous login attempts.
3. Review Celery task logs for unauthorized data exports.
