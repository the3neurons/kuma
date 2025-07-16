import os
import tempfile
from datetime import timedelta
from dotenv import load_dotenv
import whisper
import discord
from discord import app_commands
from discord.ext import commands

# Absolute paths pour ffmpeg et ffprobe
ffmpeg_path = r"C:\Users\romai\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
ffprobe_path = r"C:\Users\romai\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

# Force envs vars for pydud before importing
os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ["PATH"]
os.environ["FFMPEG_BINARY"] = ffmpeg_path
os.environ["FFPROBE_BINARY"] = ffprobe_path

from pydub import AudioSegment  # noqa: E402

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path


model = whisper.load_model("small")  # base / small / medium / large


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


@tree.command(name="kuma-say", description="Fait parler le bot dans ce channel.")
@app_commands.describe(message="Message à envoyer")
async def kuma_say(interaction: discord.Interaction, message: str):
    try:
        await interaction.channel.send(message)
        await interaction.response.send_message(
            f"Message envoyé dans {interaction.channel.mention}", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "Le bot n’a pas la permission d’écrire dans ce salon.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"Une erreur est survenue : {e}", ephemeral=True
        )


@tree.command(
    name="kuma-get-last", description="Récupère les derniers messages d'un salon."
)
@app_commands.describe(nombre="Nombre de messages à récupérer (max 100)")
async def get_last_messages(interaction: discord.Interaction, nombre: int):
    if not interaction.channel:
        await interaction.response.send_message(
            "Impossible de récupérer le salon.", ephemeral=True
        )
        return

    if nombre < 1 or nombre > 100:
        await interaction.response.send_message(
            "Choisis un nombre entre 1 et 100.", ephemeral=True
        )
        return

    await interaction.response.defer()

    messages = []
    async for message in interaction.channel.history(limit=nombre + 1):
        messages.append(message)

    if messages and messages[0].author == bot.user:
        messages.pop(0)

    messages = messages[:nombre]

    lines = []
    for msg in reversed(messages):
        content = msg.content or ""

        if msg.attachments:
            for att in msg.attachments:
                filename = att.filename.lower()
                if filename.endswith((".ogg", ".mp3", ".wav", ".m4a")):
                    try:
                        # Download the attachment
                        with tempfile.TemporaryDirectory() as tmpdir:
                            file_path = os.path.join(tmpdir, att.filename)
                            await att.save(file_path)

                            # Convert to WAV if necessary
                            wav_path = os.path.join(tmpdir, "converted.wav")
                            audio = AudioSegment.from_file(file_path)
                            audio.export(wav_path, format="wav")

                            # Transcribe the audio
                            result = model.transcribe(wav_path, language="fr")
                            transcription = result["text"].strip()

                            content += f"\n[Vocal] {att.filename} : {att.url}"
                            content += f"\nTranscription : {transcription or '(vide)'}"

                    except Exception as e:
                        content += f"\nErreur transcription : {e}"

                else:
                    content += f"\n[Fichier] {att.filename} : {att.url}"

        if not content.strip():
            content = "[Message vide]"

        timestamp = (msg.created_at + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        author = msg.author.display_name
        lines.append(f"[{timestamp}] {author} : {content}")

    response = "\n".join(lines)

    if len(response) > 1900:
        with open("messages.txt", "w", encoding="utf-8") as f:
            f.write(response)
        await interaction.followup.send(file=discord.File("messages.txt"))
    else:
        await interaction.followup.send(
            f"Voici les **{nombre}** derniers messages :\n```{response}```"
        )


token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("L'environnement DISCORD_BOT_TOKEN n'est pas défini.")
bot.run(token)
