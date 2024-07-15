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
    'test-release':1262212983426125835,
    'release': 1219457468011380892
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
        data.get('cover', ''),
        data.get('abbreviation', '')
    )
    
    return 'Message sent', 200

async def send_discord_message(channel_id, novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, novel_id, cover_id, abbreviation):
    channel = bot.get_channel(channel_id)
    if channel:
        # Define novel_id to role_id and color mapping
        role_map = {
            '0c09a384-dc9f-474d-a1c5-f2c65f68a5ab': {'role_id': 1219457467847544932, 'color': discord.Color.from_rgb(153, 170, 181)},  # The Lone SF Transmigrator in the Otherworld Forum
            '1476685b-badc-4fe1-a962-5517f4b23363': {'role_id': 1219457467793145959, 'color': discord.Color.from_rgb(192, 192, 192)},  # Civil Servant in Romance Fantasy
            '222a1192-5471-48a5-a22c-d5277ba03df8': {'role_id': 1219457467793145963, 'color': discord.Color.from_rgb(141, 57, 255)},  # I Became The Necromancer Of The Academy
            '3135a8c6-f426-4eca-9c9e-2c5011766f81': {'role_id': 1219457467847544924, 'color': discord.Color.from_rgb(67, 100, 255)},  # I Am This Murim's Crazy Bitch
            '3bc6a1f0-2b1b-4ee6-a377-13be0bc67b87': {'role_id': 1219457467872968742, 'color': discord.Color.from_rgb(212, 238, 15)},  # The Regressor and the Blind Saint
            '3fecc06f-57f1-4f6e-8fff-cf109de39e88': {'role_id': 1219457467793145962, 'color': discord.Color.from_rgb(212, 99, 193)},  # I Unknowingly Rejected My Favorite
            '4db280ca-8ce5-4464-afc7-2079c17e6d5e': {'role_id': 1219457467872968747, 'color': discord.Color.from_rgb(255, 0, 4)},  # Escaping the Mystery Hotel
            '5535a77a-9375-4882-8766-8388348abc4c': {'role_id': 1219457467847544931, 'color': discord.Color.from_rgb(133, 223, 204)},  # The Academy's Weakest Became A Demon-Limited Hunter
            '6468040e-a86a-44f8-a14a-7067418fe0a1': {'role_id': 1219457467872968743, 'color': discord.Color.from_rgb(218, 214, 47)},  # Omniscient First-Person's Viewpoint
            '69c2c3c2-ae68-46e7-97d2-b1868b05adc1': {'role_id': 1219457467872968746, 'color': discord.Color.from_rgb(211, 22, 42)},  # Fated To Be Loved By Villains
            '69d6ab1d-4da5-4e84-8ffb-190308540908': {'role_id': 1219457467847544929, 'color': discord.Color.from_rgb(62, 226, 159)},  # Seoul Object Story
            '827757d8-161c-441b-8240-f4dbd7407ce4': {'role_id': 1219457467793145965, 'color': discord.Color.from_rgb(164, 114, 230)},  # My Daughters Are Regressors
            '8da58504-bee5-4807-804a-23215c8a4e7e': {'role_id': 1219457467847544930, 'color': discord.Color.from_rgb(26, 188, 156)},  # City of Witches
            '94683b45-439b-424a-b7f6-76154bcd8750': {'role_id': 1219457467847544923, 'color': discord.Color.from_rgb(13, 108, 223)},  # Pseudo Resident's Illegal Stay in Another World
            '9fe66022-d209-4d2c-9397-beb256982883': {'role_id': 1244241518437601321, 'color': discord.Color.from_rgb(230, 126, 34)},  # Transmigrated Into A Tragic Romance Fantasy
            'a7e499f7-fa6b-4d86-8ee6-1bf6772890f5': {'role_id': 1219457467872968744, 'color': discord.Color.from_rgb(246, 186, 16)},  # Childhood Friend of the Zenith
            'b92c8a56-9538-42e5-9428-0d55a0e1becc': {'role_id': 1219457467793145957, 'color': discord.Color.from_rgb(87, 87, 109)},  # The Heaven-Slaying Sword
            'c0018319-9173-4cc8-9aed-27db5b33fbd0': {'role_id': 1219457467675836435, 'color': discord.Color.from_rgb(17, 16, 16)},  # Becoming Professor Moriarty's Probability
            'd63886fd-b00b-426c-ba94-f5f7186c89d9': {'role_id': 1244241901616627773, 'color': discord.Color.from_rgb(32, 102, 148)},  # The Magic Academy's Physicist
            'e1ee79a1-35f4-40e4-8c0d-f54cb6e1be81': {'role_id': 1219457467847544928, 'color': discord.Color.from_rgb(46, 204, 113)},  # The Villain Who Robbed the Heroines
            'e5cd1c8b-af3d-4975-8166-8865092d2a6a': {'role_id': 1219457467847544927, 'color': discord.Color.from_rgb(140, 234, 246)},  # The Main Heroines are Trying to Kill Me
            'f1cc7b93-ba56-4cf0-9d33-26e62e17c395': {'role_id': 1219457467793145964, 'color': discord.Color.from_rgb(113, 54, 138)},  # Otherworld TRPG Game Master
            'fb2cfad1-9b49-40be-83f5-8cbcd706b0bf': {'role_id': 1219457467793145961, 'color': discord.Color.from_rgb(185, 20, 226)},  # A Love Letter From The Future
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
        embed.url = f"https://genesistudio.com/novels/{abbreviation}"
        
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
