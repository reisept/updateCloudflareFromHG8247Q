import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import sys, getopt

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

# Load the environment variables from the .env file
load_dotenv()

def send_telegram_message(message):
    """Send notification via Telegram bot"""
    if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
        return False
    
    url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage"
    payload = {
        "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
    
    return False

def get_HG8247Q_wan_ip():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in background
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)  # or webdriver.Firefox()
    driver.get(f"http://{os.getenv('ROUTER_IP')}{os.getenv('ROUTER_LOGIN_URL')}")
    
    try:
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'txt_Username'))
        )
        
        # Fill in credentials
        driver.find_element(By.ID, 'txt_Username').send_keys(os.getenv('ROUTER_USERNAME'))
        driver.find_element(By.ID, 'txt_Password').send_keys(os.getenv('ROUTER_PASSWORD'))
        
        # Click login button
        driver.find_element(By.ID, 'loginbutton').click()
        
        # Wait for login to complete
        time.sleep(3)
        
        # Check if login was successful
        if 'index.asp' in driver.current_url:
            print("Login successful!")
            
            # Get WAN IP on status page
            driver.get(f"http://{os.getenv('ROUTER_IP')}{os.getenv('ROUTER_STATUS_URL')}")

            #print(f"status url=http://{os.getenv('ROUTER_IP')}{os.getenv('ROUTER_STATUS_URL')}")
            #print(f"status page source {driver.page_source}")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # 4. Look for public IP in the page (this part is very specific to the page HTML)
            ip_address = None
            for td in soup.find_all("td"):
                if td.text.strip().count('.') == 3:  # crude check for IPv4
                    ip_address = td.text.strip()
                    break

            if ip_address:
                print(f"Public IP: {ip_address}")
                return ip_address
            else:
                print("Could not find public IP.")
                return None
            
    except Exception as e:
        print(f"Error during login: {e}")
        return None
    finally:
        driver.quit()

def get_public_ip():
    """Get current public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        if response.status_code == 200:
            return response.json()['ip']
    except Exception as e:
        error_msg = f"Error getting public IP: {e}"
        print(error_msg)
        send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    
    # Fallback to alternative services if the primary fails
    try:
        response = requests.get('https://ident.me', timeout=10)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        error_msg = f"Error getting public IP from fallback service: {e}"
        print(error_msg)
        send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    
    return None

def get_dns_record_id():
    """Get the DNS record ID from Cloudflare"""
    url = f"https://api.cloudflare.com/client/v4/zones/{os.getenv('ZONE_ID')}/dns_records"
    headers = {
        "X-Auth-Email": os.getenv('EMAIL'),
        "X-Auth-Key": os.getenv('API_KEY'),
        "Content-Type": "application/json"
    }
    params = {
        "name": os.getenv('DNS_RECORD_NAME'),
        "type": os.getenv('DNS_RECORD_TYPE')
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['success'] and len(data['result']) > 0:
                return data['result'][0]['id']
            else:
                error_msg = f"DNS record not found for {os.getenv('DNS_RECORD_NAME')}"
                print(error_msg)
                send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    except Exception as e:
        error_msg = f"Error getting DNS record ID: {e}"
        print(error_msg)
        send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    
    return None

def update_dns_record(new_ip, record_id):
    """Update the DNS record with the new IP"""
    url = f"https://api.cloudflare.com/client/v4/zones/{os.getenv('ZONE_ID')}/dns_records/{record_id}"
    headers = {
        "X-Auth-Email": os.getenv('EMAIL'),
        "X-Auth-Key": os.getenv('API_KEY'),
        "Content-Type": "application/json"
    }
    data = {
        "type": os.getenv('DNS_RECORD_TYPE'),
        "name": os.getenv('DNS_RECORD_NAME'),
        "content": new_ip,
        "ttl": os.getenv('TTL'),
        "proxied": False  # Set to True if you use Cloudflare's proxy
    }
    
    try:
        response = requests.put(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                success_msg = f"✅ <b>DNS Update Successful</b>\n\n" \
                            f"<b>Record:</b> {os.getenv('DNS_RECORD_NAME')}\n" \
                            f"<b>New IP:</b> {new_ip}\n" \
                            f"<b>Type:</b> {os.getenv('DNS_RECORD_TYPE')}\n" \
                            f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                print(f"Successfully updated DNS record to {new_ip}")
                send_telegram_message(success_msg)
                return True
            else:
                error_msg = f"Cloudflare API error: {result['errors']}"
                print(error_msg)
                send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
        else:
            error_msg = f"API request failed with status code {response.status_code}"
            print(error_msg)
            send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    except Exception as e:
        error_msg = f"Error updating DNS record: {e}"
        print(error_msg)
        send_telegram_message(f"⚠️ <b>DNS Updater Error</b>\n{error_msg}")
    
    return False

def main():    
    startup_msg = f"🚀 <b>Cloudflare DNS Updater Started</b>\n\n" \
                f"<b>Domain:</b> {os.getenv('DNS_RECORD_NAME')}\n" \
                f"<b>Check Interval:</b> Every {int(os.getenv('CHECK_INTERVAL'))//60} minutes\n" \
                f"<b>Start Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"Starting Cloudflare DNS updater for {os.getenv('DNS_RECORD_NAME')}")
    print(f"Checking IP every {os.getenv('CHECK_INTERVAL')} seconds")
    send_telegram_message(startup_msg)
    
    current_ip = None
    record_id = get_dns_record_id()
    
    if not record_id:
        error_msg = f"❌ <b>DNS Updater Failed to Start</b>\n\n" \
                   f"Could not find DNS record for {os.getenv('DNS_RECORD_NAME')}.\n" \
                   f"Please check your Cloudflare settings."
        print(error_msg)
        send_telegram_message(error_msg)
        return
    
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Checking IP...")
        
        new_ip = get_HG8247Q_wan_ip()
        
        if new_ip and new_ip != current_ip:
            print(f"IP changed from {current_ip} to {new_ip}")
            if update_dns_record(new_ip, record_id):
                current_ip = new_ip
        elif not new_ip:
            print("Could not determine public IP address")
        else:
            print(f"IP unchanged ({current_ip})")
        
        time.sleep(int(os.getenv('CHECK_INTERVAL')))

if __name__ == "__main__":
    main()