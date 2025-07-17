import os
import re
import tempfile
import requests
import torch
from io import BytesIO
from datetime import timedelta
from dotenv import load_dotenv
from PIL import Image
from bs4 import BeautifulSoup

import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction, ButtonStyle
from discord.ui import Button, View
import whisper

from transformers import BlipProcessor, BlipForConditionalGeneration
import asyncio

from answer import get_answers

# --- Configuration ---

device = "cuda" if torch.cuda.is_available() else "cpu"

# Regex to detect Tenor URLs
TENOR_URL_PATTERN = re.compile(r"https?://tenor\.com/view/\S+")

# Simple regex to detect classic image URLs in a message (optional)
IMG_URL_PATTERN = re.compile(r"https?://\S+\.(?:png|jpg|jpeg|gif)")

# BLIP (image captioning)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model_blip = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base"
).to(device)

# Whisper (audio transcription)
model_whisper = whisper.load_model("small")

# Absolute paths for ffmpeg and ffprobe
ffmpeg_path = r"C:\Users\romai\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
ffprobe_path = r"C:\Users\romai\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

# Force pydub to use these paths
os.environ["PATH"] = (
    os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")
)
os.environ["FFMPEG_BINARY"] = ffmpeg_path
os.environ["FFPROBE_BINARY"] = ffprobe_path

from pydub import AudioSegment  # noqa: E402

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# --- Utility functions ---


async def get_tenor_gif_url(tenor_page_url: str) -> str | None:
    """Gets the direct GIF URL from a Tenor page."""
    try:
        resp = requests.get(tenor_page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        meta_og_image = soup.find("meta", property="og:image")
        if meta_og_image:
            return meta_og_image["content"]
    except Exception as e:
        print(f"Error retrieving Tenor URL: {e}")
    return None


def describe_image_blip_from_bytes(image_bytes_io: BytesIO) -> str:
    """Describes an image using BLIP, from a BytesIO."""
    try:
        image = Image.open(image_bytes_io).convert("RGB")
        inputs = processor(image, return_tensors="pt").to(device)
        out = model_blip.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        return f"BLIP description error: {e}"


async def describe_image_blip(image_url: str) -> str:
    """Async function to describe an image from a URL (download + BLIP)."""
    try:
        resp = requests.get(image_url)
        resp.raise_for_status()
        img_bytes = BytesIO(resp.content)
        # BLIP is blocking => run in thread
        description = await asyncio.to_thread(describe_image_blip_from_bytes, img_bytes)
        return description
    except Exception as e:
        return f"Error downloading/describing image: {e}"


async def transcribe_audio_attachment(att_url: str, filename: str) -> str:
    """Downloads audio, converts and transcribes with Whisper."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, filename)
            # Download
            resp = requests.get(att_url)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)

            # Convert to WAV if needed
            wav_path = os.path.join(tmpdir, "converted.wav")
            audio = AudioSegment.from_file(local_path)
            audio.export(wav_path, format="wav")

            # Transcribe
            result = model_whisper.transcribe(wav_path, language="fr")
            return result.get("text", "").strip() or "(empty)"
    except Exception as e:
        return f"Transcription error: {e}"


# --- Discord Bot ---

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Connected as {bot.user}")


@tree.command(name="kuma-say", description="Make the bot speak in this channel.")
@app_commands.describe(message="Message to send")
async def kuma_say(interaction: discord.Interaction, message: str):
    try:
        await interaction.channel.send(message)
        await interaction.response.send_message(
            f"Message sent in {interaction.channel.mention}", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "The bot does not have permission to write in this channel.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"An error occurred: {e}", ephemeral=True
        )


async def extract_clean_conversation(
    interaction: discord.Interaction, limit: int
) -> str:
    messages = []
    async for msg in interaction.channel.history(limit=limit + 1):
        if msg.author != bot.user:
            content = msg.content or ""

            # Tenor links
            tenor_links = TENOR_URL_PATTERN.findall(content)
            for tenor_link in tenor_links:
                gif_url = await get_tenor_gif_url(tenor_link)
                if gif_url:
                    desc = await describe_image_blip(gif_url)
                    content += f"\n[Tenor] {desc}"

            # Attachments
            for att in msg.attachments:
                fname = att.filename.lower()

                if fname.endswith((".ogg", ".mp3", ".wav", ".m4a")):
                    transcription = await transcribe_audio_attachment(att.url, fname)
                    content += f"\n[Audio] Transcription: {transcription}"

                elif fname.endswith((".png", ".jpg", ".jpeg", ".gif")):
                    desc = await describe_image_blip(att.url)
                    content += f"\n[Image] Description: {desc}"

                else:
                    content += f"\n[Attachment] {att.filename}"

            if not content.strip():
                content = "[Empty message]"

            messages.append(f"{msg.author.display_name}: {content.strip()}")

    return "\n".join(reversed(messages[:limit]))


@tree.command(name="kuma-answer", description="Generate 3 answers based on an emotion.")
@app_commands.describe(
    number="Number of messages to analyze (max 100)",
    emotion="Emotion to convey in the answer",
)
@app_commands.choices(
    emotion=[
        app_commands.Choice(name="Like the conversation's sentiment", value="default"),
        app_commands.Choice(name="Seductive", value="seductive"),
        app_commands.Choice(name="Aggressive", value="aggressive"),
        app_commands.Choice(name="Funny", value="funny"),
        app_commands.Choice(name="Professional", value="professional"),
        app_commands.Choice(name="Opposite", value="opposite"),
    ]
)
async def kuma_answer(
    interaction: Interaction, number: int, emotion: app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True)

    # Step 1: retrieve and enrich the conversation
    conversation = await extract_clean_conversation(interaction, number)

    # Step 2: call the model
    emotion_value = emotion.value if emotion.value != "default" else "neutral"
    answers = await asyncio.to_thread(get_answers, conversation, emotion_value)

    # Step 3: answer interface
    class AnswerView(View):
        def __init__(self, answers_list: list[str]):
            super().__init__(timeout=60)
            for i, answer in enumerate(answers_list):
                label = f"Answer {chr(65 + i)}"
                style = [ButtonStyle.primary, ButtonStyle.success, ButtonStyle.danger][
                    i
                ]

                async def button_callback(inter: Interaction, msg=answer):
                    await inter.response.send_message(f"💬 **{msg}**", ephemeral=True)

                self.add_item(Button(label=label, style=style, custom_id=str(i)))
                self.children[-1].callback = button_callback

    text = "**Here are 3 generated answers:**\n\n"
    for idx, a in enumerate(answers):
        text += f"**Answer {chr(65+idx)}**: {a}\n"

    text += "\n*Click on an answer to copy it.*"

    await interaction.followup.send(
        content=text, view=AnswerView(answers), ephemeral=True
    )


token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set.")
bot.run(token)
