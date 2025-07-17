import boto3
import json
import os
from ocr import extract_conversation


def get_answers(conversation: str, emotion: str) -> list[str]:
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION_NAME"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    # Request parameters
    system_prompts = [
        {
            "text": f"""You will be given a conversation between two or more participants.
            The user (you) is always labeled as "me" in the transcript.
            All other participants are labeled with their original names or usernames.

            Your task is to generate exactly 3 distinct and natural-sounding messages that "me" could send as a reply to the latest message(s) from the other person(s).
            These replies must reflect the following emotion: {emotion}.

            Important guidelines:
            - The conversation may include metadata like timestamps, usernames, dates, app system messages (iMessage, WhatsApp, Messenger, etc.). Ignore these — they are not part of the actual conversation.
            - The replies must be in the **same language** as the conversation.
            - The replies should **match the sentiment and tone** of the overall conversation.
            - Do not include any speaker names (no "me:", no usernames).
            - Do not use quotation marks, bullet points, dashes, or markdown formatting.
            - Do not add extra explanations or commentary — only return the 3 messages.
            - The 3 messages must be **separated by a single newline** (`\\n`), and nothing else.

            Your output must be:
            - Exactly 3 ready-to-send, natural messages,
            - Clean and realistic, as if typed in a chat app,
            - Solely those 3 messages, each on its own line.
            """
        }
    ]
    message_list = [{"role": "user", "content": [{"text": conversation}]}]
    inference_params = {
        "max_new_tokens": 128,
        "top_p": 0.9,
        "top_k": 20,
        "temperature": 0.7,
    }
    request_body = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_prompts,
        "inferenceConfig": inference_params,
    }

    response = client.invoke_model_with_response_stream(
        modelId="eu.amazon.nova-micro-v1:0", body=json.dumps(request_body)
    )

    # Read the response stream
    chunk_count = 0
    answers: list[str] = []
    stream = response.get("body")
    if stream:
        for event in stream:
            chunk = event.get("chunk")
            if chunk:
                chunk_json = json.loads(chunk.get("bytes").decode())
                content_block_delta = chunk_json.get("contentBlockDelta")
                if content_block_delta:
                    chunk_count += 1
                    answers.append(content_block_delta.get("delta").get("text"))
    else:
        print("No response stream received.")

    return [text.strip() for text in "".join(answers).split("\n")]


if __name__ == "__main__":
    application: str = "imessage"
    conversation: str = extract_conversation(
        f"../conversations-examples/{application}.json"
    )
    emotion: str = "professional"
    print(get_answers(conversation, emotion))
