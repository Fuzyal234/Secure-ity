# Secure-ity — Client Functionality Overview

This document describes what the Secure-ity platform does from a client perspective, covering the web app (frontend), API (backend), and ingress (Nginx). It is written to help stakeholders understand capabilities, user flows, and security controls without needing to read source code.

## 1) What the platform does
Secure-ity is a secure configuration management system that lets teams:
- Store sensitive configuration bundles as encrypted payloads
- Control access with authentication and role-based authorization
- Track changes and access via audit logs
- Enforce strong transport, application, and data-at-rest security measures

## 2) User roles and permissions
Two roles are supported by default:
- Admin
  - Read/write/delete any configuration
  - View audit logs for the system
  - Manage users (future extensibility)
- User
  - Read/write/delete only configurations they created (own)

Plaintext access policy:
- Owners can view decrypted configuration payloads for their own items
- Admins who are not the owner see encrypted payload metadata (ciphertext and envelope), not plaintext

## 3) Web application (Frontend)
The frontend is a single-page React application that provides:

- Authentication
  - Register: Create an account with username, email, password (enforced password policy)
  - Login: Obtain access and refresh tokens; the app stores tokens locally to maintain session
  - Logout: Clears local session; backend logs the event
  - Session handling: Automatically refreshes access tokens on expiration and retries the last request

- Dashboard
  - Encrypted inventory: List of configuration bundles with version, creator, timestamps, and description
  - Create configuration: Provide a name, description, and JSON data; the backend encrypts and stores payload
  - View configuration:
    - Owners see decrypted JSON payload on demand
    - Non-owners (e.g., admins) see encrypted payload metadata only (no plaintext)
  - Update configuration: Modify name/description and/or data; versions increment automatically
  - Delete configuration: Soft deletion workflow with confirmation
  - Notifications: User-friendly success and error toasts

Navigation
- Unauthenticated users are routed to Login/Register
- Authenticated users land on the Dashboard

## 4) API (Backend) functionality
All API routes are under `/api` (except health). Authentication uses JWT access and refresh tokens.

Authentication
- POST `/api/auth/register`: Create a user (bcrypt hashing, password policy enforcement)
- POST `/api/auth/login`: Issue access and refresh tokens; failed login attempts trigger lockout after repeated failures
- POST `/api/auth/logout`: Stateless logout (event is audited)
- POST `/api/auth/refresh`: Obtain a new access token using the refresh token
- GET  `/api/auth/me`: Return the current user’s profile

Configuration management
- GET  `/api/config`: List configurations
  - Admins: all configurations
  - Users: their own configurations
- GET  `/api/config/{id}`: Get a configuration
  - Owner: receives decrypted `data`
  - Non-owner with privileges: receives encrypted payload metadata only (no plaintext)
- POST `/api/config`: Create a configuration
  - Validates JSON structure and size
  - Encrypts payload (AES‑256‑GCM) and stores ciphertext + integrity hash + IV + key version + algorithm
  - Sets version to 1
- PUT  `/api/config/{id}`: Update a configuration
  - Re-encrypts any updated `data`
  - Increments version
- DELETE `/api/config/{id}`: Soft delete a configuration
- GET  `/api/config/audit`: View audit events (admin-only)

Health
- GET `/health`: Application and database connectivity status

## 5) Security controls
Transport security (Nginx)
- TLS 1.2/1.3 enforced with strong cipher suites
- HSTS and common security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, CSP)
- Global request rate limiting to reduce abuse

Authentication and authorization
- JWT access tokens (short-lived) and refresh tokens
- Role-based access control (RBAC) decorators enforce permissions on endpoints

Data-at-rest encryption
- AES‑256‑GCM authenticated encryption
- Envelope includes: ciphertext, IV (nonce), SHA‑256 hash of plaintext, key version, algorithm
- Key management via environment or HashiCorp Vault (KV v2) with simple in-process caching
- Owner-only decryption: Owners may view plaintext; admins see metadata when not the owner

Audit logging
- Structured JSON security logs for auth and config operations
- Sensitive fields in metadata are masked before persistence
- Logs include event type, severity, status, user context, client IP, and user agent

Rate limiting
- Nginx-level global rate limiting for APIs
- Application-level rate limiting (in-memory fallback by default)

Credential and input policies
- Password policy: length, mixed character types, common-password checks
- Account lockout after repeated failed logins
- Input sanitization and payload size limits for configuration data

## 6) Ingress and routing (Nginx)
- HTTP to HTTPS redirection
- Reverse proxy to the backend service for:
  - `/api/*` → Flask API
  - `/health` and default `/` routing
- Security headers and CSP applied at the edge
- TLS certificate/key mounting supported via container volumes

## 7) Data handling lifecycle
- Create
  - Client submits JSON payload (validated for structure and size)
  - Backend encrypts payload and stores ciphertext + metadata
  - Version initialized to 1
- Read
  - Owner: backend decrypts and returns plaintext `data`
  - Non-owner admin: backend returns encryption envelope (no plaintext)
- Update
  - Modified data is re‑validated and re‑encrypted
  - Version automatically increments
- Delete
  - Soft deletion supported via API

## 8) Constraints and limits
- Stateless token revocation: tokens are not server-blacklisted; expiration and rotation are relied upon
- Configuration payload limit: up to 1 MB per bundle (enforced by validation)
- Availability of Supabase services is required for persistence and audit logging
- Default rate limits can be tuned per environment

## 9) Environment configuration (summary)
Core
- SECRET_KEY, JWT_SECRET_KEY, CORS_ORIGINS

Supabase
- SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)

Encryption / KMS
- Default (env): KMS_DATA_KEY or ENCRYPTION_KEY (base64url, decodes to 32 bytes), optional KMS_KEY_VERSION
- Vault: KMS_PROVIDER=vault, VAULT_ADDR, VAULT_TOKEN, VAULT_SECRET_PATH, optional VAULT_KEY_FIELD and VAULT_KEY_VERSION_FIELD

Optional
- LOG_LEVEL, RATELIMIT_STORAGE_URL

## 10) Glossary
- AES‑256‑GCM: Authenticated encryption algorithm providing confidentiality and integrity
- Envelope: The metadata accompanying ciphertext (IV, hash, key version, algorithm)
- IV (nonce): Initialization vector; must be unique per encryption operation
- RBAC: Role-Based Access Control, assigning permissions based on user roles
- HSTS: HTTP Strict Transport Security; instructs browsers to only use HTTPS

---
If you need additional details (e.g., API error codes, example payloads, or deployment runbooks), we can provide a companion technical appendix.


