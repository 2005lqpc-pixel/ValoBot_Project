import discord
from discord.ext import commands, tasks
import os
import json
import requests
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
VALO_KEY = os.getenv("VALO_API_KEY")

CHANNEL_ID = 1501420477091156019
ROLE_ID = 1501426409632039032


class ValorantBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.last_match = {}

    async def setup_hook(self):
        self.match_loop.start()

    async def on_ready(self):
        print(f"Logged in as {self.user}")


bot = ValorantBot()


@bot.command()
async def track(ctx, name: str, tag: str):
    if not os.path.exists("tracked_players.json"):
        with open("tracked_players.json", "w") as f:
            json.dump({}, f)

    with open("tracked_players.json", "r") as f:
        data = json.load(f)

    data[f"{name}#{tag}"] = {"name": name, "tag": tag}

    with open("tracked_players.json", "w") as f:
        json.dump(data, f, indent=4)

    await ctx.send(f"Tracking {name}#{tag}")


@tasks.loop(seconds=60)
async def match_loop():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    if not os.path.exists("tracked_players.json"):
        return

    with open("tracked_players.json", "r") as f:
        players = json.load(f)

    for p_id, info in players.items():
        try:
            url = f"https://api.henrikdev.xyz/valorant/v3/matches/na/{info['name']}/{info['tag']}"
            headers = {"Authorization": VALO_KEY}

            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                continue

            data = r.json().get("data")
            if not data:
                continue

            match = data[0]
            match_id = match["metadata"]["matchid"]

            if bot.last_match.get(p_id) == match_id:
                continue

            bot.last_match[p_id] = match_id

            players_list = match["players"]["all_players"]

            agent = None
            for p in players_list:
                if p["name"].lower() == info["name"].lower():
                    agent = p.get("character")
                    break

            if not agent:
                continue

            map_name = match["metadata"].get("map", "Unknown")
            mode = match["metadata"].get("mode", "Unknown")

            await channel.send(
                f"🚨 <@&{ROLE_ID}> {p_id} entered a match\n"
                f"Agent: {agent}\n"
                f"Map: {map_name}\n"
                f"Mode: {mode}"
            )

            await asyncio.sleep(2)

        except:
            continue


@match_loop.before_loop
async def before_loop():
    await bot.wait_until_ready()


bot.run(TOKEN)