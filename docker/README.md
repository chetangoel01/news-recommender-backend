# Docker Multi-Container Setup

This directory contains a complete Docker setup for the news recommender system with multiple services running in containers.

## 🐳 Services Overview

- **API Service** - FastAPI application serving the news API
- **Pipeline Service** - Continuous pipeline that fetches articles every 12 hours
- **Database Service** - PostgreSQL with pgvector extension
- **Redis Service** - Caching and session management
- **Nginx Service** - Reverse proxy and load balancer
- **Monitoring Service** - Prometheus for metrics collection

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Copy environment file
cp env.example .env

# Edit with your API keys
nano .env
```

### 2. Start All Services
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Check Services
```bash
# Check service status
docker-compose ps

# Check individual service logs
docker-compose logs api
docker-compose logs pipeline
docker-compose logs db
```

## 📋 Service Details

### API Service (`api`)
- **Port**: 8000
- **Health Check**: `http://localhost:8000/health`
- **Documentation**: `http://localhost:8000/docs`
- **Resources**: 1GB RAM, 0.5 CPU

### Pipeline Service (`pipeline`)
- **Function**: Runs every 12 hours to fetch new articles
- **Resources**: 2GB RAM, 0.8 CPU
- **Logs**: `docker-compose logs pipeline`

### Database Service (`db`)
- **Port**: 5432
- **Database**: news_recommender
- **Extensions**: pgvector
- **Resources**: 1GB RAM, 0.5 CPU

### Redis Service (`redis`)
- **Port**: 6379
- **Function**: Caching and session storage
- **Resources**: 256MB RAM, 0.2 CPU

### Nginx Service (`nginx`)
- **Port**: 80, 443
- **Function**: Reverse proxy and load balancer
- **Resources**: 128MB RAM, 0.2 CPU

### Monitoring Service (`monitoring`)
- **Port**: 9090
- **Function**: Prometheus metrics collection
- **Resources**: 256MB RAM, 0.2 CPU

## 🔧 Management Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api
docker-compose up -d pipeline
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop api
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f pipeline
docker-compose logs -f db
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api
```

### Rebuild Services
```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build api
```

### Check Status
```bash
# Service status
docker-compose ps

# Service health
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

## 📊 Monitoring

### Access Points
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Prometheus**: http://localhost:9090
- **Database**: localhost:5432
- **Redis**: localhost:6379

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Check database connection
docker-compose exec db pg_isready -U news_user -d news_recommender

# Check Redis
docker-compose exec redis redis-cli ping
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
docker-compose logs service_name

# Check resource usage
docker stats

# Restart service
docker-compose restart service_name
```

#### 2. Database Connection Issues
```bash
# Check database logs
docker-compose logs db

# Test database connection
docker-compose exec db psql -U news_user -d news_recommender -c "SELECT 1;"

# Check pgvector extension
docker-compose exec db psql -U news_user -d news_recommender -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

#### 3. Pipeline Issues
```bash
# Check pipeline logs
docker-compose logs pipeline

# Run pipeline manually
docker-compose exec pipeline python pipeline/continuous_scheduler.py --run-once

# Check pipeline status
docker-compose exec pipeline python pipeline/monitor_pipeline.py --status
```

#### 4. Memory Issues
```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.yml
# Or add swap space to host system
```

### Performance Optimization

#### 1. Resource Limits
Edit `docker-compose.yml` to adjust resource limits:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
    reservations:
      memory: 512M
      cpus: '0.25'
```

#### 2. Database Tuning
The database service includes optimized PostgreSQL settings for the news recommender workload.

#### 3. Caching
Redis is included for session management and caching. Configure your application to use it.

## 🔐 Security

### Environment Variables
- Store sensitive data in `.env` file
- Never commit `.env` to version control
- Use strong passwords for database

### Network Security
- Services communicate over internal Docker network
- Only necessary ports are exposed
- Nginx provides additional security layer

### SSL/TLS
To enable HTTPS:
1. Add SSL certificates to `./ssl/` directory
2. Update nginx configuration
3. Expose port 443

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale API service
docker-compose up -d --scale api=3

# Scale with load balancer
# Update nginx configuration for multiple API instances
```

### Vertical Scaling
Edit resource limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 2G  # Increase memory
      cpus: '1.0' # Increase CPU
```

## 🗄️ Data Persistence

### Volumes
- `postgres_data`: Database data
- `redis_data`: Redis data
- `api_logs`: API logs
- `pipeline_logs`: Pipeline logs
- `pipeline_cache`: Pipeline cache
- `prometheus_data`: Monitoring data

### Backup
```bash
# Backup database
docker-compose exec db pg_dump -U news_user -d news_recommender > backup.sql

# Backup volumes
docker run --rm -v news-recommender-backend_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## 🧹 Maintenance

### Cleanup
```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a
```

### Updates
```bash
# Pull latest images
docker-compose pull

# Rebuild services
docker-compose build --no-cache

# Restart services
docker-compose up -d
```

## 📝 Configuration Files

- `docker-compose.yml` - Main orchestration file
- `Dockerfile.api` - API service container
- `Dockerfile.pipeline` - Pipeline service container
- `nginx.conf` - Nginx configuration
- `init-db.sql` - Database initialization
- `prometheus.yml` - Monitoring configuration
- `env.example` - Environment variables template

## 🆘 Support

### Log Locations
- **API logs**: `docker-compose logs api`
- **Pipeline logs**: `docker-compose logs pipeline`
- **Database logs**: `docker-compose logs db`
- **Nginx logs**: `docker-compose logs nginx`

### Getting Help
1. Check service logs first
2. Verify environment variables
3. Test individual services
4. Check resource usage
5. Review this troubleshooting guide

---

**Happy containerizing! 🐳**

For issues or questions, check the logs first and refer to this troubleshooting guide. 