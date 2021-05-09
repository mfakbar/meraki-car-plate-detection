# functions related to JSON-server database
import requests
import json
from datetime import datetime, timedelta


# store car event to database
def car_to_db(url, plate, time, location):

    payload = json.dumps({
        "plate": plate,
        "time": time,
        "location": location
    })

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()


# get existing order information
def get_order(url):

    payload = {}

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return response.json()[0]


# add seconds to a date time in str
def addSeconds(timeString, second):
    dateTimeObj = datetime.strptime(timeString[:19], "%Y-%m-%dT%H:%M:%S")
    addSec = dateTimeObj + timedelta(seconds=second)
    dateTimeISO = addSec.isoformat() + 'Z'
    return dateTimeISO
