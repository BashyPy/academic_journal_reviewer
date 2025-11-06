# AARIS Deployment Guide

This directory contains all Docker and deployment configurations for AARIS (Academic Agentic Review Intelligence System).

## 📁 Directory Structure

```
deployment/
├── Dockerfile                    # Backend production image
├── Dockerfile.frontend           # Frontend production image
├── docker-compose.yml            # Development environment
├── docker-compose.prod.yml       # Production environment
├── nginx.conf                    # Production Nginx config
├── nginx-frontend.conf           # Frontend container Nginx config
├── mongo-init.js                 # MongoDB initialization script
├── .dockerignore                 # Docker build exclusions
├── .env.production.example       # Production environment template
└── README.md                     # This file
```

## 🚀 Quick Start

### Development

```bash
# From project root
cd deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production

```bash
# 1. Copy and configure environment
cp .env.production.example ../.env.production
# Edit .env.production with your values

# 2. Generate SSL certificates (see SSL section below)

# 3. Start production stack
docker-compose -f docker-compose.prod.yml up -d

# 4. View logs
docker-compose -f docker-compose.prod.yml logs -f

# 5. Check health
curl http://localhost/health
```

## 🔒 SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

### Option 2: Self-Signed (Development/Testing)

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## 🔧 Configuration

### Environment Variables

**Required:**
- `MONGODB_USERNAME` - MongoDB admin username
- `MONGODB_PASSWORD` - MongoDB admin password (min 16 chars)
- `JWT_SECRET` - JWT signing secret (min 32 chars)
- At least one LLM API key (OPENAI, ANTHROPIC, GEMINI, or GROQ)

**Optional:**
- `SMTP_*` - Email configuration for OTP
- `REDIS_PASSWORD` - Redis cache password
- `SENTRY_DSN` - Error tracking

### Resource Limits

Production deployment includes resource limits:

**Backend:**
- CPU: 1-2 cores
- Memory: 2-4 GB

**Frontend:**
- CPU: 0.5 cores
- Memory: 512 MB

**MongoDB:**
- CPU: 1-2 cores
- Memory: 1-2 GB

**Redis:**
- CPU: 0.5 cores
- Memory: 512 MB

Adjust in `docker-compose.prod.yml` based on your needs.

## 📊 Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost/health

# Frontend health
curl http://localhost:3000/health

# MongoDB health
docker exec aaris-mongodb-prod mongosh --eval "db.adminCommand('ping')"

# Redis health
docker exec aaris-redis-prod redis-cli ping
```

### Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## 🔄 Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Clean old images
docker image prune -f
```

### Database Backup

```bash
# Backup MongoDB
docker exec aaris-mongodb-prod mongodump \
  --username=$MONGODB_USERNAME \
  --password=$MONGODB_PASSWORD \
  --authenticationDatabase=admin \
  --out=/data/backup

# Copy backup to host
docker cp aaris-mongodb-prod:/data/backup ./backup-$(date +%Y%m%d)
```

### Database Restore

```bash
# Copy backup to container
docker cp ./backup-20240101 aaris-mongodb-prod:/data/restore

# Restore
docker exec aaris-mongodb-prod mongorestore \
  --username=$MONGODB_USERNAME \
  --password=$MONGODB_PASSWORD \
  --authenticationDatabase=admin \
  /data/restore
```

## 🛡️ Security Checklist

- [ ] Strong passwords for MongoDB (min 16 chars)
- [ ] Strong JWT_SECRET (min 32 chars)
- [ ] SSL/TLS certificates configured
- [ ] Firewall rules configured (only 80, 443 open)
- [ ] MongoDB authentication enabled
- [ ] Redis password set
- [ ] Regular backups scheduled
- [ ] Log rotation configured
- [ ] Security headers enabled (in nginx.conf)
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] Environment variables secured (not in git)

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check container status
docker ps -a

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### Database Connection Issues

```bash
# Test MongoDB connection
docker exec aaris-mongodb-prod mongosh \
  --username=$MONGODB_USERNAME \
  --password=$MONGODB_PASSWORD \
  --authenticationDatabase=admin

# Check network
docker network inspect deployment_aaris-network
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Restart service
docker-compose -f docker-compose.prod.yml restart backend

# Adjust resource limits in docker-compose.prod.yml
```

### SSL Certificate Issues

```bash
# Verify certificate
openssl x509 -in ssl/cert.pem -text -noout

# Check certificate expiry
openssl x509 -in ssl/cert.pem -noout -dates

# Test SSL connection
openssl s_client -connect localhost:443
```

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
# In docker-compose.prod.yml
backend:
  deploy:
    replicas: 3
```

### Vertical Scaling (More Resources)

```yaml
# In docker-compose.prod.yml
backend:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
```

## 🔗 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Let's Encrypt](https://letsencrypt.org/)

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review [main README](../README.md)
- Open GitHub issue
