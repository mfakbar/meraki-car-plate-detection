# Flask server as webhook receiver > then triggers a series of scripts

from flask import Flask, request, Response, json
import meraki
import time
import os
from dotenv import load_dotenv
from db_functions import *
from plate_detection_functions import *

# search .env file and load environment variable
load_dotenv()
MV_SHARED_KEY = os.getenv('MV_SHARED_KEY')
MV_API_KEY = os.getenv('MV_API_KEY')
DB_HOST = os.getenv('DB_HOST')

# database url address
dbCarUrl = DB_HOST+'/car_event'
dbOrderUrl = DB_HOST+'/order'

# define label for filter out notification
labelFilter = ['Vehicle registration plate',
               'Automotive tire', 'Vehicle', 'Car', 'Motor vehicle']

# Flask server setup
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST' and request.headers['Content-Type'] == 'application/json':
        payload = request.json
        if payload['sharedSecret'] == MV_SHARED_KEY:

            # define variable
            networkId = payload['networkId']
            deviceSerial = payload['deviceSerial']
            deviceName = payload['deviceName']
            alertTypeId = payload['alertTypeId']
            occurredAt = payload['occurredAt']

            # generate snapshot url
            if alertTypeId == 'motion_alert':
                mvDashboard = meraki.DashboardAPI(MV_API_KEY)
                snapResponse = mvDashboard.camera.generateDeviceCameraSnapshot(
                    deviceSerial, timestamp=occurredAt)
                print("Snapshot url is generated = ", snapResponse,
                      '\nMotion occured at = ', occurredAt)
            else:
                print('Not a motion alert. Failed to generate snapshot url.')
                exit()

            # check if the url is accessible
            for _ in range(5):
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

            # detecting car plate from snapshot url
            detectedPlate = detect_text_uri(snapResponse['url'])
            # detectedPlate = 'MY70 BMW'
            print("Car plate detected = ", detectedPlate)

            # extracting labels from snapshot url
            detectedLabel = detect_labels_uri(snapResponse['url'])
            print("Snapshot labels detected = ", detectedLabel)

            # filter the snapshot with labels
            labelList = ['Vehicle', 'Vehicle registration plate', 'Car']
            filter_labels(detectedLabel, labelList)

            # if car plate is not detected, send snapshot url to webex for manual check
            # to minimize overhead, notification only include car/vehicle-related label

            # labelCheck = any(item in detectedLabel for item in labelFilter)
            # if detectedPlate == [] and labelCheck is True:
            #     #### to-do: send url image to webex for manual investigation / security reason ####

            # if car plate is detected, run series of process:
            # store car event in database > check order information > send webex notification

            # if detectedPlate != []:
            for plate in detectedPlate:

                # store car event to database
                newCarEntry = car_to_db(dbCarUrl, plate,
                                        occurredAt, deviceName)
                print('New car entry has been stored in DB = ', newCarEntry)

                # check if the detected car plate relate to existing order database
                queryParam = '?car_plate=' + plate + \
                    '&_sort=id&_order=desc&_limit=1'  # search car plate by most recent entry
                searchOrder = get_order(dbOrderUrl + queryParam)

                # if car plate and order information match, send notification to webex
                if searchOrder != []:
                    print('The most recent order that match ',
                          plate, '= ', searchOrder)

                    ##### to-do: insert webex notification here #####

                else:
                    print("No order information match with ", plate)
                    #### to-do: send url image to webex for manual investigation ####

            return Response(status=200)
        else:
            print("Invalid secret key")
    else:
        abort(400, 'Unauthorized action')


# run Flask server
if __name__ == '__main__':
    app.run(debug=True)
