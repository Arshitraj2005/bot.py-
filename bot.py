import asyncio
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.types.input_stream import AudioPiped, InputStream
import yt_dlp

API_ID = 21104628
API_HASH = "45261b9ce50786fc8ab1a8b45494f577"
BOT_TOKEN = "8299919094:AAHzRFwXOYI0hDlLc8smrABr4R7zlR0ib9Q"

app = Client("music-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
voice = PyTgCalls(app)

queues: Dict[int, List[dict]] = {}
now_playing: Dict[int, Optional[dict]] = {}

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
}

async def ytdlp_extract(query: str) -> dict:
    loop = asyncio.get_running_loop()
    def _extract():
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            for f in info.get("formats", [])[::-1]:
                if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url"):
                    return {
                        "url": f["url"],
                        "title": info.get("title", "Unknown"),
                        "webpage_url": info.get("webpage_url", query),
                        "duration": info.get("duration"),
                    }
            return {
                "url": info.get("url"),
                "title": info.get("title", "Unknown"),
                "webpage_url": info.get("webpage_url", query),
                "duration": info.get("duration"),
            }
    return await loop.run_in_executor(None, _extract)

async def ensure_queue(chat_id: int):
    if chat_id not in queues:
        queues[chat_id] = []

async def start_stream(chat_id: int):
    await ensure_queue(chat_id)
    if not queues[chat_id]:
        now_playing[chat_id] = None
        return
    track = queues[chat_id].pop(0)
    now_playing[chat_id] = track
    try:
        await voice.join_group_call(chat_id, InputStream(AudioPiped(track["url"])))
    except Exception:
        await voice.change_stream(chat_id, InputStream(AudioPiped(track["url"])))

@voice.on_stream_end()
async def on_stream_end(_: PyTgCalls, update: Update):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        await start_stream(chat_id)

@app.on_message(filters.command(["start"]))
async def start_cmd(_, m: Message):
    await m.reply_text("Namaste! Main group voice chat mein gaane chala sakta hoon.\nUse /play <song> to play.")

@app.on_message(filters.command(["play"]))
async def play_cmd(_, m: Message):
    chat_id = m.chat.id
    if len(m.command) < 2:
        return await m.reply_text("Usage: /play <YouTube URL or search>")
    query = m.text.split(None, 1)[1].strip()
    await ensure_queue(chat_id)
    msg = await m.reply_text("Searching…")
    try:
        info = await ytdlp_extract(query)
        queues[chat_id].append(info)
        await msg.edit_text(f"Queued: {info['title']}")
        if not now_playing.get(chat_id):
            await start_stream(chat_id)
    except Exception as e:
        await msg.edit_text(f"Error: {e}")

async def main():
    await app.start()
    await voice.start()
    print("Bot running...")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
