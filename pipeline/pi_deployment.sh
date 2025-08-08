#!/bin/bash

# Raspberry Pi Pipeline Deployment Script
# This script sets up the continuous pipeline on a Raspberry Pi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/pi/news-recommender-backend"
SERVICE_NAME="news-pipeline"
SERVICE_FILE="/etc/systemd/system/news-pipeline.service"
LOG_DIR="/var/log/news-pipeline"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if we're on a Raspberry Pi
check_pi() {
    if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        postgresql-server-dev-all \
        build-essential \
        libpq-dev \
        git \
        supervisor \
        htop \
        nginx \
        certbot \
        python3-certbot-nginx
    
    success "System dependencies installed"
}

# Setup PostgreSQL
setup_postgresql() {
    log "Setting up PostgreSQL..."
    
    # Start PostgreSQL service
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE DATABASE news_recommender;
CREATE USER news_user WITH PASSWORD 'news_password';
GRANT ALL PRIVILEGES ON DATABASE news_recommender TO news_user;
\q
EOF
    
    # Enable pgvector extension
    sudo -u postgres psql -d news_recommender -c "CREATE EXTENSION IF NOT EXISTS vector;"
    
    success "PostgreSQL setup completed"
}

# Setup project directory
setup_project() {
    log "Setting up project directory..."
    
    # Create project directory
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Clone repository if not exists
    if [[ ! -d ".git" ]]; then
        log "Cloning repository..."
        git clone https://github.com/your-username/news-recommender-backend.git .
    else
        log "Repository already exists, pulling latest changes..."
        git pull
    fi
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    success "Project setup completed"
}

# Setup environment variables
setup_environment() {
    log "Setting up environment variables..."
    
    # Create .env file
    cat > "$PROJECT_DIR/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql://news_user:news_password@localhost:5432/news_recommender

# API Keys (you'll need to set these manually)
NEWS_API_KEY=your_news_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
EOF
    
    # Set proper permissions
    chown -R pi:pi "$PROJECT_DIR"
    chmod 600 "$PROJECT_DIR/.env"
    
    warning "Please edit $PROJECT_DIR/.env and set your API keys"
    success "Environment variables configured"
}

# Setup systemd service
setup_systemd() {
    log "Setting up systemd service..."
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    chown pi:pi "$LOG_DIR"
    
    # Create systemd service file
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=News Recommender Pipeline Scheduler
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/venv/bin/python pipeline/continuous_scheduler.py --daemon --interval-hours 12
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/pipeline.log
StandardError=append:$LOG_DIR/pipeline.error.log
SyslogIdentifier=news-pipeline

# Resource limits for Pi
MemoryMax=512M
CPUQuota=50%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $PROJECT_DIR/pipeline/logs

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    success "Systemd service configured"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring script
    cat > /usr/local/bin/monitor-pipeline << 'EOF'
#!/bin/bash
cd /home/pi/news-recommender-backend
source venv/bin/activate
python pipeline/monitor_pipeline.py "$@"
EOF
    
    chmod +x /usr/local/bin/monitor-pipeline
    
    # Create log rotation
    cat > /etc/logrotate.d/news-pipeline << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload news-pipeline
    endscript
}
EOF
    
    success "Monitoring setup completed"
}

# Setup Nginx (optional)
setup_nginx() {
    log "Setting up Nginx..."
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/news-pipeline << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/news-pipeline /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and restart Nginx
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    
    success "Nginx configured"
}

# Setup cron for maintenance
setup_cron() {
    log "Setting up maintenance cron jobs..."
    
    # Add cron jobs for maintenance
    (crontab -l 2>/dev/null; cat << 'EOF'
# Daily database backup
0 2 * * * /home/pi/news-recommender-backend/scripts/backup_db.sh

# Weekly log cleanup
0 3 * * 0 find /var/log/news-pipeline -name "*.log.*" -mtime +7 -delete

# Monthly system update
0 4 1 * * apt-get update && apt-get upgrade -y
EOF
) | crontab -
    
    success "Cron jobs configured"
}

# Create backup script
create_backup_script() {
    log "Creating backup script..."
    
    mkdir -p "$PROJECT_DIR/scripts"
    
    cat > "$PROJECT_DIR/scripts/backup_db.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/news_recommender_$DATE.sql"

mkdir -p "$BACKUP_DIR"

# Create database backup
pg_dump -h localhost -U news_user -d news_recommender > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF
    
    chmod +x "$PROJECT_DIR/scripts/backup_db.sh"
    
    success "Backup script created"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start pipeline service
    systemctl start "$SERVICE_NAME"
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Pipeline service started successfully"
    else
        error "Failed to start pipeline service"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
}

# Show status
show_status() {
    log "Checking deployment status..."
    
    echo
    echo "=== Deployment Status ==="
    echo
    
    # Check systemd service
    echo "📊 Pipeline Service:"
    systemctl status "$SERVICE_NAME" --no-pager -l
    
    echo
    echo "📈 Pipeline Health:"
    /usr/local/bin/monitor-pipeline --status
    
    echo
    echo "💾 Database Status:"
    sudo -u postgres psql -d news_recommender -c "SELECT COUNT(*) as total_articles FROM articles;"
    
    echo
    echo "🔧 System Resources:"
    free -h
    df -h /
    
    echo
    echo "📋 Useful Commands:"
    echo "  Monitor pipeline: monitor-pipeline --status"
    echo "  View logs: journalctl -u news-pipeline -f"
    echo "  Restart service: sudo systemctl restart news-pipeline"
    echo "  Check disk usage: df -h"
    echo "  Check memory: free -h"
}

# Main deployment function
deploy() {
    log "Starting Raspberry Pi deployment..."
    
    check_root
    check_pi
    
    install_dependencies
    setup_postgresql
    setup_project
    setup_environment
    setup_systemd
    setup_monitoring
    setup_nginx
    setup_cron
    create_backup_script
    start_services
    
    success "Deployment completed successfully!"
    
    show_status
}

# Help function
show_help() {
    cat << EOF
Raspberry Pi Pipeline Deployment Script

Usage: $0 [COMMAND]

Commands:
    deploy          Full deployment (recommended)
    install-deps    Install system dependencies only
    setup-db        Setup PostgreSQL only
    setup-service   Setup systemd service only
    status          Show deployment status
    help            Show this help message

Examples:
    sudo $0 deploy              # Full deployment
    sudo $0 status              # Check status
    monitor-pipeline --status   # Monitor pipeline health

Requirements:
    - Raspberry Pi (recommended)
    - Internet connection
    - sudo privileges
    - API keys for News API and OpenAI

EOF
}

# Main script logic
case "${1:-help}" in
    deploy)
        deploy
        ;;
    install-deps)
        check_root
        install_dependencies
        ;;
    setup-db)
        check_root
        setup_postgresql
        ;;
    setup-service)
        check_root
        setup_systemd
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 