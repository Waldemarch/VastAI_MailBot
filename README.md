# VastAIBot Email Version

VastAIBot is a Python-based monitoring tool that tracks the status of your rented servers on [Vast.ai](https://vast.ai) and sends updates via email notifications. It provides real-time notifications about server status changes, pricing updates, and other relevant metrics.

## Features

- Monitors multiple Vast.ai accounts and their associated servers
- Sends real-time email notifications with intelligent subject lines
- Tracks server metrics such as rental status, GPU usage, pricing, and reliability
- Logs all activities for debugging and auditing purposes
- Automatically restarts on failure to ensure continuous monitoring
- Email-friendly formatting with emoji-to-text conversion
- Support for multiple email recipients per account

## Prerequisites

Before running VastAIBot, ensure you have the following:

1. **Python 3.8+** installed on your system
2. Required Python packages listed in `requirements.txt`
3. SMTP email server access (Gmail, Outlook, Yahoo, or custom SMTP)
4. API keys for your Vast.ai accounts

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/VastAIBot.git
   cd VastAIBot
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment variables:
   - Copy `.env.sample` to `.env`:
     ```bash
     cp .env.sample .env
     ```
   - Edit `.env` and provide the required values:
     ```env
     VAST_URL=https://console.vast.ai/api/v0
     
     # Email Configuration
     SMTP_SERVER=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USE_TLS=true
     SMTP_USERNAME=your_email@gmail.com
     SMTP_PASSWORD=your_app_password
     EMAIL_FROM=your_email@gmail.com
     EMAIL_TO=recipient@gmail.com
     
     CHECK_INTERVAL=300
     ```

4. Configure your Vast.ai accounts:
   - Copy `config.json.sample` to `config.json`:
     ```bash
     cp config.json.sample config.json
     ```
   - Edit `config.json` to include your Vast.ai API keys, machine IDs, and notification email addresses:
     ```json
     {
         "Account1": {
             "api_key": "<account1_api_key>",
             "machine_ids": [12345, 23456],
             "notify": ["admin@example.com", "monitoring@example.com"]
         },
         "Account2": {
             "api_key": "<account2_api_key>",
             "machine_ids": [987654, 876543],
             "notify": ["admin@example.com"]
         }
     }
     ```

## Email Provider Configuration

### Gmail
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

**Important:** For Gmail, you must use an "App Password" instead of your regular password. Generate one in your Google Account security settings.

### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_email@outlook.com
SMTP_PASSWORD=your_password
```

### Yahoo Mail
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_email@yahoo.com
SMTP_PASSWORD=your_app_password
```

### Custom SMTP Server
```env
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your_username
SMTP_PASSWORD=your_password
```

## Usage

### Starting the Bot

Run the Python script directly:
```bash
python3 VastAIBot_Email.py
```

### Running with Logging

```bash
mkdir -p log
python3 VastAIBot_Email.py 2>&1 | tee -a log/VastAIBot.log
```

### Running in Background

```bash
nohup python3 VastAIBot_Email.py >> log/VastAIBot.log 2>&1 &
```

### Running as a System Service

Create a systemd service file:
```bash
sudo nano /etc/systemd/system/vastaibot.service
```

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
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vastaibot
sudo systemctl start vastaibot

# Check status
sudo systemctl status vastaibot

# View logs
sudo journalctl -u vastaibot -f
```

## How It Works

1. **Configuration Loading**:
   - The bot reads environment variables from `.env`
   - Account configurations are loaded from `config.json`

2. **Monitoring Loop**:
   - Periodically fetches server status from Vast.ai API
   - Compares current status with previous state stored in `status.json`

3. **Email Notifications**:
   - Sends emails when changes are detected (server rented, price updated, etc.)
   - Uses intelligent subject lines based on the type of change:
     - `🚀 VastAI New Rental - AccountName`
     - `🛬 VastAI Rental Ended - AccountName`
     - `⚠️ VastAI Price Change - AccountName`
     - `VastAI Status Update - AccountName`

4. **Email Formatting**:
   - Converts emoji to text for better email compatibility
   - Formats messages for readability in email clients

5. **Logging**:
   - All activities are logged for debugging and auditing

## Email Message Format

The bot sends emails with the following format:

```
Subject: 🚀 VastAI New Rental - MyAccount

Account: MyAccount Balance: 123.45$ Earnings: 567.89$

[NEW RENTAL]ID123 [RENTED] 0/4 » 2/4 = DD00
[WARNING]ID123 price change, 0.1500$ » 0.2000$

Server:ID123 [RENTED]2/4«1 Price:0.20 0.15 0.05 Reliability:95.67% Running:2
Server:ID456 [FREE]0/8«2 [FREE] NotList [FREE] Reliability:98.12%
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VAST_URL` | Base URL for the Vast.ai API |
| `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | SMTP server port (587 for TLS, 465 for SSL) |
| `SMTP_USE_TLS` | Whether to use TLS encryption (true/false) |
| `SMTP_USERNAME` | SMTP authentication username |
| `SMTP_PASSWORD` | SMTP authentication password |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_TO` | Default recipient email address |
| `CHECK_INTERVAL` | Interval (in seconds) between status checks |

## Configuration File (`config.json`)

| Key | Description |
|-----|-------------|
| `api_key` | API key for the Vast.ai account |
| `machine_ids` | List of server IDs to monitor. Use `-1` for all servers |
| `notify` | List of email addresses to notify for this account |

## Getting Vast.ai API Keys

1. Log in to https://console.vast.ai
2. Go to Account → API Keys
3. Copy existing key or create a new one

## Finding Machine IDs

1. On Vast.ai go to Host → My Machines
2. IDs are visible in the "ID" column (e.g., 12345)
3. Use `-1` to monitor all machines for an account

## Logging

- Logs are stored in the `log` directory
- Main log file is `VastAIBot.log`
- Configure logrotate for log rotation:

Create `/etc/logrotate.d/vastaibot`:
```
/path/to/VastAIBot/log/*.log {
   daily
   rotate 30
   compress
   notifempty
   missingok
   copytruncate
}
```

## Troubleshooting

### Email Issues

**Emails not being sent:**
- Verify SMTP settings in `.env`
- Check email credentials and app passwords
- Ensure SMTP server allows connections from your IP
- Check firewall rules for SMTP ports

**Authentication errors:**
- For Gmail: Use App Passwords, not regular password
- For 2FA accounts: Generate app-specific passwords
- Verify username/password combination

### API Issues

**No status updates:**
- Verify Vast.ai API keys in `config.json`
- Ensure server IDs are correct
- Check network connectivity to Vast.ai

**Script crashes:**
- Check logs for stack traces: `tail -f log/VastAIBot.log`
- Ensure all dependencies are installed
- Verify Python version (3.8+ required)

### Testing

**Test email configuration:**
```bash
python3 -c "
import smtplib
from email.mime.text import MIMEText
# Add your SMTP settings here and test
"
```

**Test Vast.ai API:**
```bash
curl -H 'Authorization: Bearer YOUR_API_KEY' https://console.vast.ai/api/v0/users/current
```

## Stopping the Bot

```bash
# If running in foreground
Ctrl+C

# If running in background
pkill -f VastAIBot_Email.py

# If running as service
sudo systemctl stop vastaibot
```

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## Changelog

### v1.0.6 (Email Version)
- Replaced Telegram notifications with email notifications
- Added support for multiple email providers (Gmail, Outlook, Yahoo, custom SMTP)
- Intelligent email subject lines based on notification type
- Email-friendly message formatting with emoji-to-text conversion
- Support for multiple email recipients per account
- Improved error handling for email delivery

## Acknowledgments

- [Vast.ai](https://vast.ai) for their API
- Email providers for SMTP services
