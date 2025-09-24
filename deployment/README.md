# FazzTV/HCD Linode Deployment

This directory contains all necessary files and configurations to deploy the FazzTV/Hollow City Driver media broadcasting system to Linode infrastructure.

## Quick Start

### Prerequisites

1. **Linode Account**: Sign up at [linode.com](https://www.linode.com)
2. **Linode API Token**: Generate from [Cloud Manager](https://cloud.linode.com/profile/tokens)
3. **SSH Key Pair**: For secure server access
4. **Terraform** (optional): For infrastructure as code deployment
5. **Docker** (optional): For containerized deployment

### Deployment Methods

#### Method 1: Manual Shell Script Deployment

1. **Deploy to Test Environment**:
```bash
chmod +x deploy.sh
./deploy.sh test <linode-ip> ~/.ssh/id_rsa
```

2. **Deploy to Production Environment**:
```bash
./deploy.sh production <linode-ip> ~/.ssh/id_rsa
```

#### Method 2: Terraform Infrastructure Deployment

1. **Install Terraform**:
```bash
# macOS
brew install terraform

# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

2. **Configure Terraform**:
```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your credentials
```

3. **Deploy Infrastructure**:
```bash
terraform init
terraform plan
terraform apply
```

4. **Get Instance IPs**:
```bash
terraform output
```

#### Method 3: Docker Deployment

1. **Build and Run Locally**:
```bash
docker-compose build
docker-compose up -d
```

2. **Deploy to Linode**:
```bash
# SSH to your Linode instance
ssh root@<linode-ip>

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/thefazzer/fazztv.git
cd fazztv/deployment

# Run with Docker Compose
docker-compose up -d
```

## File Structure

```
deployment/
├── README.md                  # This file
├── deploy.sh                  # Automated deployment script
├── Dockerfile                 # Docker container definition
├── docker-compose.yml         # Docker Compose configuration
├── requirements.txt           # Python dependencies
├── .env.test                  # Test environment variables
├── .env.prod                  # Production environment variables
└── terraform/                 # Infrastructure as Code
    ├── main.tf               # Terraform configuration
    └── terraform.tfvars.example  # Example variables
```

## Environment Configuration

### Test Environment

- **Instance**: Linode 4GB (2 CPU, 4GB RAM)
- **Storage**: 100GB Block Storage
- **Cost**: ~$30/month
- **Purpose**: Development and testing

### Production Environment

- **Instance**: Linode 16GB (4 CPU, 16GB RAM)
- **Storage**: 500GB Block Storage
- **Cost**: ~$181/month
- **Purpose**: Live broadcasting

## Configuration Files

### .env Files

Copy and customize the appropriate environment file:

```bash
# For test environment
cp .env.test .env

# For production environment
cp .env.prod .env
```

**Important**: Never commit `.env` files with real API keys!

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| OPENROUTER_API_KEY | OpenRouter API key | `or-v1-xxx` |
| STREAM_KEY | YouTube stream key | `xxxx-xxxx-xxxx-xxxx` |
| DATA_DIR | Data storage directory | `/opt/fazztv/data` |
| CACHE_DIR | Cache directory | `/opt/fazztv/cache` |
| LOG_DIR | Log directory | `/var/log/fazztv` |

## Post-Deployment Tasks

### 1. Verify Installation

```bash
# Check service status
systemctl status fazztv

# View logs
journalctl -u fazztv -f

# Test health endpoint (if implemented)
curl http://<linode-ip>/health
```

### 2. Setup Monitoring

```bash
# Install Linode Longview
curl -s https://lv.linode.com/xxx | sudo bash

# Setup basic monitoring alerts
# Configure in Linode Cloud Manager
```

### 3. Configure Backups

```bash
# Enable Linode Backup Service (via Cloud Manager)
# Or setup custom backup script
crontab -e
# Add: 0 2 * * * /opt/fazztv/scripts/backup.sh
```

### 4. SSL Certificate (Production)

```bash
# Install Certbot
apt-get install certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d your-domain.com

# Auto-renewal
certbot renew --dry-run
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**:
```bash
apt-get update && apt-get install -y ffmpeg
```

2. **Permission denied**:
```bash
chown -R fazztv:fazztv /opt/fazztv
```

3. **Service won't start**:
```bash
# Check logs
journalctl -u fazztv -n 50
# Check Python path
which python3.11
# Verify virtual environment
source /opt/fazztv/venv/bin/activate
python --version
```

4. **RTMP connection failed**:
```bash
# Test RTMP connectivity
ffmpeg -re -i test.mp4 -c copy -f flv rtmp://a.rtmp.youtube.com/live2/STREAM_KEY
```

### Debug Mode

Enable debug logging by setting in `.env`:
```
LOG_LEVEL=DEBUG
```

## Maintenance

### Update Application

```bash
# Test environment
./deploy.sh test <linode-ip>

# Production (with zero downtime)
./deploy.sh production <linode-ip>
```

### Scale Resources

```bash
# Via Linode Cloud Manager or CLI
linode-cli linodes resize <linode-id> --type g6-standard-2
```

### Monitor Resources

```bash
# CPU and Memory
htop

# Disk usage
df -h

# Network
iftop

# Service logs
tail -f /var/log/fazztv/fazztv.log
```

## Security Recommendations

1. **Use SSH Keys**: Disable password authentication
2. **Configure Firewall**: Use Linode Cloud Firewall
3. **Regular Updates**: Enable unattended-upgrades
4. **Secure Secrets**: Use environment variables, never commit keys
5. **Monitor Access**: Review auth logs regularly
6. **Backup Data**: Enable Linode Backup Service

## Cost Optimization

1. **Right-size instances**: Start small, scale as needed
2. **Use Block Storage**: More cost-effective than instance storage
3. **Enable caching**: Reduce API calls and processing
4. **Monitor usage**: Set billing alerts in Cloud Manager

## Support

For deployment issues:
1. Check service logs: `journalctl -u fazztv`
2. Review this documentation
3. Contact Linode support for infrastructure issues
4. Open GitHub issue for application problems

## Next Steps

1. ✅ Choose deployment method
2. ✅ Configure environment variables
3. ✅ Deploy to test environment
4. ✅ Verify functionality
5. ✅ Deploy to production
6. ✅ Setup monitoring and backups
7. ✅ Configure domain and SSL

---

**Note**: This deployment is designed for the FazzTV/HCD media broadcasting system. Ensure all dependencies (especially FFmpeg) are properly installed for media processing capabilities.