import discord
from discord.ext import commands
from flask import Flask, jsonify, request
import asyncio
import threading
import os

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Flask app setup
app = Flask(__name__)

# Discord channel IDs (replace with your actual channel IDs)
CHANNEL_IDS = {
    'general': 1235297170287231079
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    channel_name = data.get('channel', 'general')
    
    if channel_name not in CHANNEL_IDS:
        return 'Invalid channel name', 400
    
    channel_id = CHANNEL_IDS[channel_name]
    
    asyncio.run_coroutine_threadsafe(send_discord_message(
        channel_id,
        data.get('novel_title', ''),
        data.get('chapter_number', ''),
        data.get('chapter_title', ''),
        data.get('chapter_id', ''),
        data.get('free_chapter_number', ''),
        data.get('free_chapter_title', ''),
        data.get('free_chapter_id', ''),
        data.get('novel_id', ''),
        data.get('cover', '')
    ), bot.loop)
    return 'Message sent', 200

async def send_discord_message(channel_id, novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, novel_id, cover_id):
    channel = bot.get_channel(channel_id)
    if channel:
        # Define novel_id to role_id mapping
        role_map = {
            '827757d8-161c-441b-8240-f4dbd7407ce4': 1259695280413085737,
            '69d6ab1d-4da5-4e84-8ffb-190308540908': 1259695317436076082
        }
        
        role_id = role_map.get(novel_id)
        role = None
        if role_id:
            role = channel.guild.get_role(role_id)
        
        embed = discord.Embed(color=discord.Color.blue())
        
        embed.title = novel_title
        embed.description = f"Premium Chapter:\n[{chapter_number} - {chapter_title}](https://genesistudio.com/viewer/{chapter_id})\n\n Free Chapter:\n[{free_chapter_number} - {free_chapter_title}](https://genesistudio.com/viewer/{free_chapter_id})"
        
        if cover_id:
            cover_url = f"https://edit.genesistudio.com/assets/{cover_id}"
            embed.set_thumbnail(url=cover_url)
        
        # Mention the role in the message if it exists
        message_content = f"{role.mention if role else ''}"
        await channel.send(content=message_content, embed=embed)

def run_flask():
    app.run(debug=True, port=os.getenv("PORT", default=5000))

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Run the Discord bot
    bot.run(os.environ["DISCORD_TOKEN"])