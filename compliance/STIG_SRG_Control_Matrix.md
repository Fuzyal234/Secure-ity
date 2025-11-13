# Secure-ity STIG/SRG and NIST SP 800-52 Compliance Matrix

This document maps Secure-ity’s implemented technical controls to DISA Application Security and Development STIG/SRG requirements and aligns transport security with NIST SP 800-52 Rev.2. Keep this file versioned with the codebase and update it as controls evolve.

---

## 1. Scope and System Overview

- Application: Flask API with JWT auth, RBAC, encrypted configuration storage, and structured audit logging.
- Frontend: Vite/React UI (served via backend or separately).
- Data store: Supabase (managed Postgres) via Supabase Python client.
- Edge: NGINX handles TLS termination, security headers, and HTTPS redirection.
- Key management: Environment-backed keys or HashiCorp Vault KV v2 (optional) via `KeyManagementService`.

---

## 2. NIST SP 800-52 Rev.2 TLS Requirements

| Requirement | Description | Implementation | Evidence |
| --- | --- | --- | --- |
| TLS Versions | Only TLS 1.2 or 1.3 | NGINX `ssl_protocols TLSv1.2 TLSv1.3;` | `nginx/nginx.conf` (lines 54-60) |
| Cipher Suites | AEAD with PFS (Tables 3-2 & 3-3) | ECDHE/DHE AES-GCM and CHACHA20 suites only | `nginx/nginx.conf` (lines 57-59) |
| HTTPS Enforcement | Redirect cleartext HTTP to HTTPS | Port 80 returns `301 https://$host$request_uri` | `nginx/nginx.conf` (lines 41-46) |
| Session Security | HSTS and TLS session settings | HSTS header, session cache and timeout set | `nginx/nginx.conf` (lines 59-66) |
| External Service TLS | TLS to managed services | Supabase Python client communicates over HTTPS/TLS | `flask_app/app/db/supabase_client.py` |

Notes:
- NGINX also sets security headers including X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, and a baseline CSP. See `nginx/nginx.conf` (lines 61-68).

---

## 3. STIG/SRG Control Mapping

| Control ID | Requirement Summary | Implementation & Coverage | Evidence |
| --- | --- | --- | --- |
| SRG-APP-000014-APP-000029<br/>SRG-APP-000164-APP-000417 | Enforce FIPS-approved transport encryption | TLS 1.2/1.3 only; approved cipher suites; HSTS | `nginx/nginx.conf`; Section 2 |
| SRG-APP-000015-APP-000089 | Protect sensitive data at rest using approved algorithms | AES-256-GCM encrypts config payloads before persistence; unique IV; key version tracked | `flask_app/app/utils/encryption.py`; `flask_app/app/services/key_management.py`; `flask_app/app/routes/config_routes.py` |
| SRG-APP-000033-APP-000094 | Enforce password composition | `validate_password` enforces length and character class requirements | `flask_app/app/utils/validation.py`; `flask_app/app/routes/auth_routes.py` (`/register`) |
| SRG-APP-000023-APP-000279 | Validate and sanitize input | Input sanitation for names/descriptions; size limits; required fields | `flask_app/app/utils/validation.py`; `flask_app/app/routes/config_routes.py`; `flask_app/app/routes/auth_routes.py` |
| SRG-APP-000040-APP-000101 | Produce security/audit logs | Structured JSON audit logging with masking and persistence to Supabase | `flask_app/app/utils/logger.py`; call sites in routes |
| SRG-APP-000141-APP-000451 | Retain audit records securely | Audit events stored in Supabase (managed Postgres over TLS) | `flask_app/app/utils/logger.py`; `flask_app/app/db/supabase_client.py` |
| SRG-APP-000148-APP-000443 | Lock accounts after failed auth attempts | After 5 failed logins account is locked for 30 minutes | `flask_app/app/routes/auth_routes.py` (`/login`) |
| SRG-APP-000148-APP-000454 | Provide admin review of security events | Admin-only config audit endpoint exposes change history | `flask_app/app/routes/config_routes.py` (`/api/config/audit`); `flask_app/app/services/security_audit.py` |
| SRG-APP-000231-APP-000302 | Implement role-based access control | Centralized RBAC decorators check required permissions via JWT claims | `flask_app/app/services/rbac.py`; usage in `config_routes.py` |
| SRG-APP-000219-APP-000151 | Handle errors without revealing internals | Routes catch exceptions and return generic error messages | `flask_app/app/routes/auth_routes.py`; `flask_app/app/routes/config_routes.py` |
| SRG-APP-000516-APP-000433 | Prevent sensitive data exposure in logs | Logger masks secret-like fields and contextual metadata | `flask_app/app/utils/logger.py` (`mask_sensitive_data`) |
| SRG-APP-000206-APP-000147 | Audit configuration changes | Create/update/delete operations emit audit events with user metadata | `flask_app/app/routes/config_routes.py`; `flask_app/app/utils/logger.py` |
| SRG-APP-000356-APP-000315 | Protect application secrets | Keys via env or Vault; secrets not logged; encryption at app layer | `flask_app/app/services/key_management.py`; `.env.example` |

Not Implemented/Out of Scope (Current Build):
- Centralized session revocation/blacklisting (stateless JWT used; `/logout` is event-only). If required, introduce a token blacklist store and revoke on logout/compromise.
- Redis-backed session management (not used). `_ensure_active_session` is a no-op in `config_routes.py` indicating stateless mode.
- Kubernetes manifests referenced previously (e.g., Redis, Secrets) are not part of this repository’s current implementation.

---

## 4. Evidence Index (Quick Links)

- Transport Security and Headers: `nginx/nginx.conf`
- Key Management and Encryption: `flask_app/app/services/key_management.py`, `flask_app/app/utils/encryption.py`
- Authentication and Lockout: `flask_app/app/routes/auth_routes.py`, `flask_app/app/utils/validation.py`
- RBAC Enforcement: `flask_app/app/services/rbac.py`
- Audit Logging and Reports: `flask_app/app/utils/logger.py`, `flask_app/app/services/security_audit.py`
- Supabase Client (TLS-backed): `flask_app/app/db/supabase_client.py`

---

## 5. Maintenance Notes

- Update this matrix whenever controls are added or modified.
- Capture runtime evidence (e.g., screenshots, curl outputs, log extracts) prior to formal assessments.
- Host/OS-level STIG controls (patching, CIS baselines, banners, etc.) are managed outside this repo; document them in infrastructure compliance runbooks.

