import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import datetime

# 1. 봇의 기본 설정 및 필수 인텐트 활성화
intents = discord.Intents.default()
intents.members = True          # 신규 멤버 감지 및 자동 DM에 필수
intents.message_content = True  # 메시지 내용 읽기 및 필터링 권한

# [5번 기능] 욕설 및 금지어 필터링 리스트
BAD_WORDS = ["바보", "멍청이", "비속어텍스트"]

# [32번 기능] 서버 채널 구조를 임시 저장할 데이터베이스
server_backups = {}

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("[-] 슬래시 명령어 동기화 완료!")

bot = MyBot()

# [10번 기능 Helper] 실시간 멤버 수 채널 이름 업데이트 함수
async def update_member_count_channel(guild: discord.Guild):
    for channel in guild.voice_channels:
        if "전체 멤버:" in channel.name:
            await channel.edit(name=f"👥 전체 멤버: {guild.member_count}명")
            break

@bot.event
async def on_ready():
    print(f'[-] 로그인 성공: {bot.user.name} (ID: {bot.user.id})')
    print('[-] 봇이 정상적으로 작동 중입니다.')
    print('-----------------------------------------')
    for guild in bot.guilds:
        await update_member_count_channel(guild)

# ================= [ 기존 기능 1: 공지 ] =================
@bot.tree.command(name="공지", description="공지사항 채널에 예쁜 임베드 형태로 공지를 작성합니다.")
@app_commands.describe(제목="공지 제목을 입력하세요", 내용="공지 내용을 입력하세요")
async def notice(interaction: discord.Interaction, 제목: str, 내용: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 권한(관리자)이 없습니다.", ephemeral=True)
        return
    embed = discord.Embed(title=f"📢 {제목}", description=내용, color=0xff0000)
    embed.set_footer(text=f"작성자: {interaction.user.display_name}")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ 공지가 성공적으로 발송되었습니다.", ephemeral=True)

# ================= [ 기존 기능 2: 메시지 ] =================
@bot.tree.command(name="메시지", description="봇이 현재 채널에 일반 메시지를 대리 전송합니다.")
@app_commands.describe(내용="보낼 메시지 내용")
async def send_msg(interaction: discord.Interaction, 내용: str):
    await interaction.channel.send(내용)
    await interaction.response.send_message("✅ 메시지를 전송했습니다.", ephemeral=True)

# ================= [ 기존 기능 3: 자동 DM (신규 유저 환영) ] =================
@bot.event
async def on_member_join(member: discord.Member):
    try:
        await member.send(f"안녕하세요 {member.mention}님! **{member.guild.name}** 서버에 오신 것을 환영합니다! 🎉\n공지사항 채널을 꼭 확인해 주세요!")
    except discord.Forbidden:
        print(f"[경고] {member.name}님이 DM을 차단하여 자동 DM을 전송하지 못했습니다.")
    await update_member_count_channel(member.guild)

@bot.event
async def on_member_remove(member: discord.Member):
    await update_member_count_channel(member.guild)

# ================= [ 기존 기능 4: 타겟 DM ] =================
@bot.tree.command(name="타겟dm", description="특정 유저에게 봇의 이름으로 DM을 보냅니다.")
@app_commands.describe(유저="DM을 받을 유저 선택", 내용="보낼 메시지 내용")
async def target_dm(interaction: discord.Interaction, 유저: discord.User, 내용: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
        return
    try:
        await 유저.send(f"📩 **관리자로부터 온 메시지:**\n\n{내용}")
        await interaction.response.send_message(f"✅ {유저.mention}님에게 DM 전송 완료!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {유저.mention}님이 DM을 차단해두어 보낼 수 없습니다.", ephemeral=True)

# ================= [ 기존 기능 5: 다른 유저인 척 메시지 (웹훅 기능) ] =================
@bot.tree.command(name="가짜메시지", description="특정 유저의 이름과 프로필 사진을 복사하여 메시지를 보냅니다.")
@app_commands.describe(유저="흉내낼 유저 선택", 내용="보낼 메시지 내용")
async def fake_msg(interaction: discord.Interaction, 유저: discord.Member, 내용: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
        return
    await interaction.response.send_message("🔄 메시지 변장 전송 중...", ephemeral=True)
    webhook = await interaction.channel.create_webhook(name=유저.display_name)
    try:
        await webhook.send(content=내용, username=유저.display_name, avatar_url=get_avatar_url(유저))
    finally:
        await webhook.delete()

def get_avatar_url(user):
    return user.avatar.url if user.avatar else user.default_avatar.url

# ================= [ 01. 기존 추가 기능: 채팅 청소 ] =================
@bot.tree.command(name="청소", description="지정한 개수만큼 현재 채널의 메시지를 일괄 삭제합니다.")
@app_commands.describe(개수="삭제할 메시지 개수 (1~100)")
async def clear_chat(interaction: discord.Interaction, 개수: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ 메시지 관리 권한이 없습니다.", ephemeral=True)
        return
    if 개수 < 1 or 개수 > 100:
        await interaction.response.send_message("❌ 1개부터 100개 사이의 개수를 지정해 주세요.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=개수)
    await interaction.followup.send(f"🗑️ 성공적으로 {len(deleted)}개의 메시지를 삭제했습니다.", ephemeral=True)

# ================= [ 02. 기존 추가 기능: 유저 뮤트 ] =================
@bot.tree.command(name="뮤트", description="지정한 시간(분) 동안 유저가 채팅을 치지 못하게 설정합니다.")
@app_commands.describe(유저="뮤트할 유저", 시간="뮤트 시간 (분 단위)")
async def mute_user(interaction: discord.Interaction, 유저: discord.Member, 시간: int):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ 멤버 관리(뮤트) 권한이 없습니다.", ephemeral=True)
        return
    duration = timedelta(minutes=시간)
    try:
        await 유저.timeout(duration, reason=f"관리자 {interaction.user.name}에 의한 뮤트")
        await interaction.response.send_message(f"🤫 {유저.mention}님이 {시간}분 동안 뮤트 처리되었습니다.")
    except Exception as e:
        await interaction.response.send_message(f"❌ 뮤트 처리에 실패했습니다: {e}", ephemeral=True)

# ================= [ 05. 기존 추가 기능: 금지어 자동 필터링 ] =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    for word in BAD_WORDS:
        if word in message.content:
            try:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}님, 사용 금지어가 포함되어 있어 메시지가 삭제되었습니다.", delete_after=5)
            except discord.Forbidden:
                print("[오류] 메시지 삭제 권한이 없습니다.")
            return
    await bot.process_commands(message)

# ================= [ 06. 기존 추가 기능: 실시간 관리자 로그 ] =================
@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return
    log_channel = discord.utils.get(message.guild.text_channels, name="봇-로그")
    if log_channel:
        embed = discord.Embed(title="🗑️ 메시지 삭제됨", color=0xff0000, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="작성자", value=message.author.mention, inline=True)
        embed.add_field(name="채널", value=message.channel.mention, inline=True)
        embed.add_field(name="내용", value=message.content if message.content else "(내용 없음 또는 파일)", inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or before.content == after.content:
        return
    log_channel = discord.utils.get(before.guild.text_channels, name="봇-로그")
    if log_channel:
        embed = discord.Embed(title="✏️ 메시지 수정됨", color=0xffa500, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="작성자", value=before.author.mention, inline=True)
        embed.add_field(name="채널", value=before.channel.mention, inline=True)
        embed.add_field(name="수정 전", value=before.content, inline=False)
        embed.add_field(name="수정 후", value=after.content, inline=False)
        await log_channel.send(embed=embed)

# ================= [ 08. 기존 추가 기능: 서버 정보 조회 ] =================
@bot.tree.command(name="서버정보", description="현재 디스코드 서버의 상세 정보를 보여줍니다.")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name} 서버 정보", color=0x00ff00)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 서버 주인", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="👥 전체 멤버 수", value=f"{guild.member_count}명", inline=True)
    embed.add_field(name="📆 서버 생성일", value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name="🚀 부스트 레벨", value=f"레벨 {guild.premium_tier} ({guild.premium_subscription_count}개 부스트)", inline=True)
    embed.set_footer(text=f"서버 ID: {guild.id}")
    await interaction.response.send_message(embed=embed)

# ================= [ 09. 기존 추가 기능: 유저 정보 조회 ] =================
@bot.tree.command(name="유저정보", description="특정 유저의 가입일 및 권한 상태를 확인합니다.")
@app_commands.describe(유저="확인할 유저 선택 (비워두면 본인)")
async def user_info(interaction: discord.Interaction, 유저: discord.Member = None):
    target = 유저 if 유저 else interaction.user
    embed = discord.Embed(title=f"👤 {target.display_name} 유저 정보", color=0x0000ff)
    embed.set_thumbnail(url=get_avatar_url(target))
    embed.add_field(name="태그", value=str(target), inline=True)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="디스코드 가입일", value=target.created_at.strftime('%Y-%m-%d'), inline=False)
    embed.add_field(name="서버 입장일", value=target.joined_at.strftime('%Y-%m-%d') if target.joined_at else "알 수 없음", inline=False)
    roles = [role.mention for role in target.roles if role != interaction.guild.default_role]
    embed.add_field(name=f"보유 역할 ({len(roles)})", value=" ".join(roles) if roles else "보유 역할 없음", inline=False)
    await interaction.response.send_message(embed=embed)

# ================= [ 14. 기존 추가 기능: 투표 시스템 ] =================
@bot.tree.command(name="투표", description="간단한 선택지 투표 창을 생성합니다.")
@app_commands.describe(주제="투표할 주제", 선택지1="첫 번째 선택지", 선택지2="두 번째 선택지", 선택지3="세 번째 선택지 (선택)", 선택지4="네 번째 선택지 (선택)")
async def create_poll(interaction: discord.Interaction, 주제: str, 선택지1: str, 선택지2: str, 선택지3: str = None, 선택지4: str = None):
    emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    description = f"1️⃣ : {선택지1}\n2️⃣ : {선택지2}"
    count = 2
    if 선택지3:
        description += f"\n3️⃣ : {선택지3}"
        count += 1
    if 선택지4:
        description += f"\n4️⃣ : {선택지4}"
        count += 1
    embed = discord.Embed(title=f"📊 투표: {주제}", description=description, color=0x800080)
    embed.set_footer(text=f"제안자: {interaction.user.display_name}")
    await interaction.response.send_message("✅ 투표를 생성했습니다.", ephemeral=True)
    poll_msg = await interaction.channel.send(embed=embed)
    for i in range(count):
        await poll_msg.add_reaction(emoji_list[i])

# ================= [ 32. 기존 추가 기능: 서버 백업 및 복구 ] =================
@bot.tree.command(name="백업", description="현재 서버의 카테고리 및 채널 구조를 봇에 백업합니다.")
async def backup_server(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    structure = []
    for category in guild.categories:
        cat_data = {"name": category.name, "type": "category", "channels": []}
        for channel in category.channels:
            ch_type = "text" if isinstance(channel, discord.TextChannel) else "voice"
            cat_data["channels"].append({"name": channel.name, "type": ch_type})
        structure.append(cat_data)
    for channel in guild.channels:
        if channel.category is None:
            ch_type = "text" if isinstance(channel, discord.TextChannel) else "voice"
            if not isinstance(channel, discord.CategoryChannel):
                structure.append({"name": channel.name, "type": ch_type, "category_none": True})
    server_backups[guild.id] = structure
    await interaction.response.send_message("💾 현재 서버의 채널 레이아웃 백업이 완료되었습니다!")

@bot.tree.command(name="복구", description="백업된 구조를 바탕으로 서버에 채널들을 재생성합니다.")
async def restore_server(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    guild = interaction.guild
    if guild.id not in server_backups:
        await interaction.response.send_message("❌ 이 서버에 저장된 백업 데이터가 없습니다.", ephemeral=True)
        return
    await interaction.response.send_message("🔄 백업 데이터를 기반으로 채널 구조 복구를 시작합니다...", ephemeral=True)
    data = server_backups[guild.id]
    for item in data:
        if item.get("type") == "category":
            category = await guild.create_category(name=item["name"])
            for ch in item["channels"]:
                if ch["type"] == "text":
                    await guild.create_text_channel(name=ch["name"], category=category)
                else:
                    await guild.create_voice_channel(name=ch["name"], category=category)
        elif item.get("category_none"):
            if item["type"] == "text":
                await guild.create_text_channel(name=item["name"])
            else:
                await guild.create_voice_channel(name=item["name"])

# ================= [ 44. 신규 기능: 채널 잠금/해제 ] =================
@bot.tree.command(name="잠금", description="현재 채널의 채팅 기능을 잠그거나 해제합니다.")
@app_commands.describe(상태="채널의 잠금 상태를 선택하세요")
@app_commands.choices(상태=[
    app_commands.Choice(name="🔒 채널 잠금", value="lock"),
    app_commands.Choice(name="🔓 잠금 해제", value="unlock")
])
async def lock_channel(interaction: discord.Interaction, 상태: app_commands.Choice[str]):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ 채널 관리 권한이 없습니다.", ephemeral=True)
        return
    
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)

    if 상태.value == "lock":
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔒 관리자가 현재 채널을 잠궜습니다. 일반 유저는 더 이상 채팅을 칠 수 없습니다.")
    else:
        overwrite.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message("🔓 현재 채널의 잠금이 해제되었습니다. 이제 채팅이 가능합니다.")

# ================= [ 49. 신규 기능: 스포방지 대리 전송 ] =================
@bot.tree.command(name="스포방지", description="중요한 스포일러 내용을 숨김처리하여 안전하게 전송합니다.")
@app_commands.describe(메시지="스포일러 방지 처리할 핵심 내용")
async def spoiler_msg(interaction: discord.Interaction, 메시지: str):
    # 유저가 친 원래 명령어 자체를 다른 사람 눈에 안 띄게 숨김 처리하며 전송 시작
    await interaction.response.send_message("✅ 스포방지 메시지를 출력합니다.", ephemeral=True)
    
    # 예쁜 박스(임베드) 형태로 스포일러 감옥 전송
    embed = discord.Embed(
        title="⚠️ 스포일러 경고!", 
        description=f"작성자: {interaction.user.mention}\n\n👇 아래 상자를 누르면 내용이 보입니다.\n|| {메시지} ||", 
        color=0x36393f
    )
    await interaction.channel.send(embed=embed)

# ⚠️ 디스코드 봇 토큰 입력
BOT_TOKEN = "MTUwOTE5NjIwMDI3NTA4MzM2NA.GPhw5H.E2MeR4gbAvdOzHLS54xvrUK5Id7tW0BrQhPX38"

bot.run(BOT_TOKEN)
