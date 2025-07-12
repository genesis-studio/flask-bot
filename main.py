import discord
from discord.ext import commands
from quart import Quart, jsonify, request
import asyncio
import os
from discord.ext import tasks
import aiohttp  # You'll need to install this: pip install aiohttp
from supabase import create_client, Client

# Attempt to import praw
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    print("Warning: praw module not found. Reddit functionality will be disabled.")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Quart app setup
app = Quart(__name__)

# Supabase setup
supabase_url = os.environ.get('SUPABASE_URL')
supabase_anon_key = os.environ.get('PUBLIC_SUPABASE_ANON_KEY')
supabase: Client = create_client(supabase_url, supabase_anon_key)

# Discord channel IDs (replace with your actual channel IDs)
CHANNEL_IDS = {
    'test-release':1262212983426125835,
    'release': 1219457468011380892
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

async def get_novel_role_info(novel_id):
    """Fetch role info for a novel from Supabase"""
    try:
        response = supabase.table('novel_roles').select('role,hex').eq('novel', novel_id).execute()
        if response.data:
            data = response.data[0]
            return {
                'role_id': int(data['role']),
                'color': hex_to_rgb(data['hex'])
            }
        return None
    except Exception as e:
        print(f"Error fetching novel role info: {e}")
        return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    call_analytics.start()  # Start the scheduled task

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
    
    return jsonify({
        'status': 'success',
        'message': 'Message sent',
        'channel': channel_name,
        'channel_id': channel_id,
        'novel_title': data.get('novel_title'),
        'chapter_number': data.get('chapter_number'),
        'chapter_title': data.get('chapter_title'),
        'chapter_id': data.get('chapter_id'),
        'novel_id': data.get('novel_id')
    }), 200

async def send_discord_message(channel_id, novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, novel_id, cover_id, abbreviation):
    channel = bot.get_channel(channel_id)
    if channel:
        # Fetch role info from Supabase
        role_info = await get_novel_role_info(novel_id)
        
        role_id = None
        embed_color = discord.Color.default()
        
        if role_info:
            role_id = role_info.get('role_id')
            color_rgb = role_info.get('color')
            if color_rgb:
                embed_color = discord.Color.from_rgb(*color_rgb)
        
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

        # # Post to Reddit only if praw is available
        # if PRAW_AVAILABLE:
        #     await post_to_reddit(novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, abbreviation, cover_id)
        # else:
        #     print("Skipping Reddit post due to missing praw module.")

# async def post_to_reddit(novel_title, chapter_number, chapter_title, chapter_id, free_chapter_number, free_chapter_title, free_chapter_id, abbreviation, cover_id):
#     if not PRAW_AVAILABLE:
#         print("Cannot post to Reddit: praw module is not available.")
#         return

#     # Reddit API credentials
#     client_id = 'I_KzFNWGpvgB4eK9547nPg'
#     client_secret = 'Q1OfzN_mUd-X4qkiJzOX-44C2BvPWw'
#     username = 'genesis_studio'
#     password = 'GenesisStudioTL13!'
#     user_agent = 'Genesis/0.1'

#     # Initialize the Reddit instance
#     reddit = praw.Reddit(
#         client_id=client_id,
#         client_secret=client_secret,
#         user_agent=user_agent,
#         username=username,
#         password=password
#     )

#     subreddit_name = 'GenesisStudio'
#     title = f"New Release: {novel_title}"
#     content = (
#         f"New chapters for {novel_title} are now available!\n\n"
#         f"Premium Chapter:\n"
#         f"{chapter_number} - {chapter_title}\n"
#         f"https://genesistudio.com/viewer/{chapter_id}\n\n"
#         f"Free Chapter:\n"
#         f"{free_chapter_number} - {free_chapter_title}\n"
#         f"https://genesistudio.com/viewer/{free_chapter_id}\n\n"
#         f"Read more at: https://genesistudio.com/novels/{abbreviation}"
#     )

#     try:
#         # Get the subreddit
#         subreddit = reddit.subreddit(subreddit_name)
        
#         # Create the post
#         if cover_id:
#             cover_url = f"https://edit.genesistudio.com/assets/{cover_id}"
#             post = subreddit.submit(title=title, selftext=content, url=cover_url)
#         else:
#             post = subreddit.submit(title=title, selftext=content)
        
#         print(f"Reddit post created successfully! URL: {post.url}")
#     except praw.exceptions.RedditAPIException as e:
#         print(f"An error occurred while posting to Reddit: {e}")

#     # Wait for 1-0- minute(s) before the next potential post (to comply with rate limits)
#     await asyncio.sleep(60)

@tasks.loop(minutes=5)
async def call_analytics():
    """Run analytics worker every 5 minutes"""
    try:
        from analytics_worker import run_analytics_worker
        result = await run_analytics_worker()
        if result.get("success"):
            print("Analytics worker completed successfully")
        else:
            print(f"Analytics worker failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error running analytics worker: {e}")

@call_analytics.before_loop
async def before_analytics():
    await bot.wait_until_ready()

async def start_bot():
    await bot.start(os.environ["DISCORD_TOKEN"])

@app.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
