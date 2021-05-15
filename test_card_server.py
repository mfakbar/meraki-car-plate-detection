from flask import Flask, request, Response
from webexteamssdk import Webhook
from functions import *

WEBEX_ROOM_ID = 'Y2lzY29zcGFyazovL3VzL1JPT00vZWNhYzZiYjAtYjJmMC0xMWViLThhYmUtZGY3OTM3ZTg1ZTAw'

# URL for webhook
target_url = "https://a69432b6fb0c.ngrok.io/card_action"

# delete_webhooks()
# create_webhook(WEBEX_ROOM_ID, target_url)

webexApp = Flask(__name__)
webexApp.debug = True


@webexApp.route("/card_action", methods=["POST"])
def card_action():
    webhook_obj = Webhook(request.json)
    print(webhook_obj)

    # change serviced status in db
    respond_to_button_press(webhook_obj)
    return Response(status=200)


if __name__ == "__main__":
    webexApp.run()
