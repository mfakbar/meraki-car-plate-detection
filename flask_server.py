# Flask server as webhook receiver > then triggers a series of scripts

from flask import Flask, request, Response, json
import meraki
import time
import os
from dotenv import load_dotenv
from db_functions import *
from plate_detection_functions import *
from webexteamssdk import WebexTeamsAPI


# search .env file and load environment variable
load_dotenv()
MV_SHARED_KEY = os.getenv('MV_SHARED_KEY')
MV_API_KEY = os.getenv('MV_API_KEY')
DB_HOST = os.getenv('DB_HOST')
WEBEX_TOKEN = os.getenv('WEBEX_TOKEN')

# database url address
dbCarUrl = DB_HOST+'/car_event'
dbOrderUrl = DB_HOST+'/order'

# webex destination
webexTo = 'Y2lzY29zcGFyazovL3VzL1JPT00vYWIxYjczMTAtOTFmNS0xMWViLWFiNDctZDc2MTU5NmE4ZGE4'

# boolean for filtering webhooks
runScript = True
waitTime = 10  # seconds
intervalTime = 2  # seconds

# Flask server setup
app = Flask(__name__)


# take a snapshot and return the snapshot resonponse
def SnapshotAndUri(deviceSerial, occurredAt, snapTime):
    # generate snapshot and perform analysis
    mvDashboard = meraki.DashboardAPI(MV_API_KEY)
    snapResponse = mvDashboard.camera.generateDeviceCameraSnapshot(
        deviceSerial, timestamp=snapTime)
    print("Snapshot url is generated = ", snapResponse,
          '\nMotion occured at = ', occurredAt,
          '\nStable snapshot taken at = ', snapTime)
    # check if the url is accessible
    for _ in range(5):
        # wait for a short time until the snapshot is available
        time.sleep(3)
        # check if snapshot is accessible
        image_response = requests.get(snapResponse['url'])
        # If HTTP code 200 (OK) is returned, quit the loop and continue
        if image_response.status_code == 200:
            return snapResponse
            break
        else:
            print(
                f"Could not access snapshot for camera {deviceSerial} right now. Wait for 3 sec.")
        continue


# filter the snapshot with label, if car or registration plate is detected, return true.
def VisionFiltering(url):
    # extracting labels from snapshot url
    detectedLabel = detect_labels_uri(url)
    print("Snapshot labels detected = ", detectedLabel)
    # filter the snapshot with labels
    labelList = ['Vehicle', 'Vehicle registration plate', 'Car']
    boolResult = filter_labels(detectedLabel, labelList)
    return boolResult

# Post notification to WebexTeamsAPI
def PostToWebex(snapResponse, searchOrder, detectedPlate):
    # Webex API
    webexAPI = WebexTeamsAPI(access_token=WEBEX_TOKEN)

    # if car plate and order information match, send notification to webex
    for plate in detectedPlate:
        if searchOrder != []:

            # Notify WebEx
            try:
                teams_message = "Your customer, {}".format(
                    searchOrder['customer'])
                teams_message += " , with car plate number: {}".format(
                    searchOrder['car_plate'])
                teams_message += "has arrived \n \n"
                teams_message += "Image of the car detected: {}\n".format(
                    snapResponse['url'])
            except Exception as e:
                teams_message = 'The server received a webhook but there was a Webex error'

            webexAPI.messages.create(
                roomId=webexTo, markdown=teams_message)

        else:
            print("No order information match with ", plate)
            # if there is no match, send url image to webex for manual investigation
            # send to dedicated space
            try:
                teams_message = "Error!! There was no match: {}\n".format(
                    plate)
                teams_message += "Image of the car detected: {}\n".format(
                    snapResponse['url'])
            except Exception as e:
                teams_message = 'The server received a webhook but there was a Webex error'

            webexAPI.messages.create(
                roomId=webexTo, markdown=teams_message)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST' and request.headers['Content-Type'] == 'application/json':
        payload = request.json
        if payload['sharedSecret'] == MV_SHARED_KEY:

            # define variable of the alert event
            networkId = payload['networkId']
            deviceSerial = payload['deviceSerial']
            deviceName = payload['deviceName']
            alertTypeId = payload['alertTypeId']
            occurredAt = payload['occurredAt']

            # wait several seconds for the car to be parked, then take a snapshot
            time.sleep(waitTime)
            snapTime = addSeconds(occurredAt, waitTime)

            # if motion_alert is received
            if alertTypeId == 'motion_alert':
                # wait several seconds for the car to be parked
                #time.sleep(waitTime)
                #snapTime = addSeconds(occurredAt, waitTime)

                # then take 5 snapshots
                for _ in range(5):
                    snapResponse = SnapshotAndUri(
                        deviceSerial, occurredAt, snapTime)
                    # filter the snapshot for vehicle and carplate
                    filterResult = VisionFiltering(snapResponse['url'])
                    if filterResult == True:
                        # detecting car plate from snapshot url
                        detectedPlate = detect_text_uri(snapResponse['url'])
                        print("Car plate detected = ", detectedPlate)

                        # loop through the text detection result
                        for plate in detectedPlate:
                            # store car event to a database
                            newCarEntry = car_to_db(
                                dbCarUrl, plate, snapTime, deviceName)
                            print('New car entry has been stored in DB = ', newCarEntry)

                            #search for a plate match in the order datbase
                            queryParam = '?car_plate=' + plate + \
                                '&_sort=id&_order=desc&_limit=1'  # search car plate by most recent entry
                            searchOrder = get_order(dbOrderUrl + queryParam)

                            #if there is an order match, break from the loop
                            if searchOrder != []:
                                break
                            #if there is no order match, wait a while and take the snapshot again
                            else:
                                time.sleep(intervalTime)
                                snapTime = addSeconds(snapTime, intervalTime)
                                continue

                    # if no car or plate is detected within 5 tries just keep going
                    else:
                        time.sleep(intervalTime)
                        snapTime = addSeconds(snapTime, intervalTime)
                        continue

                # post result as webex notification
                PostToWebex(snapResponse, searchOrder, detectedPlate)

            else:
                print('Not a motion alert. Failed to generate snapshot url.')
                exit()

            # reset the runScript for the next car event
            runScript = True
            return Response(status=200)

        else:
            print('Invalid Meraki secret key')

    else:
        abort(400, 'Unauthorized action')


# run Flask server
if __name__ == '__main__':
    app.run(debug=True)
