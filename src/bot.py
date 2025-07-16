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
import whisper

from transformers import BlipProcessor, BlipForConditionalGeneration
import asyncio

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
    print(f"Connecté en tant que {bot.user}")
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


@tree.command(
    name="kuma-get-last", description="Retrieve the last messages from a channel."
)
@app_commands.describe(nombre="Number of messages to retrieve (max 100)")
async def get_last_messages(interaction: discord.Interaction, nombre: int):
    if not interaction.channel:
        await interaction.response.send_message(
            "Unable to retrieve the channel.", ephemeral=True
        )
        return

    if nombre < 1 or nombre > 100:
        await interaction.response.send_message(
            "Choose a number between 1 and 100.", ephemeral=True
        )
        return

    await interaction.response.defer()

    messages = []
    async for msg in interaction.channel.history(limit=nombre + 1):
        messages.append(msg)

    # Remove the last bot message if it exists (auto)
    if messages and messages[0].author == bot.user:
        messages.pop(0)

    messages = messages[:nombre]

    lines = []
    for msg in reversed(messages):
        content = msg.content or ""

        # Handle Tenor links (GIF page) in text
        tenor_links = TENOR_URL_PATTERN.findall(content)
        for tenor_link in tenor_links:
            gif_url = await get_tenor_gif_url(tenor_link)
            if gif_url:
                desc = await describe_image_blip(gif_url)
                content += f"\n[Tenor GIF] {tenor_link}\n🖼️ Description: {desc}"
            else:
                content += f"\n[Tenor GIF] {tenor_link}\n🖼️ Description: unable to retrieve GIF."

        # Handle attachments
        if msg.attachments:
            for att in msg.attachments:
                filename = att.filename.lower()
                if filename.endswith((".ogg", ".mp3", ".wav", ".m4a")):
                    # Audio transcription
                    transcription = await transcribe_audio_attachment(
                        att.url, att.filename
                    )
                    content += f"\n[Vocal] {att.filename}: {att.url}\n📝 Transcription: {transcription}"

                elif filename.endswith((".png", ".jpg", ".jpeg", ".gif")):
                    # Image/GIF description
                    description = await describe_image_blip(att.url)
                    content += f"\n[Image/GIF] {att.filename}: {att.url}\n🖼️ Description: {description}"

                else:
                    content += f"\n[File] {att.filename}: {att.url}"

        if not content.strip():
            content = "[Empty message]"

        timestamp = (msg.created_at + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        author = msg.author.display_name
        lines.append(f"[{timestamp}] {author}: {content}")

    response = "\n".join(lines)

    if len(response) > 1900:
        with open("messages.txt", "w", encoding="utf-8") as f:
            f.write(response)
        await interaction.followup.send(file=discord.File("messages.txt"))
    else:
        await interaction.followup.send(
            f"Here are the **{nombre}** last messages:\n```{response}```"
        )


token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set.")
bot.run(token)
