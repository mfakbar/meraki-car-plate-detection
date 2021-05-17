# functions related to flask server process
from datetime import datetime, timedelta
import requests
import shutil
import json
import time
import meraki
import os
import io
from dotenv import load_dotenv
from google.cloud import vision
from webexteamssdk import WebexTeamsAPI


# search .env and load environment variable
load_dotenv()
MV_SHARED_KEY = os.getenv('MV_SHARED_KEY')
MV_API_KEY = os.getenv('MV_API_KEY')
DB_HOST = os.getenv('DB_HOST')
WEBEX_TOKEN = os.getenv('WEBEX_TOKEN')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# webex API instance
webexAPI = WebexTeamsAPI(access_token=WEBEX_TOKEN)

# google Vision API client instance
client = vision.ImageAnnotatorClient()
imageUrl = vision.Image()


####################################################################################
# ------------------------------------GENERAL---------------------------------------
# time string to object
def timeStrToObj(timeString):
    timeObj = datetime.strptime(timeString[:19], "%Y-%m-%dT%H:%M:%S")
    return timeObj


# add seconds to a date time in str
def addSeconds(timeString, second):
    dateTimeObj = timeStrToObj(timeString)
    addSec = dateTimeObj + timedelta(seconds=second)
    dateTimeISO = addSec.isoformat() + 'Z'
    return dateTimeISO


# filter the labels from a pre-defined label list
def filterLabels(labels, lst):
    for label in labels:
        for part in lst:
            if label == part:
                print('There is at least a relevant label in the snapshot = ', label)
                return True
    print('There is no relevant label in the snapshot')
    return False


# label detection and check
def visionFiltering(url):

    # extracting labels from snapshot url
    detectedLabel = detectLabelsURI(url)

    # filter the snapshot with labels
    labelList = ['Vehicle', 'Vehicle registration plate', 'Car']
    boolResult = filterLabels(detectedLabel, labelList)
    return boolResult


