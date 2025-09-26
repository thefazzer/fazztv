#!/bin/bash
# FazzTV/HCD Deployment Script for Linode

set -e

# Configuration
PROJECT_NAME="fazztv"
ENVIRONMENT="${1:-test}"
LINODE_HOST="${2}"
SSH_KEY="${3:-~/.ssh/id_rsa}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check arguments
if [ -z "$LINODE_HOST" ]; then
    log_error "Usage: $0 <environment> <linode-host> [ssh-key-path]"
    log_error "Example: $0 test 192.168.1.100 ~/.ssh/id_rsa"
    exit 1
fi

# Validate environment
if [ "$ENVIRONMENT" != "test" ] && [ "$ENVIRONMENT" != "production" ]; then
    log_error "Environment must be 'test' or 'production'"
    exit 1
fi

log_info "Deploying $PROJECT_NAME to $ENVIRONMENT environment on $LINODE_HOST"

# Check SSH connectivity
log_info "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -i "$SSH_KEY" root@"$LINODE_HOST" "echo 'SSH connection successful'"; then
    log_error "Cannot connect to $LINODE_HOST via SSH"
    exit 1
fi

# Deploy based on environment
if [ "$ENVIRONMENT" == "test" ]; then
    log_info "Deploying to TEST environment..."

    ssh -i "$SSH_KEY" root@"$LINODE_HOST" << 'ENDSSH'
        # Update system
        apt-get update
        apt-get upgrade -y

        # Install dependencies
        apt-get install -y python3.11 python3.11-venv python3-pip ffmpeg git supervisor nginx

        # Create application directory
        mkdir -p /opt/fazztv
        cd /opt/fazztv

        # Clone or update repository
        if [ -d ".git" ]; then
            # Use git-fetch-with-retry for better error handling
            if [ -f "/opt/fazztv/scripts/utils/git-fetch-with-retry.sh" ]; then
                /opt/fazztv/scripts/utils/git-fetch-with-retry.sh --remote origin --branch test
                git merge origin/test
            else
                git pull origin test
            fi
        else
            git clone -b test https://github.com/thefazzer/fazztv.git .
        fi

        # Setup Python virtual environment
        python3.11 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Create necessary directories
        mkdir -p data cache logs

        # Copy environment file
        if [ ! -f ".env" ]; then
            cp .env.test .env
        fi

        # Setup systemd service
        cat > /etc/systemd/system/fazztv.service << EOF
[Unit]
Description=FazzTV Broadcasting Service (Test)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fazztv
Environment="PATH=/opt/fazztv/venv/bin"
ExecStart=/opt/fazztv/venv/bin/python -m fazztv.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Reload and start service
        systemctl daemon-reload
        systemctl enable fazztv
        systemctl restart fazztv

        # Check service status
        sleep 5
        systemctl status fazztv --no-pager
ENDSSH

elif [ "$ENVIRONMENT" == "production" ]; then
    log_info "Deploying to PRODUCTION environment..."

    ssh -i "$SSH_KEY" root@"$LINODE_HOST" << 'ENDSSH'
        # Update system
        apt-get update
        apt-get upgrade -y

        # Install dependencies
        apt-get install -y python3.11 python3.11-venv python3-pip ffmpeg git supervisor nginx ufw

        # Setup firewall
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 1935/tcp  # RTMP port
        ufw --force enable

        # Create fazztv user
        id -u fazztv &>/dev/null || useradd -m -s /bin/bash fazztv

        # Create application directories
        mkdir -p /opt/fazztv /opt/fazztv-staging

        # Deploy to staging first
        cd /opt/fazztv-staging

        # Clone or update repository
        if [ -d ".git" ]; then
            # Use git-fetch-with-retry for better error handling
            if [ -f "/opt/fazztv-staging/scripts/utils/git-fetch-with-retry.sh" ]; then
                /opt/fazztv-staging/scripts/utils/git-fetch-with-retry.sh --remote origin --branch main
                git merge origin/main
            else
                git pull origin main
            fi
        else
            git clone https://github.com/thefazzer/fazztv.git .
        fi

        # Setup Python virtual environment
        python3.11 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Run tests
        pytest tests/
        if [ $? -ne 0 ]; then
            echo "Tests failed! Deployment aborted."
            exit 1
        fi

        # If tests pass, deploy to production
        rsync -av --delete /opt/fazztv-staging/ /opt/fazztv/
        cd /opt/fazztv

        # Create necessary directories
        mkdir -p data cache logs
        chown -R fazztv:fazztv /opt/fazztv

        # Copy production environment file
        if [ ! -f ".env" ]; then
            cp .env.prod .env
            chown fazztv:fazztv .env
            chmod 600 .env
        fi

        # Setup systemd service
        cat > /etc/systemd/system/fazztv.service << EOF
[Unit]
Description=FazzTV Broadcasting Service (Production)
After=network.target

[Service]
Type=simple
User=fazztv
Group=fazztv
WorkingDirectory=/opt/fazztv
Environment="PATH=/opt/fazztv/venv/bin"
ExecStart=/opt/fazztv/venv/bin/python -m fazztv.main
Restart=always
RestartSec=10
StandardOutput=append:/var/log/fazztv/fazztv.log
StandardError=append:/var/log/fazztv/fazztv-error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/fazztv/data /opt/fazztv/cache /var/log/fazztv

[Install]
WantedBy=multi-user.target
EOF

        # Create log directory
        mkdir -p /var/log/fazztv
        chown fazztv:fazztv /var/log/fazztv

        # Setup log rotation
        cat > /etc/logrotate.d/fazztv << EOF
/var/log/fazztv/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 fazztv fazztv
    sharedscripts
    postrotate
        systemctl reload fazztv >/dev/null 2>&1 || true
    endscript
}
EOF

        # Reload and start service
        systemctl daemon-reload
        systemctl enable fazztv
        systemctl restart fazztv

        # Setup nginx reverse proxy
        cat > /etc/nginx/sites-available/fazztv << EOF
server {
    listen 80;
    server_name _;

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        return 404;
    }
}
EOF

        ln -sf /etc/nginx/sites-available/fazztv /etc/nginx/sites-enabled/
        nginx -t && systemctl reload nginx

        # Check service status
        sleep 5
        systemctl status fazztv --no-pager
ENDSSH
fi

log_info "Deployment completed successfully!"
log_info "Checking service health..."

# Health check
if curl -f "http://$LINODE_HOST/health" 2>/dev/null; then
    log_info "Service is healthy and responding"
else
    log_warning "Service health check failed or not implemented"
fi

log_info "Deployment finished for $ENVIRONMENT environment"