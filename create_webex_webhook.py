import requests
import json
import os
from dotenv import load_dotenv

# search .env and load environment variable
load_dotenv()
NGROK_URL = os.getenv('NGROK_URL')
WEBEX_ROOM_ID = os.getenv('WEBEX_ROOM_ID')
WEBEX_TOKEN = os.getenv('WEBEX_TOKEN')

url = "https://webexapis.com/v1/webhooks"

webhook_name = "your webhook name"
secret = "optional secret key"

payload = json.dumps({
    "name": webhook_name,
    "targetUrl": NGROK_URL + "/card_action",
    "resource": "attachmentActions",
    "event": "created",
    "filter": "roomId=" + WEBEX_ROOM_ID,
    "secret": secret
})
headers = {
    'Authorization': 'Bearer ' + WEBEX_TOKEN,
    'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
