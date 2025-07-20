import os
import json
import asyncio
import aiohttp
import logging
import signal
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Load environment variables from the .env file
load_dotenv()

# Constants
VERSION = "1.0.6"
STATUS_FILE = "status.json"
CONFIG_FILE = "config.json"
RETRY_TIMEOUT = 15  # Retry timeout in seconds
REQUEST_DELAY = 2  # Delay between API requests
API_TIMEOUT = 10  # Timeout for API requests in seconds

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))  # Default to 300 seconds
VAST_URL = os.getenv("VAST_URL", "https://console.vast.ai/api/v0")

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")


class VastAIBot:
    def __init__(self):
        self.previous_status: Dict[str, Any] = {}
        self.vast_accounts: Dict[str, Any] = {}
        self.shutdown_event = asyncio.Event()

    @staticmethod
    def load_json(file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"JSON file not found: {file_path}")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in file: {file_path}")
            return {}

    @staticmethod
    def save_json(file_path: str, data: Dict[str, Any]) -> None:
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving JSON to {file_path}: {e}")

    def send_email(self, subject: str, message: str, recipients: Optional[List[str]] = None) -> None:
        """Send email notification"""
        if recipients is None:
            recipients = [EMAIL_TO] if EMAIL_TO else []
        
        if not recipients:
            logging.error("No email recipients configured")
            return

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['Subject'] = subject
            
            # Convert emoji and format message for email
            email_body = self.format_for_email(message)
            msg.attach(MIMEText(email_body, 'plain', 'utf-8'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()
            
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # Send email to each recipient
            for recipient in recipients:
                msg['To'] = recipient
                text = msg.as_string()
                server.sendmail(EMAIL_FROM, recipient, text)
                logging.info(f"Email sent to {recipient}")
                del msg['To']  # Remove for next iteration
            
            server.quit()
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")

    def format_for_email(self, message: str) -> str:
        """Format message for email (convert or remove emoji)"""
        # Simple emoji to text conversion for better email compatibility
        emoji_map = {
            '🟢': '[START]',
            '🔴': '[STOP]',
            '👤': 'Account:',
            '💰': 'Balance:',
            '🏦': 'Earnings:',
            '🖥️': 'Server:',
            '✅': '[RENTED]',
            '❌': '[FREE]',
            '🚀': '[NEW RENTAL]',
            '🛬': '[RENTAL ENDED]',
            '⚠️': '[WARNING]',
            '💵': 'Price:',
            '🎯': 'Reliability:',
            '🗄️': 'Resident:',
            '👤': 'Running:',
            '💾': 'storage',
            '🎞': 'min gpu',
            '🪫': 'min bid',
            '🚨': 'reports'
        }
        
        formatted_message = message
        for emoji, text in emoji_map.items():
            formatted_message = formatted_message.replace(emoji, text)
        
        return formatted_message

    async def call_vast_api(
        self, url: str, api_key: str, session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            async with session.get(
                url, headers=headers, timeout=API_TIMEOUT
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching {url}: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON response from {url}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {traceback.format_exc()}")
        return {}

    async def get_server_status(
        self, api_key: str, session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        data = await self.call_vast_api(f"{VAST_URL}/machines", api_key, session)
        return data.get("machines", [])

    async def get_current_user(
        self, api_key: str, session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        return await self.call_vast_api(f"{VAST_URL}/users/current", api_key, session)

    async def get_user_earnings(
        self, api_key: str, session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        return await self.call_vast_api(f"{VAST_URL}/user/earnings", api_key, session)

    async def process_account(
        self,
        account_name: str,
        account_data: Dict[str, Any],
        session: aiohttp.ClientSession,
    ) -> None:
        first_run = False if self.previous_status else True

        messages: List[str] = []
        account_lines: List[str] = []
        changes_lines: List[str] = []

        changes_detected = False

        api_key = account_data["api_key"]
        notify_emails = account_data.get("notify", [EMAIL_TO] if EMAIL_TO else [])
        server_ids = account_data["machine_ids"]

        user = await self.get_current_user(api_key, session)
        balance: float = user.get("balance", 0)

        earnings = await self.get_user_earnings(api_key, session)
        machine_earnings = earnings.get("machine_earnings", 0) or 0.0

        servers = await self.get_server_status(api_key, session)

        all_server: bool = True if -1 in server_ids else False

        for server in servers:
            server_id = str(server.get("id"))
            if not all_server and int(server_id) not in server_ids:
                continue

            listed: bool = server.get("listed", 0) or False
            running: int = server.get("current_rentals_running", 0)
            resident: int = server.get("current_rentals_resident", 0)
            rented: bool = running > 0
            reliability: float = server.get("reliability2", 0) or 0.0
            num_gpus: int = server.get("num_gpus", 0)
            earn_hour: float = server.get("earn_hour", 0) or 0.0
            earn_day: float = server.get("earn_day", 0) or 0.0
            gpu_occupancy: str = server.get("gpu_occupancy", "") or ""
            listed_gpu_cost: float = 0.0
            min_bid_price: float = 0.0
            listed_storage_cost: float = 0.0
            listed_min_gpu_count: int = 0
            num_reports: int = server.get("num_reports", "") or 0

            min_bid_price: float = server.get("min_bid_price", 0) or 0.0

            if listed:
                rented_gpus = gpu_occupancy.count("D") + gpu_occupancy.count("I")
                listed_gpu_cost = server.get("listed_gpu_cost", 0) or 0.0
                listed_storage_cost = server.get("listed_storage_cost", 0) or 0.0
                listed_min_gpu_count = server.get("listed_min_gpu_count", 0) or 0
                price_info = f"💵{listed_gpu_cost:.2f} {min_bid_price:.2f} {listed_storage_cost:.2f}"
            else:
                rented_gpus = running
                price_info = "❌ NotList ❌"

            status_str = f"✅" if rented else "❌"
            gpu_status = f"{rented_gpus}/{num_gpus}"
            reliability_info = f"🎯{reliability*100:.2f}%"
            running_info = (f"🗄️{resident}" if resident > 0 else "") + (
                f"👤{running}" if rented else ""
            )
            server_line = f"🖥️{server_id} {status_str}{gpu_status}«{listed_min_gpu_count} {price_info} {reliability_info} {running_info}\n"

            old_data = self.previous_status.get(server_id)
            if old_data is not None:
                p_listed_gpu_cost = old_data.get("listed_gpu_cost") or 0.0
                p_listed_storage_cost = old_data.get("listed_storage_cost") or 0.0
                p_rented = old_data.get("rented") or False
                p_rented_gpus = old_data.get("rented_gpus") or 0
                p_min_bid_price = old_data.get("min_bid_price") or 0.0
                p_listed_min_gpu_count = old_data.get("listed_min_gpu_count") or 0.0
                p_num_reports = old_data.get("num_reports") or 0

                p_gpu_status = f"{p_rented_gpus}/{num_gpus}"

                if p_rented != rented or p_rented_gpus != rented_gpus:
                    changes_detected = True
                    ico_status = "🚀" if p_rented_gpus < rented_gpus else "🛬"
                    changes_lines.append(
                        f"{ico_status}{server_id} {status_str} {p_gpu_status} » {rented_gpus}/{num_gpus} = {(gpu_occupancy.replace(' ', ''))}\n"
                    )

                if p_listed_gpu_cost != listed_gpu_cost:
                    changes_detected = True
                    changes_lines.append(
                        f"⚠️{server_id} 💰 price change, {p_listed_gpu_cost:.4f}$ » {listed_gpu_cost:.4f}$\n"
                    )

                if p_listed_storage_cost != listed_storage_cost:
                    changes_detected = True
                    changes_lines.append(
                        f"⚠️{server_id} 💾 price change, {p_listed_storage_cost:.4f}$ » {listed_storage_cost:.4f}$\n"
                    )

                if p_listed_min_gpu_count != listed_min_gpu_count:
                    changes_detected = True
                    changes_lines.append(
                        f"⚠️{server_id} 🎞 min gpu change, {p_listed_min_gpu_count} » {listed_min_gpu_count}\n"
                    )

                if p_min_bid_price != min_bid_price:
                    changes_detected = True
                    changes_lines.append(
                        f"⚠️{server_id} 🪫 min bid change, {p_min_bid_price} » {min_bid_price}\n"
                    )
                if p_num_reports != num_reports:
                    changes_detected = True
                    changes_lines.append(
                        f"⚠️{server_id} 🚨 num reports change, {p_num_reports} » {num_reports}\n"
                    )

            else:
                changes_detected = True

            self.previous_status[server_id] = {
                "rented": rented,
                "rented_gpus": rented_gpus,
                "listed_gpu_cost": listed_gpu_cost,
                "listed_storage_cost": listed_storage_cost,
                "min_bid_price": min_bid_price,
                "listed_min_gpu_count": listed_min_gpu_count,
                "earn_hour": earn_hour,
                "earn_day": earn_day,
                "reliability": reliability,
                "num_reports": num_reports,
                "gpu_occupancy": gpu_occupancy,
            }
            account_lines.append(server_line)

        if changes_lines:
            changes_lines.append(f"\n")

        if (first_run or changes_detected) and account_lines:
            message_body = (
                f"👤 {account_name} 💰 {balance:.2f}$ 🏦 {machine_earnings:.2f}$\n\n"
                + "".join(changes_lines)
                + "".join(account_lines)
            )
            
            subject = f"VastAI Status Update - {account_name}"
            if changes_detected and not first_run:
                if any("🚀" in line for line in changes_lines):
                    subject = f"🚀 VastAI New Rental - {account_name}"
                elif any("🛬" in line for line in changes_lines):
                    subject = f"🛬 VastAI Rental Ended - {account_name}"
                elif any("⚠️" in line for line in changes_lines):
                    subject = f"⚠️ VastAI Price Change - {account_name}"
            
            self.send_email(subject, message_body, notify_emails)
        else:
            logging.info(f"👤 {account_name} No changes detected.")

    async def monitor_servers(self) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                while not self.shutdown_event.is_set():
                    # Load the previous status and account data at each loop iteration to ensure they are up to date
                    self.previous_status = self.load_json(STATUS_FILE)
                    self.vast_accounts = self.load_json(CONFIG_FILE)

                    for account_name, account_data in self.vast_accounts.items():
                        await self.process_account(account_name, account_data, session)

                    self.save_json(STATUS_FILE, self.previous_status)

                    logging.info(
                        f"Loop completed. Next loop in {CHECK_INTERVAL} seconds."
                    )
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(), timeout=CHECK_INTERVAL
                        )
                    except asyncio.TimeoutError:
                        continue
            finally:
                await session.close()

    def handle_shutdown(self) -> None:
        logging.info("Shutdown signal received.")
        self.shutdown_event.set()

    async def main(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.handle_shutdown)

        self.send_email(f"VastAI Bot Started", f"🟢 VastAIBot v{VERSION} started successfully")
        try:
            await self.monitor_servers()
        finally:
            self.send_email(f"VastAI Bot Stopped", f"🔴 VastAIBot v{VERSION} stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    bot = VastAIBot()
    asyncio.run(bot.main())
