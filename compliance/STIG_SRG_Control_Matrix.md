# Secure-ity STIG/SRG & NIST 800-52 Compliance Matrix

This document maps the Secure-ity application’s technical controls to the DISA Application Security and Development STIG/SRG requirements and demonstrates alignment with NIST SP 800-52 Rev.2 TLS guidance.  
Use it as a compliance artifact and keep it versioned alongside the codebase.

---

## 1. NIST SP 800-52 Rev.2 TLS Requirements

| Requirement | Description | Implementation | Evidence |
| --- | --- | --- | --- |
| TLS Versions | Servers must negotiate TLS 1.2 or TLS 1.3 only | NGINX ingress `ssl_protocols TLSv1.2 TLSv1.3;` | `nginx/nginx.conf` (lines 49-60) |
| Cipher Suites | Approved AEAD suites with forward secrecy (Tables 3-2 & 3-3) | Cipher list restricted to NIST-approved ECDHE/DHE AES-GCM or CHACHA20 suites | `nginx/nginx.conf` (lines 53-58) |
| HTTPS Enforcement | Cleartext HTTP must redirect to HTTPS | Port 80 server block returns `301 https://$host$request_uri` | `nginx/nginx.conf` (lines 40-46) |
| Session Security | HSTS, session cache, timeouts | HSTS enabled, session cache/timeouts set; modern OpenSSL provides renegotiation protection | `nginx/nginx.conf` (lines 55-65) |
| Backend TLS | Downstream services use TLS | Supabase connection URLs append `sslmode=require` | `flask_app/app/db/supabase_client.py`; `env.example` |

---

## 2. STIG/SRG Control Mapping

| Control ID | Requirement Summary | Implementation & Coverage | Evidence |
| --- | --- | --- | --- |
| SRG-APP-000014-APP-000029<br/>SRG-APP-000164-APP-000417 | Enforce FIPS-approved transport encryption | HTTPS terminated at NGINX with TLS 1.2/1.3 and NIST 800-52 cipher suites; strict headers | `nginx/nginx.conf`; Section 1 |
| SRG-APP-000015-APP-000089 | Protect sensitive data at rest using approved algorithms | AES-256-GCM encrypts configuration payloads before DB insert; per-record IV & key version | `flask_app/app/utils/encryption.py`; `flask_app/app/services/key_management.py`; `flask_app/app/routes/config_routes.py` |
| SRG-APP-000033-APP-000094 | Enforce password composition | Registration calls `validate_password` to enforce length & complexity | `flask_app/app/utils/validation.py`; `flask_app/app/routes/auth_routes.py` |
| SRG-APP-000023-APP-000279 | Validate and sanitize input | Config routes sanitize/scrub input; auth routes validate required fields; duplicate prevention | `flask_app/app/utils/validation.py`; `flask_app/app/routes/config_routes.py`; `flask_app/app/routes/auth_routes.py` |
| SRG-APP-000040-APP-000101 | Produce security/audit logs | Structured JSON logger masks secrets and writes to Supabase `audit_logs`; async-safe | `flask_app/app/utils/logger.py`; route log invocations |
| SRG-APP-000141-APP-000451 | Retain audit records securely | Audit events persisted to managed Supabase Postgres (TLS enforced); failures logged | `flask_app/app/utils/logger.py`; Supabase config |
| SRG-APP-000148-APP-000443 | Lock accounts after failed auth attempts | Login increments `failed_login_attempts` and sets `locked_until` after 5 failures | `flask_app/app/routes/auth_routes.py`; `flask_app/app/models/user.py` |
| SRG-APP-000148-APP-000454 | Provide admin review of security events | Admin-only `/api/config/audit` endpoint exposes configuration change history | `flask_app/app/routes/config_routes.py`; `flask_app/app/services/security_audit.py` |
| SRG-APP-000231-APP-000302 | Implement role-based access control | Centralized RBAC service enforces role permissions; routes require matching permissions | `flask_app/app/services/rbac.py`; `flask_app/app/routes/config_routes.py`; `flask_app/app/routes/auth_routes.py` |
| SRG-APP-000295-APP-000304 | Terminate sessions/tokens on logout | Session manager tracks active sessions in Redis, ties them to JWT claims, revokes on logout/expiry | `flask_app/app/services/session_manager.py`; `flask_app/app/routes/auth_routes.py` (`login`, `logout`, `refresh`) |
| SRG-APP-000172-APP-000437 | Secure communications with external services | Supabase & Redis connections require TLS/secure URLs via config | `flask_app/app/db/supabase_client.py`; `k8s/redis-deployment.yaml` |
| SRG-APP-000516-APP-000433 | Prevent sensitive data exposure in logs | Logger masks secret-like keys; error responses generic; metadata sanitized | `flask_app/app/utils/logger.py` (`mask_sensitive_data`) |
| SRG-APP-000206-APP-000147 | Audit configuration changes | Create/update/delete routes log change events with user metadata | `flask_app/app/routes/config_routes.py`; `flask_app/app/utils/logger.py` |
| SRG-APP-000219-APP-000151 | Handle errors without revealing internals | Routes wrap operations in try/except, respond with generic error JSON | All Flask routes (`auth_routes.py`, `config_routes.py`) |
| SRG-APP-000356-APP-000315 | Protect application secrets | Secrets stored encrypted, retrieved via Vault/env; never written to logs | `.env.example`; `k8s/secret.yaml.example`; encryption service |

---

## 3. Maintenance Notes

- Update this matrix whenever controls are added/modified.  
- Capture runtime evidence (screenshots, curl outputs, audit log extracts) before formal assessments.  
- Host/OS-level STIG controls (patching, CIS baselines, banner text, etc.) are handled outside this repo and should be documented in infrastructure compliance runbooks.

