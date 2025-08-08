#!/bin/bash

# Docker Management Script for News Recommender
# This script provides easy management of the multi-container setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if docker-compose is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
}

# Setup environment
setup() {
    log "Setting up Docker environment..."
    
    # Copy environment file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        cp env.example .env
        warning "Created .env file from template. Please edit it with your API keys."
    else
        log ".env file already exists"
    fi
    
    # Create SSL directory for nginx
    mkdir -p ssl
    
    success "Environment setup completed"
}

# Start services
start() {
    log "Starting all services..."
    docker-compose up -d
    success "Services started"
    
    # Show status
    status
}

# Stop services
stop() {
    log "Stopping all services..."
    docker-compose down
    success "Services stopped"
}

# Restart services
restart() {
    log "Restarting all services..."
    docker-compose restart
    success "Services restarted"
}

# Show status
status() {
    log "Checking service status..."
    
    echo
    echo "=== Service Status ==="
    docker-compose ps
    
    echo
    echo "=== Health Checks ==="
    
    # Check API health
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        success "API: Healthy"
    else
        error "API: Unhealthy"
    fi
    
    # Check database
    if docker-compose exec -T db pg_isready -U news_user -d news_recommender > /dev/null 2>&1; then
        success "Database: Healthy"
    else
        error "Database: Unhealthy"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        success "Redis: Healthy"
    else
        error "Redis: Unhealthy"
    fi
    
    echo
    echo "=== Resource Usage ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# View logs
logs() {
    local service=${1:-""}
    
    if [[ -n "$service" ]]; then
        log "Showing logs for $service..."
        docker-compose logs -f "$service"
    else
        log "Showing logs for all services..."
        docker-compose logs -f
    fi
}

# Run pipeline manually
run_pipeline() {
    log "Running pipeline manually..."
    docker-compose exec pipeline python pipeline/continuous_scheduler.py --run-once
}

# Check pipeline status
pipeline_status() {
    log "Checking pipeline status..."
    docker-compose exec pipeline python pipeline/monitor_pipeline.py --status
}

# Backup database
backup() {
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    log "Creating database backup: $backup_file"
    docker-compose exec -T db pg_dump -U news_user -d news_recommender > "$backup_file"
    success "Backup created: $backup_file"
}

# Restore database
restore() {
    local backup_file=${1:-""}
    
    if [[ -z "$backup_file" ]]; then
        error "Please specify backup file"
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log "Restoring database from: $backup_file"
    docker-compose exec -T db psql -U news_user -d news_recommender < "$backup_file"
    success "Database restored"
}

# Cleanup
cleanup() {
    log "Cleaning up Docker resources..."
    
    # Stop services
    docker-compose down
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    success "Cleanup completed"
}

# Full reset
reset() {
    warning "This will remove all data and containers. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "Reset cancelled"
        exit 0
    fi
    
    log "Performing full reset..."
    
    # Stop and remove everything
    docker-compose down -v --remove-orphans
    
    # Remove all containers and images
    docker system prune -a -f
    
    # Remove all volumes
    docker volume prune -f
    
    success "Full reset completed"
}

# Build services
build() {
    local service=${1:-""}
    
    if [[ -n "$service" ]]; then
        log "Building service: $service"
        docker-compose build "$service"
    else
        log "Building all services..."
        docker-compose build
    fi
    
    success "Build completed"
}

# Update services
update() {
    log "Updating services..."
    
    # Pull latest images
    docker-compose pull
    
    # Rebuild services
    docker-compose build --no-cache
    
    # Restart services
    docker-compose up -d
    
    success "Services updated"
}

# Show help
show_help() {
    cat << EOF
Docker Management Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup           Setup environment and configuration
    start           Start all services
    stop            Stop all services
    restart         Restart all services
    status          Show service status and health
    logs [service]  Show logs (all or specific service)
    build [service] Build services (all or specific)
    update          Update and rebuild all services
    run-pipeline    Run pipeline manually
    pipeline-status Check pipeline status
    backup          Create database backup
    restore <file>  Restore database from backup
    cleanup         Clean up unused Docker resources
    reset           Full reset (removes all data)
    help            Show this help message

Examples:
    $0 setup                    # Setup environment
    $0 start                    # Start all services
    $0 status                   # Check service health
    $0 logs api                 # View API logs
    $0 backup                   # Create backup
    $0 restore backup.sql       # Restore from backup

Services:
    api       - FastAPI application
    pipeline  - Article fetching pipeline
    db        - PostgreSQL database
    redis     - Redis cache
    nginx     - Reverse proxy
    monitoring - Prometheus monitoring

EOF
}

# Main script logic
case "${1:-help}" in
    setup)
        check_docker
        setup
        ;;
    start)
        check_docker
        start
        ;;
    stop)
        check_docker
        stop
        ;;
    restart)
        check_docker
        restart
        ;;
    status)
        check_docker
        status
        ;;
    logs)
        check_docker
        logs "$2"
        ;;
    build)
        check_docker
        build "$2"
        ;;
    update)
        check_docker
        update
        ;;
    run-pipeline)
        check_docker
        run_pipeline
        ;;
    pipeline-status)
        check_docker
        pipeline_status
        ;;
    backup)
        check_docker
        backup
        ;;
    restore)
        check_docker
        restore "$2"
        ;;
    cleanup)
        check_docker
        cleanup
        ;;
    reset)
        check_docker
        reset
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