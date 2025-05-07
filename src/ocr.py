import boto3
import json
import os
from typing import Any
from dotenv import load_dotenv


def extract_text_from_image(image: str | bytes) -> dict[str, Any]:
    """
    Get the AWS Textract response dictionary containing the text and the
    position of it in the image.

    AWS API credentials must be defined, either in your local AWS configuration
    or in your environment variables. Environment variables names are
    `REGION_NAME`, `AWS_ACCESS_KEY_ID` an `AWS_SECRET_ACCESS_KEY`.

    Parameters
    ----------
    image: str | bytes
        Path to the image or image bytes.

    Returns
    -------
    dict[str, Any]
        The AWS Textract response dictionary.
    """
    load_dotenv()

    if isinstance(image, str):
        with open(image, "rb") as document:
            image: bytes = document.read()

    textract = boto3.client(
        service_name="textract",
        region_name=os.getenv("AWS_REGION_NAME"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    return textract.detect_document_text(Document={"Bytes": image})


# TODO: discord
def differentiate_senders(textract_response: dict[str, Any]) -> str:
    """
    Labels each text line by sender ("User" or "Other") based on the horizontal
    position.

    Processes AWS Textract response to group text lines into messages from
    either:
    - "User" (right-aligned, typically current user)
    - "Other" (left-aligned, typically other participant)

    Note: This basic implementation:
    - Uses fixed left threshold (0.1) for sender detection
    - Doesn't filter metadata (timestamps, read receipts)
    - Assumes simple left/right message alignment

    Parameters
    ----------
    textract_response : dict[str, Any]
        AWS Textract response dictionary from detect_document_text API call.
        Expected structure: Contains 'Blocks' with 'BlockType' 'LINE' entries.

    Returns
    -------
    str
        Formatted conversation with sender labels and messages.
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


def extract_conversation(file: str | bytes) -> str:
    """
    Extracts conversation from either an image file or pre-processed JSON.

    Parameters
    ----------
    file : str | bytes
        Path to a messaging screenshot image or to a pre-extracted AWS Textract
        JSON file, or the image bytes.

    Returns
    -------
    str
        Formatted conversation with sender labels and messages.

    Raises
    ------
    FileNotFoundError
        Given file path doesn't exist.
    ValueError
        Give file is in the wrong format.
    """
    if isinstance(file, str):
        if not os.path.exists(file):
            raise FileNotFoundError(f"{file} doesn't exist.")

        accepted_image_formats: list[str] = ["png", "jpeg", "jpg"]
        file_extension: str = file.split(".")[-1].lower()

        if file_extension == "json":
            with open(file, "r") as file:
                conversation_data: dict[str, Any] = json.load(file)

        elif file_extension in accepted_image_formats:
            conversation_data: dict[str, Any] = extract_text_from_image(file)

        else:
            raise ValueError("Wrong file format.")
    else:
        conversation_data: dict[str, Any] = extract_text_from_image(file)

    return differentiate_senders(conversation_data)


if __name__ == "__main__":
    application: str = "imessage"
    print(extract_conversation(f"../conversations-examples/{application}.png"))
