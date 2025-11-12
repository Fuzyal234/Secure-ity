# Secure-ity: Secure Configuration Management System

A secure, end‑to‑end system for collecting and storing sensitive configuration data. The stack is hardened to align with DoD STIG and NIST 800‑52r2 guidance.

## Architecture and Data Flow

```
Browser (React SPA)
    │  HTTPS (TLS 1.2/1.3)
    ▼
Nginx (Ingress / Reverse Proxy)
    │  Reverse proxy to backend + security headers + rate limits
    ▼
Flask Backend (API)
    │  Encrypts config data (AES‑256‑GCM)
    ▼
Supabase (PostgreSQL)
    Encrypted payload stored at rest
```

Key properties:
- Transport security at the edge (TLS 1.2/1.3, strong ciphers, HSTS, CSP)
- Application‑level encryption of configuration data before persistence (AES‑256‑GCM)
- JWT auth + RBAC for access control
- Structured audit logging with masking for sensitive metadata
- Defense‑in‑depth rate limiting (Nginx + application)

## Security Model

- Transport security:
  - `nginx/nginx.conf` enforces HTTPS, TLSv1.2/1.3, approved cipher suites, HSTS, CSP, and common hardening headers.
  - Reverse proxy forwards only required headers to the backend.
- Authentication/Authorization:
  - JWT access/refresh tokens (`HS256` by default), short‑lived access tokens.
  - Role‑based access control (RBAC) decorators gate endpoints by permission.
- Encryption at rest:
  - `app/utils/encryption.py` implements AES‑256‑GCM via `EncryptionService`.
  - Keys are provided by `app/services/key_management.py`:
    - Env provider: `KMS_DATA_KEY` or `ENCRYPTION_KEY` (base64, 32‑byte decoded).
    - Vault provider (optional): `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_SECRET_PATH`.
  - Legacy Fernet decryption is supported for backwards compatibility when needed.
- Audit logging:
  - `app/utils/logger.py` emits structured JSON logs and persists to Supabase `audit_logs`.
  - Automatic masking of common secret fields in metadata.
- Rate limiting:
  - Nginx global burst/rate rules.
  - Application rate limiting via `app/extensions.py` (in‑memory fallback).

## Backend: Files and Responsibilities

- `flask_app/app/__init__.py`
  - Flask application factory, CORS, JWT + limiter initialization, security headers middleware.
  - Registers blueprints:
    - `auth_bp` → `/api/auth`
    - `config_bp` → `/api/config`
    - `health_bp` → `/health`
- `flask_app/app/config.py`
  - Central configuration (JWT settings, logging, CORS).
  - Enforces presence of `ENCRYPTION_KEY` (or KMS) and ensures TLS for Supabase URLs.
- `flask_app/app/routes/auth_routes.py`
  - `POST /api/auth/register` — Create user (bcrypt password hash, password policy).
  - `POST /api/auth/login` — Issue access/refresh tokens, account lockout after failed attempts.
  - `POST /api/auth/logout` — Stateless logout (audit only).
  - `POST /api/auth/refresh` — Refresh access token using refresh token.
  - `GET /api/auth/me` — Current user profile.
- `flask_app/app/routes/config_routes.py`
  - `GET /api/config` — List configurations (admin: all, user: own).
  - `GET /api/config/<id>` — Get a configuration; owners receive decrypted `data`, others get encrypted payload metadata only.
  - `POST /api/config` — Create configuration: validates input, encrypts payload, persists ciphertext + metadata.
  - `PUT /api/config/<id>` — Update configuration: re‑encrypts data, bumps version.
  - `DELETE /api/config/<id>` — Soft delete.
  - `GET /api/config/audit` — Audit events (admin only).
- `flask_app/app/routes/health_routes.py`
  - `GET /health` — App/Supabase health.
- `flask_app/app/services/rbac.py`
  - `requires_permissions`, `requires_any_permission` decorators.
  - Role permission map and helpers (`has_permission`).
- `flask_app/app/services/key_management.py`
  - `KeyManagementService` facade.
  - Providers: `_EnvKeyProvider` (env), `_VaultKeyProvider` (HashiCorp Vault KV v2).
  - Caching of active keys with TTL.
- `flask_app/app/utils/encryption.py`
  - `EncryptionService.encrypt(data)` → `EncryptedPayload(ciphertext, data_hash, iv, key_version, algorithm="AES-256-GCM")`.
  - `EncryptionService.decrypt(ciphertext, expected_hash, iv, key_version, algorithm)` → `dict` data; integrity checked via SHA‑256 hash; legacy Fernet fallback supported.
  - `get_encryption_service()` singleton accessor.
- `flask_app/app/utils/logger.py`
  - `setup_logging()` structured JSON logs.
  - `log_security_event(event_type, message, severity, status, metadata, user_id, username)` logs and persists to Supabase `audit_logs` with masking and client IP/user‑agent enrichment.
- `flask_app/app/db/supabase_client.py`
  - Creates a cached Supabase client from `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_ANON_KEY`).

## Frontend: Files and Responsibilities

- `frontend/src/lib/api.ts`
  - Thin API client for the SPA.
  - Persists access/refresh tokens in localStorage; auto‑refreshes on 401 and retries original request.
  - Methods:
    - Auth: `login`, `register`, `logoutApi`, `getCurrentUser`
    - Config: `getConfigs`, `getConfig`, `createConfig`, `updateConfig`, `deleteConfig`
- UI lives under `frontend/src/components` with pages for auth and dashboard configuration CRUD.

