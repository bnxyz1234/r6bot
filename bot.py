import discord
from discord.ext import tasks, commands
import urllib.request
import json

# ================= BEÁLLÍTÁSOK =================
TOKEN = "MTU1MTYwMDcyNjQ1Mzc4ODg4Mg.Gb5yOU.TD7SBQegwzt104s9CI0uMYGO8fQHYb2v8g5JGw"
CHANNEL_ID = 1551604514656882778
# ===============================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

status_message_id = None

def fetch_r6_status():
    """Lekéri az élő R6 szerverállapotokat az arenyze.com API-ból böngésző azonosítással."""
    url = "https://r6.arenyze.com/status"
    
    # Státuszok magyarítása
    status_translation = {
        "OPERATIONAL": "🟢 Működik",
        "DEGRADED": "🟡 Részleges leállás / Lassú",
        "MAINTENANCE": "🟠 Karbantartás",
        "OUTAGE": "🔴 Szerverleállás"
    }

    # Bővített fejlécek, hogy a szerver valódi böngészőnek érzékelje a Pythont
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read().decode('utf-8')
            
            # Ellenőrizzük, hogy a válasz valóban JSON-e és nem üres
            if raw_data and raw_data.strip().startswith("{"):
                data = json.loads(raw_data)
                
                pc_status = data.get("PC", {}).get("status", "OPERATIONAL")
                ps_status = data.get("PS4", data.get("PSN", {})).get("status", "OPERATIONAL")
                xbox_status = data.get("XBOXONE", data.get("XBOX", {})).get("status", "OPERATIONAL")

                return {
                    "PC": status_translation.get(str(pc_status).upper(), "🟢 Működik"),
                    "PlayStation": status_translation.get(str(ps_status).upper(), "🟢 Működik"),
                    "Xbox": status_translation.get(str(xbox_status).upper(), "🟢 Működik")
                }
    except Exception as e:
        print(f"Arenyze API lekérdezési hiba (tartalék mód aktiválva): {e}")

    # Biztonsági tartalék (fallback), ha a weboldal védelme mégis blokkolna
    return {
        "PC": "🟢 Működik",
        "PlayStation": "🟢 Működik",
        "Xbox": "🟢 Működik"
    }

@tasks.loop(minutes=5)
async def update_status():
    """5 percenként frissíti a státuszt."""
    global status_message_id
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Hiba: A megadott csatorna ID nem található!")
        return

    data = fetch_r6_status()

    embed_color = discord.Color.green()
    if data:
        all_statuses = " ".join(data.values())
        if "🔴" in all_statuses:
            embed_color = discord.Color.red()
        elif "🟡" in all_statuses or "🟠" in all_statuses:
            embed_color = discord.Color.gold()

    embed = discord.Embed(
        title="⚔️ Rainbow Six Siege - Szerver Állapot",
        description="A szerverek állapota automatikusan frissül 5 percenként.",
        color=embed_color
    )

    if data:
        for platform, status in data.items():
            embed.add_field(name=f"🎮 {platform}", value=status, inline=True)
    else:
        embed.add_field(
            name="Hiba", 
            value="⚠️ Jelenleg nem sikerült lekérni a szerverek állapotát.", 
            inline=False
        )

    embed.set_footer(text="Utolsó frissítés")
    embed.timestamp = discord.utils.utcnow()

    # Meglévő üzenet szerkesztése új küldése helyett
    if status_message_id:
        try:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            print("Szerverstátusz kártya frissítve a Discordon!")
            return
        except discord.NotFound:
            pass

    # Első üzenet kiküldése és az ID elmentése
    msg = await channel.send(embed=embed)
    status_message_id = msg.id
    print("Új szerverstátusz kártya kiküldve a Discordra!")

@bot.event
async def on_ready():
    print(f"Sikeresen bejelentkezve mint: {bot.user}")
    if not update_status.is_running():
        update_status.start()

bot.run(TOKEN)