# download image and save img to local
def saveToLocal(url, filename):

    # Open the url image, set stream to True, this will return the stream content.
    r = requests.get(url, stream=True)

    # Check if the image was retrieved successfully
    if r.status_code == 200:
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        r.raw.decode_content = True

        # Open a local file with wb ( write binary ) permission.
        with open(filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

        print('Image sucessfully downloaded: ', filename)
    else:
        print('Image Couldn\'t be downloaded')


###################################################################################
# ------------------------------------MERAKI---------------------------------------
# generate snapshot and check if the url is accessible
def snapshotAndUri(deviceSerial, occurredAt, snapTime):

    # generate snapshot and perform analysis
    mvDashboard = meraki.DashboardAPI(MV_API_KEY)
    snapResponse = mvDashboard.camera.generateDeviceCameraSnapshot(
        deviceSerial, timestamp=snapTime)
    print("Snapshot url is generated = ", snapResponse,
          '\nMotion occured at = ', occurredAt,
          '\nStable snapshot taken at = ', snapTime)

    # check if the image url is accessible
    for i in range(5):
        # wait for a short time until the snapshot is available
        time.sleep(3)

        # check if snapshot is accessible
        image_response = requests.get(snapResponse['url'])

        # If HTTP code 200 (OK) is returned, quit the loop and continue
        if image_response.status_code == 200:
            break
        else:
            print(
                f"Could not access snapshot for camera {deviceSerial} right now. Wait for 3 sec.")
            continue

    return snapResponse


##################################################################################
# ------------------------------------WEBEX---------------------------------------
# post to Webex if any car plate is detected
def postToWebex_plateDetected(snapResponse, searchOrder, plate, room_id):
    if searchOrder != []:
        # notification if car plate match the order
        timeObj = timeStrToObj(searchOrder['time'])
        try:
            teams_message = '>**CUSTOMER HAS ARRIVED**\n' +\
                'Name: {}\n'.format(searchOrder['customer']) +\
                'Menu: {}\n'.format(searchOrder['menu']) +\
                'Qty: {}\n'.format(searchOrder['qty']) +\
                'Date order: {}\n'.format(timeObj) +\
                'Car plate: {}\n'.format(plate) +\
                '[Image URL]({})\n'.format(snapResponse['url'])
        except Exception as e:
            teams_message = 'There was a Webex error: Notification when car plate match the order'

    else:
        # notification if car plate does not match the order
        try:
            teams_message = '>**CAR PLATE DETECTED BUT NO ORDER MATCH**\n' +\
                'Car plate: {}\n'.format(plate) +\
                '[Image URL]({})\n'.format(snapResponse['url'])
        except Exception as e:
            teams_message = 'There was a Webex error: Notification when car plate does not match the order'

    webexAPI.messages.create(
        roomId=room_id, markdown=teams_message)


def postToWebex_noPlate(snapResponse, room_id):
    try:
        teams_message = ">**VEHICLE MOTION DETECTED BUT FAILED TO RECOGNIZE CAR PLATE**\n" +\
            '[Image URL]({})\n'.format(snapResponse['url'])
    except Exception as e:
        teams_message = 'There was a Webex error: Notification when no car plate detected'

    webexAPI.messages.create(
        roomId=room_id, markdown=teams_message)


# webex card payload
CARD_CONTENT = {
    "type": "AdaptiveCard",
    "body": [
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "items": [
                        {
                            "type": "Image",
                            "url": "Icon image url",  # parameter
                            "size": "Medium",
                            "height": "50px",
                            "backgroundColor": "White"
                        }
                    ],
                    "width": "auto"
                },
                {
                    "type": "Column",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Meraki Car Plate Detection",
                            "color": "Good",
                            "size": "Small",
                            "weight": "Lighter"
                        },
                        {
                            "type": "TextBlock",
                            "text": "CUSTOMER HAS ARRIVED",  # parameter
                            "wrap": True,
                            "color": "Accent",  # parameter
                            "size": "Medium",
                            "spacing": "Small",
                            "weight": "Bolder"
                        }
                    ],
                    "width": "stretch"
                }
            ]
        },
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": 35,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Car plate:",
                            "color": "Light"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Name:",
                            "weight": "Lighter",
                            "color": "Light",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Menu / Qty:",
                            "weight": "Lighter",
                            "color": "Light",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Date order / ID:",
                            "weight": "Lighter",
                            "color": "Light",
                            "spacing": "Small"
                        }
                    ]
                },
                {
                    "type": "Column",
                    "width": 65,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "[BMW I8]()",  # parameter
                            "color": "Light"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Bob",  # parameter
                            "color": "Light",
                            "weight": "Lighter",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Burger / 2",  # parameter
                            "weight": "Lighter",
                            "color": "Light",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "18 May 2021",  # parameter
                            "weight": "Lighter",
                            "color": "Light",
                            "spacing": "Small"
                        }
                    ]
                }
            ],
            "spacing": "Padding",
            "horizontalAlignment": "Center"
        },
        {
            "type": "Image",
            "url": "image_url"  # parameter
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Process Order",
                    "data": {
                        "orderId": "order_id",  # parameter
                        "type": "orderProcessed"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "Discard Order",
                    "data": {
                        "orderId": "order_id",  # parameter
                        "type": "orderDiscarded"
                    },
                    "style": "positive"
                }
            ],
            "spacing": "None"
        }
    ],
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.2"
}


