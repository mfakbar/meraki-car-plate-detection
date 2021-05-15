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
