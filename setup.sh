#!/bin/bash
# Setup script for Secure-ity application

set -e

echo "=========================================="
echo "Secure-ity Setup Script"
echo "=========================================="
echo ""

# Check for required tools
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Error: docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Error: docker-compose is required but not installed. Aborting." >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "Error: openssl is required but not installed. Aborting." >&2; exit 1; }
echo "✓ Prerequisites check passed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p nginx/certs
mkdir -p nginx/logs
mkdir -p flask_app/logs
echo "✓ Directories created"
echo ""

# Generate SSL certificates
echo "Generating SSL certificates..."
if [ ! -f "nginx/certs/server.crt" ] || [ ! -f "nginx/certs/server.key" ]; then
    cd nginx
    chmod +x generate_certs.sh
    ./generate_certs.sh
    cd ..
    echo "✓ SSL certificates generated"
else
    echo "✓ SSL certificates already exist"
fi
echo ""

# Generate encryption keys
echo "Generating encryption keys..."
if [ ! -f ".env" ]; then
    echo "Generating .env file from template..."
    cp env.example .env
    
    # Generate keys using Python script
    if command -v python3 >/dev/null 2>&1; then
        echo ""
        echo "Generated keys (add these to .env):"
        python3 scripts/generate_keys.py
        echo ""
        echo "Please update .env file with the generated keys above"
    else
        echo "Python3 not found. Please generate keys manually:"
        echo "  python3 scripts/generate_keys.py"
        echo "  Then update .env file with the generated values"
    fi
else
    echo "✓ .env file already exists"
fi
echo ""

# Build Docker images
echo "Building Docker images..."
docker-compose build
echo "✓ Docker images built"
echo ""

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review and update .env file with generated keys"
echo "2. Start services: docker-compose up -d"
echo "3. Check logs: docker-compose logs -f"
echo "4. Access application: https://localhost/api/"
echo "5. Default admin credentials:"
echo "   Username: admin"
echo "   Password: ChangeMe123!@#"
echo ""
echo "⚠️  IMPORTANT: Change default admin password immediately!"