# post webex card as notification
def postCard_plateDetected(snapResponse, searchOrder, plate, room_id):

    if searchOrder != []:
        iconUrl = "https://www.shareicon.net/data/128x128/2016/10/11/842378_multimedia_512x512.png"
        timeObj = timeStrToObj(searchOrder['time'])

        # payload parameter
        CARD_CONTENT["body"][0]["columns"][0]["items"][0]['url'] = iconUrl
        CARD_CONTENT["body"][0]["columns"][1]["items"][1]['text'] = "CUSTOMER HAS ARRIVED"
        CARD_CONTENT["body"][0]["columns"][1]["items"][1]['color'] = "Accent"
        CARD_CONTENT["body"][1]["columns"][1]["items"][0]['text'] = '[' + \
            plate + '](' + snapResponse['url'] + ')'
        CARD_CONTENT["body"][1]["columns"][1]["items"][1]['text'] = searchOrder['customer']
        CARD_CONTENT["body"][1]["columns"][1]["items"][2]['text'] = searchOrder['menu'] + \
            ' / ' + str(searchOrder['qty'])
        CARD_CONTENT["body"][1]["columns"][1]["items"][3]['text'] = timeObj.strftime(
            "%d-%b-%Y (%H:%M)") + ' / #' + str(searchOrder['id'])
        CARD_CONTENT["body"][2]["url"] = snapResponse['url']

        # input order id
        CARD_CONTENT["body"][3]["actions"][0]["data"]["orderId"] = str(
            searchOrder['id'])
        CARD_CONTENT["body"][3]["actions"][1]["data"]["orderId"] = str(
            searchOrder['id'])

        webexAPI.messages.create(
            roomId=room_id,
            text="If you see this your client cannot render cards",
            attachments=[{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": CARD_CONTENT
            }]
        )

    else:
        iconUrl = "https://findicons.com/files/icons/1671/simplicio/128/notification_warning.png"

        # payload parameter
        CARD_CONTENT["body"][0]["columns"][0]["items"][0]['url'] = iconUrl
        CARD_CONTENT["body"][0]["columns"][1]["items"][1]['text'] = "CAR PLATE DETECTED BUT NO ORDER MATCH"
        CARD_CONTENT["body"][0]["columns"][1]["items"][1]['color'] = "Attention"
        CARD_CONTENT["body"][1]["columns"][1]["items"][0][
            'text'] = '[' + plate + '](' + snapResponse['url'] + ')'
        CARD_CONTENT["body"][1]["columns"][1]["items"][1][
            'text'] = "[Check DB manually](" + DB_HOST + ")"
        CARD_CONTENT["body"][1]["columns"][1]["items"][2][
            'text'] = "[Check DB manually](" + DB_HOST + ")"
        CARD_CONTENT["body"][1]["columns"][1]["items"][3][
            'text'] = "[Check DB manually](" + DB_HOST + ")"
        CARD_CONTENT["body"][2]["url"] = snapResponse['url']

        webexAPI.messages.create(
            roomId=room_id,
            text="If you see this your client cannot render cards",
            attachments=[{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": CARD_CONTENT
            }]
        )


# post webex card as notification, if there is no plate detected
def postCard_noPlate(snapResponse, room_id):
    iconUrl = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSTPj1GNmlY8kDIjgTtZMmE-M4luNDMMRZbOQ&usqp=CAU"

    CARD_CONTENT["body"][0]["columns"][0]["items"][0]['url'] = iconUrl
    CARD_CONTENT["body"][0]["columns"][1]["items"][1]['text'] = "VEHICLE MOTION DETECTED BUT FAILED TO RECOGNIZE CAR PLATE"
    CARD_CONTENT["body"][0]["columns"][1]["items"][1]['color'] = "Warning"
    CARD_CONTENT["body"][1]["columns"][1]["items"][0][
        'text'] = "[Check DB manually](" + DB_HOST + ")"
    CARD_CONTENT["body"][1]["columns"][1]["items"][1][
        'text'] = "[Check DB manually](" + DB_HOST + ")"
    CARD_CONTENT["body"][1]["columns"][1]["items"][2][
        'text'] = "[Check DB manually](" + DB_HOST + ")"
    CARD_CONTENT["body"][1]["columns"][1]["items"][3]['text'] = "N/A"
    CARD_CONTENT["body"][2]["url"] = snapResponse['url']

    webexAPI.messages.create(
        roomId=room_id,
        text="If you see this your client cannot render cards",
        attachments=[{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": CARD_CONTENT
        }]
    )


# create webex webhook to subscribe to card action
def create_webhook(room_id, target_url):
    print("Creating new webhook..")
    webexAPI.webhooks.create(
        name="Card action: Car plate detected",
        resource="attachmentActions",
        event="created",
        filter="roomId=" + room_id,
        targetUrl=target_url
    )
    return print("Webhook created: Subscribed to card action event on roomId ", room_id)


