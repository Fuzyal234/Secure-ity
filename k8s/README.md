# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying Secure-ity using Nginx Ingress Controller.

## Prerequisites

1. **Kubernetes Cluster** (v1.24+)
2. **Nginx Ingress Controller** installed
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
   ```
3. **kubectl** configured to access your cluster
4. **Docker image** built and pushed to a registry
   ```bash
   # Build image
   cd flask_app
   docker build -t secure-ity-flask:latest .
   
   # Tag and push to registry (replace with your registry)
   docker tag secure-ity-flask:latest your-registry/secure-ity-flask:v1.0.0
   docker push your-registry/secure-ity-flask:v1.0.0
   ```

## Deployment Steps

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Secrets

**IMPORTANT**: Never commit actual secrets to version control!

```bash
# Option 1: Create from file (edit secret.yaml.example first)
cp secret.yaml.example secret.yaml
# Edit secret.yaml with your actual values
kubectl apply -f secret.yaml

# Option 2: Create from command line (recommended)
kubectl create secret generic secure-ity-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=JWT_SECRET_KEY='your-jwt-secret-key' \
  --from-literal=ENCRYPTION_KEY='your-encryption-key' \
  --from-literal=DATABASE_URL='your-supabase-connection-string' \
  --from-literal=REDIS_PASSWORD='your-redis-password' \
  --namespace=secure-ity
```

### 3. Create ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Deploy Redis

```bash
kubectl apply -f redis-deployment.yaml
```

### 5. Deploy Flask Application

**Update `flask-deployment.yaml`** with your image registry:

```yaml
image: your-registry/secure-ity-flask:v1.0.0
```

Then deploy:

```bash
kubectl apply -f flask-deployment.yaml
```

### 6. Create TLS Secret for Ingress

**Option A: Using cert-manager (Recommended for production)**

Install cert-manager and create a Certificate resource:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: secure-ity-tls
  namespace: secure-ity
spec:
  secretName: secure-ity-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - secure-ity.example.com
```

**Option B: Manual TLS Secret**

```bash
kubectl create secret tls secure-ity-tls \
  --cert=path/to/certificate.crt \
  --key=path/to/private.key \
  --namespace=secure-ity
```

### 7. Configure and Deploy Ingress

**Update `ingress.yaml`**:
- Change `secure-ity.example.com` to your actual domain
- Update TLS secret name if different

```bash
kubectl apply -f ingress.yaml
```

### 8. Verify Deployment

```bash
# Check pods
kubectl get pods -n secure-ity

# Check services
kubectl get svc -n secure-ity

# Check ingress
kubectl get ingress -n secure-ity

# Check logs
kubectl logs -f deployment/secure-ity-flask -n secure-ity
```

### 9. Get Ingress IP/Domain

```bash
# Get ingress IP
kubectl get ingress secure-ity-ingress -n secure-ity

# Or if using LoadBalancer
kubectl get svc ingress-nginx-controller -n ingress-nginx
```

## Access the Application

1. **Update DNS**: Point your domain to the Ingress IP
2. **Access via HTTPS**: `https://your-domain.com`
3. **Default Admin**: 
   - Username: `admin`
   - Password: `ChangeMe123!@#`

## Production Considerations

### 1. Persistent Volumes

For production, use PersistentVolumeClaims for Redis data and logs:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: secure-ity
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### 2. Resource Limits

Adjust resource requests/limits in deployments based on your workload.

### 3. Horizontal Pod Autoscaling

```bash
kubectl autoscale deployment secure-ity-flask \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n secure-ity
```

### 4. Monitoring

Consider adding:
- Prometheus metrics
- Grafana dashboards
- Alerting rules

### 5. Backup Strategy

- Regular database backups (Supabase)
- Redis data backup
- Secret backups (store in secure vault)

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n secure-ity

# Check logs
kubectl logs <pod-name> -n secure-ity
```

### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress secure-ity-ingress -n secure-ity

# Check nginx-ingress logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

### Database Connection Issues

- Verify DATABASE_URL in secrets
- Check network policies
- Verify Supabase IP allowlist

### TLS Certificate Issues

- Verify TLS secret exists
- Check certificate expiration
- Verify domain matches certificate

## Cleanup

To remove all resources:

```bash
kubectl delete namespace secure-ity
```

Or delete individually:

```bash
kubectl delete -f ingress.yaml
kubectl delete -f flask-deployment.yaml
kubectl delete -f redis-deployment.yaml
kubectl delete -f configmap.yaml
kubectl delete -f secret.yaml
kubectl delete -f namespace.yaml
```

## Security Notes

1. **Secrets**: Never commit secrets to version control
2. **TLS**: Use cert-manager or proper CA-signed certificates
3. **Network Policies**: Consider adding network policies for isolation
4. **RBAC**: Configure proper RBAC for service accounts
5. **Pod Security**: Use Pod Security Standards
6. **Image Scanning**: Scan container images for vulnerabilities

## Support

For issues or questions, refer to:
- `SECURITY.md` - Security documentation
- `DEPLOYMENT.md` - Deployment guide
- `README.md` - General documentation

