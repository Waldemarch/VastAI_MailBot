# VastAI_MailBot
 - Email Monitoring

A Python bot that monitors your Vast.ai servers and sends email notifications about status changes, rentals, and pricing updates.

## Quick Start

1. **Install dependencies:**
   ```bash
   sudo apt install python3 python3-pip python3-venv -y
   pip3 install aiohttp python-dotenv
   ```

2. **Download and setup:**
   ```bash
   git clone <repo-url>
   cd VastAIBot
   ```

3. **Configure email (.env file):**
   ```env
   VAST_URL=https://console.vast.ai/api/v0
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_FROM=your_email@gmail.com
   EMAIL_TO=recipient@gmail.com
   CHECK_INTERVAL=300
   ```

4. **Configure accounts (config.json):**
   ```json
   {
       "MyAccount": {
           "api_key": "your_vast_api_key",
           "machine_ids": [-1],
           "notify": ["admin@example.com"]
       }
   }
   ```

5. **Run:**
   ```bash
   python3 VastAIBot_Email.py
   ```

## Gmail Setup

1. Enable 2FA in Google Account
2. Generate App Password: Google Account → Security → App passwords
3. Use the 16-character app password in `.env` file

## Getting Vast.ai API Key

1. Login to https://console.vast.ai
2. Go to Account → API Keys
3. Copy existing key or create new one

## Email Notifications

The bot sends emails with intelligent subjects:
- `🚀 VastAI New Rental - AccountName` - New server rental
- `🛬 VastAI Rental Ended - AccountName` - Rental finished
- `⚠️ VastAI Price Change - AccountName` - Price updates
- `VastAI Status Update - AccountName` - General updates

## Running as Service

Create `/etc/systemd/system/vastaibot.service`:
```ini
[Unit]
Description=VastAI Monitoring Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/VastAIBot
ExecStart=/usr/bin/python3 VastAIBot_Email.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl enable vastaibot
sudo systemctl start vastaibot
```

## Configuration

**Environment Variables (.env):**
- `SMTP_SERVER` - Email server (smtp.gmail.com, smtp-mail.outlook.com)
- `SMTP_USERNAME/PASSWORD` - Email credentials
- `CHECK_INTERVAL` - Check frequency in seconds (default: 300)

**Account Config (config.json):**
- `api_key` - Vast.ai API key
- `machine_ids` - Server IDs to monitor (`[-1]` for all)
- `notify` - Email addresses for notifications

## Supported Email Providers

| Provider | SMTP Server | Port |
|----------|-------------|------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |

## Troubleshooting

**Email issues:**
- Use App Passwords for Gmail/Yahoo (not regular password)
- Check SMTP credentials and server settings
- Verify firewall allows SMTP traffic

**API issues:**
- Verify Vast.ai API key in config.json
- Check network connectivity to Vast.ai

**Check logs:**
```bash
tail -f log/VastAIBot.log
```

## Commands

```bash
# Run in foreground
python3 VastAIBot_Email.py

# Run in background
nohup python3 VastAIBot_Email.py >> log/VastAIBot.log 2>&1 &

# Stop background process
pkill -f VastAIBot_Email.py

# Service management
sudo systemctl start/stop/restart vastaibot
sudo systemctl status vastaibot
```

## License

GNU General Public License v3.0