def delete_webhooks():
    """
    List all webhooks and delete the webhooks
    """
    for webhook in webexAPI.webhooks.list():
        print("Deleting Webhook:", webhook.name, webhook.targetUrl)
        webexAPI.webhooks.delete(webhook.id)
    return print("All webhooks have been deleted")


# when card action is pressed > change serviced status in db
def respond_to_button_press(webhook_obj):
    """
    Respond to a button press on the card we posted
    """
    attachment_action = webexAPI.attachment_actions.get(webhook_obj.data.id)
    orderId = attachment_action.inputs['orderId']

    # change the serviced value in the database
    if attachment_action.inputs['type'] == "orderProcessed":
        serviced = True
        updateServicedStatus(orderId, serviced)
        print("Serviced updated: ", serviced)

    elif attachment_action.inputs['type'] == "orderDiscarded":
        serviced = False
        updateServicedStatus(orderId, serviced)
        print("Serviced updated: ", serviced)

###########################################################################################
# ------------------------------------GOOGLE VISION API------------------------------------
# detect text from image url


def detectTextURI(url):
    imageUrl.source.image_uri = url

    response = client.text_detection(image=imageUrl)
    texts = response.text_annotations

    detectedPlate = []

    for text in texts:
        if '\n' in text.description:
            detectedPlate.append(text.description.replace('\n', ''))

    if response.error.message:
        print("Car plate detection: Error")

    if detectedPlate != []:
        print("Car plate detected = ", detectedPlate)

    return detectedPlate


# detect label from image url
def detectLabelsURI(url):
    imageUrl.source.image_uri = url

    response = client.label_detection(image=imageUrl)
    labels = response.label_annotations

    detectedLabel = []

    for label in labels:
        detectedLabel.append(label.description)

    if response.error.message:
        print("Label detection: Error")

    if detectedLabel != []:
        print("Snapshot labels detected = ", detectedLabel)

    return detectedLabel


# detect image from local path
def detectTextLocal(path):

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    imageLocal = vision.Image(content=content)

    response = client.text_detection(image=imageLocal)
    texts = response.text_annotations

    detectedPlate = []

    for text in texts:
        if '\n' in text.description:
            detectedPlate.append(text.description.replace('\n', ''))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))

    if detectedPlate != []:
        print("Car plate detected = ", detectedPlate)

    return detectedPlate


# detect label from local path
def detectLabelslocal(path):

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    imageLocal = vision.Image(content=content)

    response = client.label_detection(image=imageLocal)
    labels = response.label_annotations

    detectedLabel = []

    for label in labels:
        detectedLabel.append(label.description)

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))

    if detectedLabel != []:
        print("Snapshot labels detected = ", detectedLabel)

    return detectedLabel


########################################################################################
# ------------------------------------JSON SERVER---------------------------------------
# store car event to database
def carToDB(plate, time, location):
    dbCarUrl = DB_HOST+'/car_event'

    payload = json.dumps({
        "plate": plate,
        "time": time,
        "location": location
    })

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "POST", dbCarUrl, headers=headers, data=payload)

    if response.status_code == 201:
        print('New car entry has been stored in DB = ', response.json())
    else:
        print('Could not input new car entry in DB')

    return response.json()


# get existing order information
def getOrder(plate):
    dbOrderUrl = DB_HOST+'/order'

    queryParam = '?car_plate=' + plate + \
        '&_sort=id&_order=desc&_limit=1'  # search car plate by most recent entry

    url = dbOrderUrl + queryParam

    payload = {}

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 200:
        print('The most recent order that match ',
              plate, ' plate = ', response.json())
    else:
        print('There is no order match for ', plate, ' plate')

    return response.json()[0] if response.json() != [] else response.json()


def updateServicedStatus(orderId, serviced):
    dbOrderUrl = DB_HOST+'/order/'+orderId

    payload = json.dumps({
        "serviced": serviced
    })

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "PATCH", dbOrderUrl, headers=headers, data=payload)

    if response.status_code == 200:
        print('Serviced status has been changed = ', response.json())
    else:
        print('Could not change serviced status')

    return response.json()
