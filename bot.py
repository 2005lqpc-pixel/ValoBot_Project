import discord
from discord.ext import commands, tasks
import json
import os
import time
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

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.active_matches = {}

    async def setup_hook(self):
        await self.add_cog(ValorantCog(self))
        print("Bot running")

    async def on_ready(self):
        print(f"Logged in as {self.user}")


class ValorantCog(commands.Cog):
    def __init__(self, bot: ValorantBot):
        self.bot = bot

        if not os.path.exists("tracked_players.json"):
            with open("tracked_players.json", "w") as f:
                json.dump({}, f)

        self.check_loop.start()

    @commands.command()
    async def help(self, ctx):
        await ctx.send("Commands: !track <name> <tag>")

    @commands.command()
    async def track(self, ctx, name: str, tag: str):
        with open("tracked_players.json", "r") as f:
            data = json.load(f)

        player_id = f"{name}#{tag}"
        data[player_id] = {"name": name, "tag": tag}

        with open("tracked_players.json", "w") as f:
            json.dump(data, f, indent=4)

        await ctx.send(f"Tracking {player_id}")

    def get_rank(self, name, tag):
        url = f"https://api.henrikdev.xyz/valorant/v2/mmr/na/{name}/{tag}"
        headers = {"Authorization": VALO_KEY}

        try:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                return "Unknown"

            data = r.json()["data"]

            rank = data.get("currenttierpatched", "Unknown")
            rr = data.get("ranking_in_tier", 0)

            return f"{rank} ({rr} RR)"

        except:
            return "Unknown"

    @tasks.loop(seconds=60)
    async def check_loop(self):
        channel = self.bot.get_channel(CHANNEL_ID)
        if not channel:
            return

        try:
            with open("tracked_players.json", "r") as f:
                players = json.load(f)
        except:
            return

        for p_id, info in players.items():
            url = f"https://api.henrikdev.xyz/valorant/v3/matches/na/{info['name']}/{info['tag']}"
            headers = {"Authorization": VALO_KEY}

            try:
                r = requests.get(url, headers=headers)
                if r.status_code != 200:
                    continue

                data = r.json().get("data")
                if not data:
                    continue

                match = data[0]
                match_id = match["metadata"]["matchid"]

                if self.bot.active_matches.get(p_id) == match_id:
                    continue

                self.bot.active_matches[p_id] = match_id

                meta = match["metadata"]

                map_name = meta.get("map", "Unknown")
                mode = meta.get("mode", "Unknown")

                agent = "Unknown"
                for p in match["players"]["all_players"]:
                    if p["name"].lower() == info["name"].lower():
                        agent = p.get("character", "Unknown")
                        break

                rank = self.get_rank(info["name"], info["tag"])

                await channel.send(
                    f"""🚨 <@&{ROLE_ID}> MATCH FOUND
👤 Player: {p_id}
🗺 Map: {map_name}
🎮 Mode: {mode}
🎯 Agent: {agent}
🏆 Rank: {rank}"""
                )

                await asyncio.sleep(2)

            except Exception as e:
                print("Loop error:", e)


bot = ValorantBot()
bot.run(TOKEN)