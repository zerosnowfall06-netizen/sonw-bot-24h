import discord
from discord.ext import tasks, commands
from datetime import datetime
import json
import os

intents = discord.Intents.default()
intents.voice_states = True      
intents.message_content = True   
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = 'voice_time.json'
active_sessions = {}

# ⚙️ จุดแก้ไขที่ 1: ใส่ ID ห้องแชทที่ต้องการให้บอทพิมพ์แจ้งเตือนแจกเหรียญ
ALERT_CHANNEL_ID = 1504827909049679882

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                content = json.load(f)
                if "coins" not in content: content["coins"] = {}
                if "time" not in content: content["time"] = {}
                return content
            except json.JSONDecodeError:
                return {"coins": {}, "time": {}}
    return {"coins": {}, "time": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} is silent and monitoring...')
    for guild in bot.guilds:
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                if not member.bot:
                    active_sessions[str(member.id)] = datetime.now()
                    
    if not send_alert.is_running():
        send_alert.start()

# ⏳ ลูปตรวจสอบและแจกเหรียญอัตโนมัติทุก 15 นาที
@tasks.loop(minutes=15)
async def send_alert():
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    data = load_data()
    rewarded_users = []

    for guild in bot.guilds:
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                if member.bot: continue
                
                voice_state = member.voice
                # 🔓 ปรับใหม่: ขอแค่อยู่ในห้องเสียง ( voice_state.channel ) เปิดหรือปิดกล้อง ก็ได้เหรียญหมดทุกคน!
                if voice_state and voice_state.channel:
                    user_id = str(member.id)
                    data["coins"][user_id] = data["coins"].get(user_id, 0) + 1  
                    rewarded_users.append(f"<@{user_id}>")

    save_data(data)

    if channel and rewarded_users:
        user_mentions = ", ".join(rewarded_users)
        await channel.send(f"🟢 **SNOW COIN**\n\n✅ ผู้เล่นที่ออนไลน์ครบครัน : 15 นาที | ได้รับคนละ 1 เหรียญ\nยินดีด้วยกับ: {user_mentions}\nพิมพ์ `!mytime` เพื่อเช็กเหรียญสะสมได้เลย")
    elif channel:
        await channel.send("🟢 **SNOW COIN**\n\nℹ️ ครบรอบ 15 นาทีแล้วจ้า! ตอนนี้ไม่มีใครอยู่ในห้องเสียงเลย")

# ⏱️ ระบบแทร็กเวลา เข้า-ออก ห้องเสียงแบบเรียลไทม์
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    user_id = str(member.id)
    
    if before.channel is None and after.channel is not None:
        active_sessions[user_id] = datetime.now()
    elif before.channel is not None and after.channel is None:
        if user_id in active_sessions:
            join_time = active_sessions.pop(user_id, None)
            if join_time:
                duration = int((datetime.now() - join_time).total_seconds())
                data = load_data()
                data["time"][user_id] = data["time"].get(user_id, 0) + duration
                save_data(data)

# คำสั่งเช็กแต้มสะสม
@bot.command()
async def mytime(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    
    coins_data = data.get("coins", {})
    time_data = data.get("time", {})
    
    coins = coins_data.get(user_id, 0)
    
    current_seconds = 0
    if user_id in active_sessions:
        current_seconds = int((datetime.now() - active_sessions[user_id]).total_seconds())
        
    total_seconds = time_data.get(user_id, 0) + current_seconds
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    await ctx.send(f"🕒 <@{user_id}> คุณมีเหรียญสะสมทั้งหมด: **{coins} เหรียญ**\n🕒 สะสมไว้แล้ว: **{hours} ชม. {minutes} นาที**")

# ⚙️ จุดแก้ไขที่ 2: วางรหัสโทเค็น (Token) บอทของคุณตรงนี้
bot.run(os.getenv('DISCORD_TOKEN'))
