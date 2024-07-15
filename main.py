import discord
from discord.ext import commands
from quart import Quart, jsonify, request
import asyncio
import os

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Quart app setup
app = Quart(__name__)

# Discord channel IDs (replace with your actual channel IDs)
CHANNEL_IDS = {
    'general': 1235297170287231079,
    'test-release':1262212983426125835
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@app.route('/')
async def index():
    return jsonify({"Choo Choo": "Welcome to your Quart app 🚅"})

@app.route('/send_message', methods=['POST'])
async def send_message():
    data = await request.json
    channel_name = data.get('channel', 'test-release')
    
    if channel_name not in CHANNEL_IDS:
        return 'Invalid channel name', 400
    
    channel_id = CHANNEL_IDS[channel_name]
    
    await send_discord_message(
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
    )
    
    return 'Message sent', 200

async def send_discord_message(channel_id, novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, novel_id, cover_id):
    channel = bot.get_channel(channel_id)
    if channel:
        # Define novel_id to role_id and color mapping
        role_map = {
            '0c09a384-dc9f-474d-a1c5-f2c65f68a5ab': {'role_id': 1219457467847544932, 'color': "#99AAB5"},  # The Lone SF Transmigrator in the Otherworld Forum
            '1476685b-badc-4fe1-a962-5517f4b23363': {'role_id': 1219457467793145959, 'color': "#c0c0c0"},  # Civil Servant in Romance Fantasy
            '222a1192-5471-48a5-a22c-d5277ba03df8': {'role_id': 1219457467793145963, 'color': "#8d39ff"},  # I Became The Necromancer Of The Academy
            '3135a8c6-f426-4eca-9c9e-2c5011766f81': {'role_id': 1219457467847544924, 'color': "#4364ff"},  # I Am This Murim's Crazy Bitch
            '3bc6a1f0-2b1b-4ee6-a377-13be0bc67b87': {'role_id': 1219457467872968742, 'color': "#d4ee0f"},  # The Regressor and the Blind Saint
            '3fecc06f-57f1-4f6e-8fff-cf109de39e88': {'role_id': 1219457467793145962, 'color': "#d463c1"},  # I Unknowingly Rejected My Favorite
            '4db280ca-8ce5-4464-afc7-2079c17e6d5e': {'role_id': 1219457467872968747, 'color': "#ff0004"},  # Escaping the Mystery Hotel
            '5535a77a-9375-4882-8766-8388348abc4c': {'role_id': 1219457467847544931, 'color': "#85dfcc"},  # The Academy's Weakest Became A Demon-Limited Hunter
            '6468040e-a86a-44f8-a14a-7067418fe0a1': {'role_id': 1219457467872968743, 'color': "#dad62f"},  # Omniscient First-Person's Viewpoint
            '69c2c3c2-ae68-46e7-97d2-b1868b05adc1': {'role_id': 1219457467872968746, 'color': "#d3162a"},  # Fated To Be Loved By Villains
            '69d6ab1d-4da5-4e84-8ffb-190308540908': {'role_id': 1219457467847544929, 'color': "#3ee29f"},  # Seoul Object Story
            '827757d8-161c-441b-8240-f4dbd7407ce4': {'role_id': 1219457467793145965, 'color': "#a472e6"},  # My Daughters Are Regressors
            '8da58504-bee5-4807-804a-23215c8a4e7e': {'role_id': 1219457467847544930, 'color': "#1ABC9C"},  # City of Witches
            '94683b45-439b-424a-b7f6-76154bcd8750': {'role_id': 1219457467847544923, 'color': "#0d6cdf"},  # Pseudo Resident's Illegal Stay in Another World
            '9fe66022-d209-4d2c-9397-beb256982883': {'role_id': 1244241518437601321, 'color': "#E67E22"},  # Transmigrated Into A Tragic Romance Fantasy
            'a7e499f7-fa6b-4d86-8ee6-1bf6772890f5': {'role_id': 1219457467872968744, 'color': "#f6ba10"},  # Childhood Friend of the Zenith
            'b92c8a56-9538-42e5-9428-0d55a0e1becc': {'role_id': 1219457467793145957, 'color': "#57576d"},  # The Heaven-Slaying Sword
            'c0018319-9173-4cc8-9aed-27db5b33fbd0': {'role_id': 1219457467675836435, 'color': "#111010"},  # Becoming Professor Moriarty's Probability
            'd63886fd-b00b-426c-ba94-f5f7186c89d9': {'role_id': 1244241901616627773, 'color': "#206694"},  # The Magic Academy's Physicist
            'e1ee79a1-35f4-40e4-8c0d-f54cb6e1be81': {'role_id': 1219457467847544928, 'color': "#2ECC71"},  # The Villain Who Robbed the Heroines
            'e5cd1c8b-af3d-4975-8166-8865092d2a6a': {'role_id': 1219457467847544927, 'color': "#8ceaf6"},  # The Main Heroines are Trying to Kill Me
            'f1cc7b93-ba56-4cf0-9d33-26e62e17c395': {'role_id': 1219457467793145964, 'color': "#71368A"},  # Otherworld TRPG Game Master
            'fb2cfad1-9b49-40be-83f5-8cbcd706b0bf': {'role_id': 1219457467793145961, 'color': "#b914e2"},  # A Love Letter From The Future
        }
        
        role_info = role_map.get(novel_id, {})
        role_id = role_info.get('role_id')
        embed_color = role_info.get('color', discord.Color.default())
        
        role = None
        if role_id:
            role = channel.guild.get_role(role_id)
        
        embed = discord.Embed(color=embed_color)
        
        embed.title = novel_title
        embed.description = f"Premium Chapter:\n[{chapter_number} - {chapter_title}](https://genesistudio.com/viewer/{chapter_id})\n\n Free Chapter:\n[{free_chapter_number} - {free_chapter_title}](https://genesistudio.com/viewer/{free_chapter_id})"
        
        if cover_id:
            cover_url = f"https://edit.genesistudio.com/assets/{cover_id}"
            embed.set_thumbnail(url=cover_url)
        
        # Mention the role in the message if it exists
        message_content = f"{role.mention if role else ''}"
        await channel.send(content=message_content, embed=embed)

async def start_bot():
    await bot.start(os.environ["DISCORD_TOKEN"])

@app.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
