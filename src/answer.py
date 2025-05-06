import boto3
import json
import os
from ocr import extract_conversation


def get_answers(conversation: str, emotion: str) -> list[str]:
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION_NAME"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    # Request parameters
    system_prompts = [
        {
            "text": f"""You will be prompt a conversation between two person:
            the user and the other person. You must provide three different
            messages that the user will choose as an answer to the last messages
            from the other person, but those three messages must be based on the
            following emotion: {emotion}. The messages you will generate must be
            based on the conversation and its sentiments. Be careful, there can
            be metadata, such as timestamps, dates, names, informations, etc.
            Those are not messages from both persons, but from the application
            they use (iMessage, WhatsApp, Signal, Messenger, etc.). Only provide
            the three messages in your answer, nothing else, not even with
            bullet points: the three messages should be separated by a newline.
            Finally, the messages you will generate must be in the same language
            than the conversation."""
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
