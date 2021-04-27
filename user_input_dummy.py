# When the user make an order from app > post JSON payload to JSON server DB

import requests
import json
import os
from dotenv import load_dotenv

# search .env and load environment variable
load_dotenv()
DB_HOST = os.getenv('DB_HOST')

url = DB_HOST+"/order"

payload = json.dumps({
    "customer": "Bob",
    "menu": "Fries",
    "qty": 3,
    "car_plate": "MY70 BMW",
    "time": "2021-04-23T08:09:46Z"
})
headers = {
    'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
