import boto3
import json
from typing import Any

# document_name: str = f"../conversations-examples/{application}.png"
#
# with open(document_name, 'rb') as document:
#     image_bytes: bytearray = bytearray(document.read())
#
# textract = boto3.client('textract')
# response = textract.detect_document_text(Document={'Bytes': image_bytes})
# with open(f"../conversations-examples/{application}.json", "w") as file:
#     json.dump(response, file)


def differentiate_senders(textract_response) -> str:
    """
    Labels each text line by sender ("User" or "Other") based on the horizontal position.

    Processes AWS Textract response to group text lines into messages from either:
    - "User" (right-aligned, typically current user)
    - "Other" (left-aligned, typically other participant)

    Note: This basic implementation:
    - Uses fixed left threshold (0.1) for sender detection
    - Doesn't filter metadata (timestamps, read receipts)
    - Assumes simple left/right message alignment

    Parameters
    ----------
    textract_response : dict
        AWS Textract response dictionary from detect_document_text API call.
        Expected structure: Contains 'Blocks' with 'BlockType' 'LINE' entries.

    Returns
    -------
    str
        Formatted conversation with sender labels and messages.

    Example
    -------
    >>> response = textract.detect_document_text(...)
    >>> print(differentiate_senders(response))
    User:
    Hello there!
    How are you?

    Other:
    I'm doing great!
    """
    conversation_lines: list[str] = []
    current_sender: str | None = None  # Tracks "User" or "Other"

    for item in textract_response["Blocks"]:
        if item["BlockType"] == "LINE":
            text: str = item["Text"]
            geometry: dict[str, float] = item["Geometry"]["BoundingBox"]

            # Determine sender using relative position
            is_recipient: bool = geometry["Left"] < 0.1
            sender: str = "Other" if is_recipient else "User"

            # Add the sender label and extra newline when changing participants
            if sender != current_sender:
                # Don't add an extra newline at the very beginning
                if conversation_lines:
                    # Extra newline between participants
                    conversation_lines.append("")

                conversation_lines.append(f"{sender}:")
                current_sender = sender

            conversation_lines.append(text)

    return "\n".join(conversation_lines)


# TODO: discord

application: str = "imessage"
with open(f"../conversations-examples/{application}.json", "r") as file:
    response: dict[str, Any] = json.load(file)

print(differentiate_senders(response))
