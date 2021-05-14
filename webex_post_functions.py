#Requirements
from webexteamssdk import WebexTeamsAPI, Webhook
from flask import Flask, request
#from db_functions import *
#from plate_detection_functions import *



#WebEx Authorization Token
access_token = "MmIxZDBmOTctZWU5Yi00YjM4LWI0OGItYTM0NmVlOTI5ZWYwYTA0OTBjZTUtMTVm_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f"


#RoomId of the bot and the space where you wanna enter the message
id = "Y2lzY29zcGFyazovL3VzL1JPT00vMzMwMjhlZjAtYjNhYS0xMWViLTlhNGYtMDdjOWE1ODk1MDdl"
api = WebexTeamsAPI(access_token)



app = Flask(__name__)


#URL for webhook
target_url = "https://dd2287283a92.ngrok.io/webhook"



def send_detected_notification(snapResponse, searchOrder, detectedPlate):
    #Pass teh URL, some boolean value for Manual Detection vs Successful Detection
    CARD_CONTENT = {

        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.1",
        "body": [

            {
                "type": "TextBlock",
                "text": "Your customer has arrived",
                "size": "medium",
                "weight": "bolder"
            },

            {
                "type": "TextBlock",
                "text": "Here's the image of the vehicle",
                "wrap": True
            },

            {
                "type": "ImageSet",
                "imageSize": "medium",
                "images": [

                    {
                        "type": "Image",
                        "url": ""   # Image of the car whose Plate has been detected
                    },
                ]
            },

             {
            "type": "FactSet",
            "facts": [
                {
                    "title": "Food Ordered:",
                    "value": "Burger"
                }
            ]
        }

    ],

        "actions": [
            {
                "type": "Action.Submit",
                "title": "Process Order",
                "data": {
                    "type": "orderProcessed",
                } # Shall I create another button saying Deleted for discarding orders
             },

            {
                 "type": "Action.Submit",
                 "title": "Discard Order",
                 "data": {
                     "type": "orderDiscard",
                 }
             }
        ]
    }

    # Sending webexcard
    if detectedPlate != []:
        for plate in detectedPlate:
            if searchOrder != []:
                url=snapResponse['url']
                CARD_CONTENT["body"][2]["images"][0]["url"] = url

                api.messages.create(
                     roomId=id,
                     text="If you see this your client cannot render cards",
                     attachments=[{
                         "contentType": "application/vnd.microsoft.card.adaptive",
                         "content": CARD_CONTENT
                        }],)

    elif:
        CARD_CONTENT["body"][1]["text"] = "Please check the order manually"
        url=snapResponse['url']
        api.messages.create(
                     roomId=id,
                     text="If you see this your client cannot render cards",
                         "contentType": "application/vnd.microsoft.card.adaptive",
                         "content": CARD_CONTENT
                        }],
                    )


def create_webhook():
    """
    Create the Webex Teams webhooks we need for the bot
    """
    print("Creating Message Created Webhook...")
    webhook = api.webhooks.create(
        name = "Test webhook",
        resource = "attachmentActions",
        event="created",
        targetUrl= target_url
    )
    return webhook


def delete_webhooks():
    """
    List all webhooks and delete the webhooks
    """
    for webhook in api.webhooks.list():
        print("Deleting Webhook:", webhook.name, webhook.targetUrl)
        api.webhooks.delete(webhook.id)
    return "All webhooks have been deleted"




def respond_to_button_press(webhook):
    """
    Respond to a button press on the card we posted
    """
    attachment_action = api.attachment_actions.get(webhook.data.id)
    if attachment_action.inputs['type'] == "orderProcessed":
        serviced = True
        print(serviced)
        #Create a function to change the value in the database

    elif attachment_action.inputs['type'] == "orderDiscard" :                 #attachment_action.data.id.type
        serviced = False
        print(serviced)

    delete_webhooks()





@app.route("/webhooks", methods=["POST"])
def webhook_received():
    webhook = Webhook(request.json)
    print(request.json)
    respond_to_button_press(webhook)

    return Response(status=200)



if __name__ == "__main__":
    send_detected_notification()
    app.run()