## API Surface (Summary)

- Auth
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `POST /api/auth/refresh`
  - `GET /api/auth/me`
- Config
  - `GET /api/config`
  - `GET /api/config/<id>`
  - `POST /api/config`
  - `PUT /api/config/<id>`
  - `DELETE /api/config/<id>`
  - `GET /api/config/audit`
- Health
  - `GET /health`

## Encryption and Key Management (Detailed)

- Algorithm: AES‑256‑GCM (authenticated encryption).
- Envelope:
  - `encrypted_data`: base64url ciphertext
  - `iv`: base64url 12‑byte nonce
  - `data_hash`: SHA‑256 of plaintext JSON for integrity checks
  - `key_version`: version string returned by KMS provider
  - `encryption_algorithm`: `"AES-256-GCM"`
- Key sourcing:
  - Env provider (default): `KMS_DATA_KEY` or `ENCRYPTION_KEY` must be base64url and decode to 32 bytes; `KMS_KEY_VERSION` optional.
  - Vault provider: set `KMS_PROVIDER=vault` and configure `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_SECRET_PATH` (KV v2 supported). Fields: `key` (base64), optional `version`.
- Backwards compatibility:
  - Legacy Fernet decryption is supported when `iv`/`algorithm` are not provided; requires `ENCRYPTION_KEY`.

## Nginx (Ingress) Overview

- `nginx/nginx.conf`:
  - Redirects HTTP→HTTPS.
  - TLSv1.2/1.3 only; strong cipher suites; HSTS; CSP; X‑Frame‑Options; X‑Content‑Type‑Options; X‑XSS‑Protection.
  - Reverse proxies:
    - `/api/*` → Flask backend (`backend:5000` in Compose network).
    - `/health` and default `/` path forwarded accordingly.
  - Global request rate limiting with `limit_req_zone`.
  - Mount certs via `nginx/certs` (do not commit private keys).

## Environment Variables

Minimum required to start:
- Core
  - `SECRET_KEY` — Flask secret
  - `JWT_SECRET_KEY` — JWT signing secret (HS256)
  - `CORS_ORIGINS` — Comma‑separated list or leave empty for permissive dev CORS
- Supabase
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY` (preferred) or `SUPABASE_ANON_KEY`
- Encryption/KMS (pick one path)
  - Env provider (default): `KMS_DATA_KEY` or `ENCRYPTION_KEY` (base64url for 32‑byte key), optional `KMS_KEY_VERSION`
  - Vault provider: `KMS_PROVIDER=vault`, plus `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_SECRET_PATH`, optional `VAULT_KEY_FIELD`, `VAULT_KEY_VERSION_FIELD`
- Optional
  - `LOG_LEVEL` (default INFO)
  - `RATELIMIT_STORAGE_URL` (fallback to in‑memory if not set)

See `env.example` for a starting template.

## Run with Docker

1) Copy env and fill values:
```bash
cp .env.example .env
```

2) Start stack:
```bash
docker compose up --build -d
```

3) Access:
- App/API via Nginx: `https://localhost/`
- Health: `https://localhost/health`

Certificates:
- Mount your certs into `nginx/certs/` as `cert.pem` and `key.pem` (Compose already mounts this path). Do not commit keys.

## Local Development (Backend)

```bash
cd flask_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# required env (example)
export SECRET_KEY=dev-secret
export JWT_SECRET_KEY=dev-jwt-secret
export SUPABASE_URL="https://<your-project>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
export KMS_DATA_KEY="$(python - <<'PY'\nimport base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\nPY)"

python wsgi.py
```

Backend will be available at `http://127.0.0.1:5000` (use Nginx for TLS in front if needed).

## Project Structure

```
.
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   ├── certs/                  # TLS materials (not committed)
│   └── logs/                   # Nginx logs (not committed)
├── flask_app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── wsgi.py
│   └── app/
│       ├── __init__.py         # app factory, CORS, JWT, limiter, headers
│       ├── config.py           # runtime configuration, JWT, logging, CORS
│       ├── extensions.py       # JWT, limiter setup and callbacks
│       ├── routes/
│       │   ├── auth_routes.py
│       │   ├── config_routes.py
│       │   └── health_routes.py
│       ├── services/
│       │   ├── key_management.py
│       │   ├── rbac.py
│       │   └── security_audit.py
│       ├── utils/
│       │   ├── encryption.py
│       │   ├── logger.py
│       │   └── validation.py
│       └── db/
│           └── supabase_client.py
└── frontend/
    └── src/
        └── lib/
            └── api.ts          # frontend API client (token mgmt + refresh)
```

## Production Checklist

- Replace any self‑signed certificates with CA‑issued certs (mounted into `nginx/certs`).
- Set strong secrets and keys (`SECRET_KEY`, `JWT_SECRET_KEY`, KMS key).
- Configure `CORS_ORIGINS` appropriately.
- Ensure Vault configuration if using `KMS_PROVIDER=vault`.
- Turn on structured log collection/rotation and monitoring.
- Review Nginx security headers and CSP for your frontend assets.
- Backup strategy for Supabase data and audit logs.

## Contributing and Security

- Never commit secrets, private keys, or generated certs (`nginx/certs/`, `nginx/logs/` should be git‑ignored).
- Changes that affect authentication, encryption, or RBAC should include a brief rationale in PR description and updated docs.
- File a confidential ticket in your organization’s process for any suspected security issues.

## License

This project is provided for secure configuration management use cases. Ensure compliance with your organization’s security and data handling policies.

