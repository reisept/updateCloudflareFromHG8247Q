# updateCloudflareFromHG8247Q
Update Cloudflare domain ip using status page from router Huawei HG8247Q

## Getting started
This script was build by me because I couldn't find a way to update my Cloudflare DNS IP address dinamically from my system. Use it, change it, do wahtever you want with it but at your own responsability.

The problem is that I have several networks and wanted to use one of them that is not the default gateway, so the only solution was try to get the public IP from the router status page.

Couldn't find any way to connect to it using ssh or telnet so the only way was to simulate a person logging in and going to WAN status page.

## Using
I'm not a Python programmer so this was made using sources from the internet, it's not pretty but it seems to work!

Need to create a .env file with all the configurations needed:
```yml
# Router configuration
ROUTER_IP="192.168.1.254"
ROUTER_USERNAME="admin"  # CHANGE_ME
ROUTER_PASSWORD="admin"  # CHANGE_ME
ROUTER_LOGIN_URL="/"
ROUTER_STATUS_URL="/html/bbsp/waninfo/waninfo.asp"

# Cloudflare API credentials
API_KEY = "12345678"   # CHANGE_ME
ZONE_ID = "12345678"   # CHANGE_ME - Go to Cloudflare your domain overview page, scroll down and should be there
EMAIL = "your.email.cloudflare@gmail.com"

# DNS record to update
DNS_RECORD_NAME = "your-domain.com"  # e.g., "home.example.com"
DNS_RECORD_TYPE = "A"  # A for IPv4, AAAA for IPv6
TTL = 1  # 1 for auto, higher values in seconds

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "12345678" # Use @BotFather in Telegram to get your token
TELEGRAM_CHAT_ID = "12345678"  # Can be channel ID or user ID

# How often to check IP (in seconds)
CHECK_INTERVAL = 300  # 5 minutes
```

Then just run it with Python3

## TODO
- Accept parameters to choose method to get public ip
- Better error handling
- Cache IP to only update if it changed
