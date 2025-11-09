# Secure-ity: Secure Configuration Management System

A secure browser-based application for collecting and storing sensitive configuration data, compliant with DoD STIG and NIST 800-52 security standards.

## 🏗️ Architecture

```
Browser UI → Nginx (TLS 1.2+) → Flask Backend → PostgreSQL/Redis
```

## 🔐 Security Features

- **Transport Security**: TLS 1.2+ with NIST 800-52r2 compliant cipher suites
- **Data Encryption**: AES-256 encryption at rest using Fernet
- **Authentication**: JWT-based authentication with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Password Security**: Bcrypt hashing with strength requirements
- **Audit Logging**: Comprehensive STIG-compliant audit logs
- **Rate Limiting**: Protection against brute force attacks
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.

## 📋 Prerequisites

- Docker and Docker Compose
- OpenSSL (for certificate generation)
- Python 3.11+ (for local development)

## 🚀 Quick Start

### 1. Configure Certificates (for production)

Place your CA-signed TLS certificate and key in the `certs/` directory:

```
certs/server.crt   # public certificate chain
certs/server.key   # private key
```

They are mounted read-only into the Nginx container at `/etc/nginx/certs`.
For local development you can leave the files absent—the container will fall back to
a self-signed certificate (you may need to trust it in your browser or disable SSL verification).

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set:
- `SECRET_KEY`: Random secret key for Flask
- `JWT_SECRET_KEY`: Random secret key for JWT tokens
- `ENCRYPTION_KEY`: Generate using:
  ```python
  from cryptography.fernet import Fernet
  print(Fernet.generate_key().decode())
  ```
- `DB_PASSWORD`: Strong database password
- `REDIS_PASSWORD`: Strong Redis password

### 3. Start Services

```bash
docker compose up --build -d
```

The Nginx container automatically generates a self-signed certificate for `localhost`
if none is provided. For production, mount CA-issued certs at `/etc/nginx/certs/server.crt`
and `/etc/nginx/certs/server.key`.

### 4. Access the Application

- **App + API via Nginx**: https://localhost/
- **API Documentation**: See API endpoints below

### 5. Default Admin User

- **Username**: `admin`
- **Password**: `ChangeMe123!@#`

**⚠️ IMPORTANT**: Change the default admin password immediately after first login!

## 📡 API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT tokens
- `POST /api/auth/logout` - Logout (blacklist token)
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

### Configuration Management

- `GET /api/config` - List configurations (paginated)
- `GET /api/config/<id>` - Get specific configuration
- `POST /api/config` - Create new configuration
- `PUT /api/config/<id>` - Update configuration
- `DELETE /api/config/<id>` - Delete configuration (soft delete)
- `GET /api/config/audit` - Get audit log (admin only)

### Health Check

- `GET /health` - Health check endpoint

## 🔒 Security Configuration

### TLS Configuration

Nginx is configured with:
- TLS 1.2 and TLS 1.3 only
- Strong cipher suites per NIST 800-52r2
- HSTS headers
- OCSP stapling

### Password Requirements

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Not a common password

### Rate Limiting

- API endpoints: 10 requests/second
- Login endpoint: 5 requests/minute
- Account lockout after 5 failed login attempts (30 minutes)

## 🧪 Testing

Run the test suite:

```bash
cd flask_app
python -m pytest ../tests/ -v
```

Or run specific test files:

```bash
python -m pytest ../tests/test_security.py -v
python -m pytest ../tests/test_routes.py -v
python -m pytest ../tests/test_logging.py -v
```

## 📊 Audit Logging

All security events are logged to:
1. **Database**: `audit_logs` table
2. **Application Logs**: `/app/logs/app.log`

Event types include:
- Authentication events (login, logout, registration)
- Configuration changes (create, update, delete)
- Access attempts (successful and failed)
- Security violations

## 🔍 Security Scanning

### Scan Docker Images

```bash
# Scan Flask app
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image secure-ity-flask_app:latest

# Scan Nginx
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image nginx:alpine
```

### Scan Python Code

```bash
cd flask_app
pip install bandit
bandit -r app/
```

### SSL/TLS Testing

```bash
# Test TLS configuration
openssl s_client -connect localhost:443 -tls1_2
```

## 📁 Project Structure

```
project-root/
├── docker-compose.yml          # Docker orchestration
├── nginx/
│   ├── nginx.conf              # Nginx configuration
│   ├── certs/                  # SSL certificates (auto-generated in dev)
│   └── entrypoint.sh           # Self-signed certificate helper
├── flask_app/
│   ├── Dockerfile              # Flask app container
│   ├── requirements.txt        # Python dependencies
│   ├── config.py              # Application configuration
│   ├── wsgi.py                # WSGI entry point
│   └── app/
│       ├── __init__.py        # Application factory
│       ├── routes/            # API routes
│       ├── models/            # Database models
│       ├── utils/             # Utilities (encryption, logging)
│       └── services/          # Business logic services
└── tests/                     # Test suite
```

## 🛠️ Development

### Local Development Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
cd flask_app
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="your-jwt-secret-key"
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
```

4. Run application:
```bash
python wsgi.py
```

## 📝 Compliance

### DoD STIG Compliance

- ✅ Application Security STIG
- ✅ Web Server STIG (Nginx)
- ✅ Database Security STIG (PostgreSQL)

### NIST 800-52r2 Compliance

- ✅ TLS 1.2+ only
- ✅ Approved cipher suites
- ✅ Certificate validation
- ✅ HSTS implementation

## ⚠️ Production Checklist

Before deploying to production:

- [ ] Replace self-signed certificates with CA-signed certificates
- [ ] Change all default passwords
- [ ] Set strong encryption keys
- [ ] Configure proper CORS origins
- [ ] Enable and configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Perform security scanning (Trivy, Bandit)
- [ ] Review and update security headers
- [ ] Configure backup strategy
- [ ] Set up SSL certificate auto-renewal
- [ ] Review firewall rules
- [ ] Document operational procedures

## 🐛 Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs flask_app
docker-compose logs nginx
```

### Database connection errors

Verify database is running:
```bash
docker-compose ps postgres
```

### Certificate errors

Regenerate certificates:
```bash
cd nginx
./generate_certs.sh
```

### Redis connection errors

Check Redis:
```bash
docker-compose exec redis redis-cli ping
```

## 📄 License

This project is designed for secure configuration management. Ensure compliance with your organization's security policies.

## 🤝 Contributing

When contributing, ensure:
- All security tests pass
- Code follows security best practices
- Documentation is updated
- No sensitive data is committed

## 📞 Support

For security issues, please follow your organization's security incident reporting procedures.

