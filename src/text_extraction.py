import boto3
import json
from typing import Any

# # Document
# documentName = "../test.png"
#
# # Read document content
# with open(documentName, 'rb') as document:
#     imageBytes = bytearray(document.read())
#
# # Amazon Textract client
# textract = boto3.client('textract')
#
# # Call Amazon Textract
# response = textract.detect_document_text(Document={'Bytes': imageBytes})
# with open("response.json", "w") as file:
#     json.dump(response, file)

with open("response.json", "r") as file:
    response: dict[str, Any] = json.load(file)

# For SMS-like messages (imessage currently)
# The recipient messages have the property "left" equal to 0.07 (near 0)
# Our messages have this property equal or greater than 0.3
# For Discord, reddit, etc..., another strategy is needed

sender: int | None = None  # 0 = me, 1 = recipient

for item in response["Blocks"]:
    if item["BlockType"] == "LINE":
        if item["Geometry"]["BoundingBox"]["Left"] < 0.1:
            if sender is None or sender == 0:
                print("\nRecipient:")
                sender = 1

            print(item["Text"])

        else:
            if sender is None or sender == 1:
                print("\nMe:")
                sender = 0

            print(item["Text"])
