# Raspberry Pi Pipeline Deployment Guide

This guide will help you set up the continuous news pipeline on a Raspberry Pi to automatically fetch and process new articles every 12 hours.

## 🍓 Prerequisites

### Hardware Requirements
- **Raspberry Pi 4** (recommended) or Pi 3B+
- **4GB RAM** minimum (8GB recommended)
- **32GB+ SD card** (Class 10 or better)
- **Stable internet connection**
- **Power supply** (5V/3A recommended)

### Software Requirements
- **Raspberry Pi OS** (Bullseye or newer)
- **Python 3.11+**
- **PostgreSQL 13+**
- **Git**

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/news-recommender-backend.git
   cd news-recommender-backend
   ```

2. **Run the deployment script:**
   ```bash
   sudo chmod +x pipeline/pi_deployment.sh
   sudo ./pipeline/pi_deployment.sh deploy
   ```

3. **Set your API keys:**
   ```bash
   sudo nano /home/pi/news-recommender-backend/.env
   ```
   Edit the file and add your API keys:
   ```
   NEWS_API_KEY=your_news_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Restart the service:**
   ```bash
   sudo systemctl restart news-pipeline
   ```

### Option 2: Docker Deployment

1. **Install Docker and Docker Compose:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. **Create environment file:**
   ```bash
   cp pipeline/.env.example pipeline/.env
   nano pipeline/.env
   ```

3. **Start the services:**
   ```bash
   cd pipeline
   docker-compose -f docker-compose.pi.yml up -d
   ```

## 📋 Manual Setup (Step by Step)

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git htop

# Enable SSH (optional)
sudo raspi-config
# Navigate to: Interface Options > SSH > Enable
```

### 2. Database Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE news_recommender;
CREATE USER news_user WITH PASSWORD 'news_password';
GRANT ALL PRIVILEGES ON DATABASE news_recommender TO news_user;
\q
EOF

# Enable pgvector extension
sudo -u postgres psql -d news_recommender -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Application Setup

```bash
# Clone repository
cd /home/pi
git clone https://github.com/your-username/news-recommender-backend.git
cd news-recommender-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Create environment file
cat > .env << EOF
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_recommender
NEWS_API_KEY=your_news_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
LOG_LEVEL=INFO
ENVIRONMENT=production
EOF

# Set permissions
chmod 600 .env
```

### 5. Service Setup

```bash
# Create systemd service
sudo tee /etc/systemd/system/news-pipeline.service > /dev/null << EOF
[Unit]
Description=News Recommender Pipeline Scheduler
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/news-recommender-backend
Environment=PYTHONPATH=/home/pi/news-recommender-backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/news-recommender-backend/venv/bin/python pipeline/continuous_scheduler.py --daemon --interval-hours 12
Restart=always
RestartSec=10
StandardOutput=append:/var/log/news-pipeline/pipeline.log
StandardError=append:/var/log/news-pipeline/pipeline.error.log
SyslogIdentifier=news-pipeline

# Resource limits for Pi
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/news-pipeline
sudo chown pi:pi /var/log/news-pipeline

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable news-pipeline
sudo systemctl start news-pipeline
```

## 🔧 Monitoring and Management

### Check Service Status
```bash
# Service status
sudo systemctl status news-pipeline

# View logs
sudo journalctl -u news-pipeline -f

# Pipeline health
monitor-pipeline --status
```

### Useful Commands
```bash
# Restart pipeline
sudo systemctl restart news-pipeline

# Stop pipeline
sudo systemctl stop news-pipeline

# View detailed logs
tail -f /var/log/news-pipeline/pipeline.log

# Check system resources
htop
free -h
df -h
```

### Database Management
```bash
# Backup database
pg_dump -h localhost -U news_user -d news_recommender > backup.sql

# Restore database
psql -h localhost -U news_user -d news_recommender < backup.sql

# Check database size
sudo -u postgres psql -d news_recommender -c "SELECT pg_size_pretty(pg_database_size('news_recommender'));"
```

## 🐳 Docker Deployment

### Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose
```

### Deploy with Docker
```bash
cd pipeline

# Create environment file
cp .env.example .env
nano .env  # Add your API keys

# Start services
docker-compose -f docker-compose.pi.yml up -d

# Check logs
docker-compose -f docker-compose.pi.yml logs -f news-pipeline
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check service status
sudo systemctl status news-pipeline

# View error logs
sudo journalctl -u news-pipeline -n 50

# Check if dependencies are installed
python3 -c "import psycopg2, sentence_transformers"
```

#### 2. Database Connection Issues
```bash
# Test database connection
psql -h localhost -U news_user -d news_recommender -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### 3. Memory Issues
```bash
# Check memory usage
free -h

# Check swap
swapon --show

# Add swap if needed
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Disk Space Issues
```bash
# Check disk usage
df -h

# Clean up old logs
sudo find /var/log/news-pipeline -name "*.log.*" -mtime +7 -delete

# Clean up Docker (if using)
docker system prune -a
```

### Performance Optimization

#### 1. System Tuning
```bash
# Add to /boot/config.txt
echo "gpu_mem=128" | sudo tee -a /boot/config.txt
echo "over_voltage=2" | sudo tee -a /boot/config.txt
echo "arm_freq=1750" | sudo tee -a /boot/config.txt
```

#### 2. PostgreSQL Tuning
```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/*/main/postgresql.conf

# Add these settings:
shared_buffers = 64MB
effective_cache_size = 128MB
maintenance_work_mem = 16MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
```

## 📊 Monitoring Dashboard

### Create a Simple Dashboard
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Create monitoring script
cat > /home/pi/monitor.sh << 'EOF'
#!/bin/bash
echo "=== System Status ==="
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2{print $5}')"
echo "Temperature: $(vcgencmd measure_temp)"
echo
echo "=== Pipeline Status ==="
monitor-pipeline --status
EOF

chmod +x /home/pi/monitor.sh
```

## 🔐 Security Considerations

### 1. Firewall Setup
```bash
# Install UFW
sudo apt install -y ufw

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL Certificate (Optional)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 📈 Performance Monitoring

### Resource Usage
- **CPU**: Should stay below 80% during pipeline runs
- **Memory**: Keep at least 1GB free
- **Disk**: Monitor `/var/log` and database growth
- **Network**: Check API rate limits

### Optimization Tips
1. **Schedule pipeline runs** during low-usage hours
2. **Use SSD** for better I/O performance
3. **Monitor temperature** - keep Pi below 70°C
4. **Regular backups** of database and logs
5. **Update system** monthly for security patches

## 🆘 Support

### Log Locations
- **Service logs**: `/var/log/news-pipeline/`
- **System logs**: `journalctl -u news-pipeline`
- **Database logs**: `/var/log/postgresql/`
- **Application logs**: `pipeline/logs/`

### Getting Help
1. Check the logs first
2. Verify API keys are correct
3. Test database connectivity
4. Check system resources
5. Review this troubleshooting guide

## 📝 Maintenance Schedule

### Daily
- Check service status: `sudo systemctl status news-pipeline`
- Monitor logs: `tail -f /var/log/news-pipeline/pipeline.log`

### Weekly
- Backup database: `pg_dump -h localhost -U news_user -d news_recommender > backup.sql`
- Clean old logs: `find /var/log/news-pipeline -name "*.log.*" -mtime +7 -delete`
- Check disk usage: `df -h`

### Monthly
- System updates: `sudo apt update && sudo apt upgrade`
- Review performance metrics
- Check for security updates

---

**Happy deploying! 🚀**

For issues or questions, check the logs first and refer to this troubleshooting guide. 