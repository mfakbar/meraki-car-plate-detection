# functions related to plate detection using Google Vision API
import os
from google.cloud import vision
import io
from dotenv import load_dotenv


# search .env and load environment variable
load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')


# define the text detection API call, taking in the url of the image:
def detect_text_uri(uri):
    """Detects text in the file located in Google Cloud Storage or on the Web.
        """
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri

    response = client.text_detection(image=image)
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

    return detectedPlate


def detect_labels_uri(uri):
    """Detects labels in the file located in Google Cloud Storage or on the
    Web."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri

    response = client.label_detection(image=image)
    labels = response.label_annotations

    detectedLabel = []

    for label in labels:
        detectedLabel.append(label.description)

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))

    return detectedLabel
