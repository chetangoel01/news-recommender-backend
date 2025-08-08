#!/bin/bash

# Pipeline Management Script
# This script provides easy management of the continuous pipeline scheduler

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="news-pipeline"
SERVICE_FILE="/etc/systemd/system/news-pipeline.service"

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

# Check if running as root for systemd operations
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This operation requires root privileges"
        exit 1
    fi
}

# Check if virtual environment exists
check_venv() {
    if [[ ! -d "$PROJECT_DIR/venv" ]]; then
        error "Virtual environment not found. Please run setup first."
        exit 1
    fi
}

# Setup function
setup() {
    log "Setting up pipeline environment..."
    
    # Create logs directory
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Make scripts executable
    chmod +x "$SCRIPT_DIR/continuous_scheduler.py"
    chmod +x "$SCRIPT_DIR/monitor_pipeline.py"
    
    # Create systemd service file
    if [[ -w /etc/systemd/system ]]; then
        log "Creating systemd service file..."
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=News Recommender Pipeline Scheduler
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/venv/bin/python $SCRIPT_DIR/continuous_scheduler.py --daemon --interval-hours 12
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=news-pipeline

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$SCRIPT_DIR/logs

[Install]
WantedBy=multi-user.target
EOF
        success "Systemd service file created"
    else
        warning "Cannot write to /etc/systemd/system. Service file not created."
        warning "You may need to run this script with sudo for systemd setup."
    fi
    
    success "Pipeline setup completed"
}

# Start function
start() {
    log "Starting pipeline scheduler..."
    
    if [[ -f "$SERVICE_FILE" ]]; then
        check_root
        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
        systemctl start "$SERVICE_NAME"
        success "Pipeline service started and enabled"
    else
        warning "Systemd service file not found. Starting manually..."
        check_venv
        cd "$PROJECT_DIR"
        nohup "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/continuous_scheduler.py" --daemon --interval-hours 12 > "$SCRIPT_DIR/logs/pipeline.log" 2>&1 &
        echo $! > "$SCRIPT_DIR/pipeline.pid"
        success "Pipeline started manually (PID: $(cat "$SCRIPT_DIR/pipeline.pid"))"
    fi
}

# Stop function
stop() {
    log "Stopping pipeline scheduler..."
    
    if [[ -f "$SERVICE_FILE" ]]; then
        check_root
        systemctl stop "$SERVICE_NAME"
        systemctl disable "$SERVICE_NAME"
        success "Pipeline service stopped and disabled"
    else
        if [[ -f "$SCRIPT_DIR/pipeline.pid" ]]; then
            PID=$(cat "$SCRIPT_DIR/pipeline.pid")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                rm "$SCRIPT_DIR/pipeline.pid"
                success "Pipeline stopped (PID: $PID)"
            else
                warning "Pipeline process not running"
                rm -f "$SCRIPT_DIR/pipeline.pid"
            fi
        else
            warning "No PID file found. Pipeline may not be running."
        fi
    fi
}

# Status function
status() {
    log "Checking pipeline status..."
    
    if [[ -f "$SERVICE_FILE" ]]; then
        systemctl status "$SERVICE_NAME" --no-pager
    else
        if [[ -f "$SCRIPT_DIR/pipeline.pid" ]]; then
            PID=$(cat "$SCRIPT_DIR/pipeline.pid")
            if kill -0 "$PID" 2>/dev/null; then
                success "Pipeline is running (PID: $PID)"
                ps -p "$PID" -o pid,ppid,cmd,etime
            else
                error "Pipeline is not running (stale PID file)"
                rm -f "$SCRIPT_DIR/pipeline.pid"
            fi
        else
            warning "Pipeline is not running"
        fi
    fi
    
    # Run monitor
    echo
    log "Pipeline health check:"
    cd "$PROJECT_DIR"
    "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/monitor_pipeline.py" --status
}

# Logs function
logs() {
    log "Showing pipeline logs..."
    
    if [[ -f "$SERVICE_FILE" ]]; then
        journalctl -u "$SERVICE_NAME" -f
    else
        if [[ -f "$SCRIPT_DIR/logs/pipeline.log" ]]; then
            tail -f "$SCRIPT_DIR/logs/pipeline.log"
        else
            warning "No log file found"
        fi
    fi
}

# Run once function
run_once() {
    log "Running pipeline once..."
    check_venv
    cd "$PROJECT_DIR"
    "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/continuous_scheduler.py" --run-once
}

# Monitor function
monitor() {
    log "Running pipeline monitor..."
    check_venv
    cd "$PROJECT_DIR"
    "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/monitor_pipeline.py" "$@"
}

# Docker functions
docker_start() {
    log "Starting pipeline with Docker..."
    cd "$SCRIPT_DIR"
    docker-compose -f docker-compose.pipeline.yml up -d
    success "Pipeline started with Docker"
}

docker_stop() {
    log "Stopping pipeline Docker containers..."
    cd "$SCRIPT_DIR"
    docker-compose -f docker-compose.pipeline.yml down
    success "Pipeline Docker containers stopped"
}

docker_logs() {
    log "Showing Docker logs..."
    cd "$SCRIPT_DIR"
    docker-compose -f docker-compose.pipeline.yml logs -f news-pipeline
}

# Help function
show_help() {
    cat << EOF
Pipeline Management Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup           Setup pipeline environment and service files
    start           Start the pipeline scheduler
    stop            Stop the pipeline scheduler
    restart         Restart the pipeline scheduler
    status          Show pipeline status and health
    logs            Show pipeline logs (follow mode)
    run-once        Run pipeline once and exit
    monitor         Run pipeline monitor
    docker-start    Start pipeline with Docker
    docker-stop     Stop pipeline Docker containers
    docker-logs     Show Docker logs
    help            Show this help message

Examples:
    $0 setup                    # Setup pipeline environment
    $0 start                    # Start pipeline service
    $0 status                   # Check pipeline health
    $0 monitor --detailed       # Detailed monitoring
    $0 docker-start             # Start with Docker

Environment Variables:
    Make sure to set these environment variables:
    - DATABASE_URL
    - NEWS_API_KEY
    - OPENAI_API_KEY

EOF
}

# Main script logic
case "${1:-help}" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    run-once)
        run_once
        ;;
    monitor)
        shift
        monitor "$@"
        ;;
    docker-start)
        docker_start
        ;;
    docker-stop)
        docker_stop
        ;;
    docker-logs)
        docker_logs
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