import discord
import aiofiles
from colorama import init, Fore
from asyncio import sleep, Event, create_task
from secrets import token_hex
from traceback import format_exc

"ADD TOKEN TO ENABLE YOUR BOT:"

bot_token = ''
bot_code_channel = 0

"TOKEN EDIT END"

init(autoreset=True)
messages = []
discord_user = user = confirm = 0
finish = Event()
client = discord.Client()


async def Login_timeout(client):
    await sleep(15)
    if not confirm:
        global finish
        print(Fore.LIGHTRED_EX + "Login Timeout")
        finish.set()
        await client.close()


async def delete_duplicate():
    code_channel = client.get_channel(bot_code_channel)
    async for message in code_channel.history(limit=None):
        if user == message.content.split(';', 1)[0]:
            await message.delete()

@client.event
async def on_ready():
    global user, password, finishc, code_channel, messages, discord_user, confirm
    async with aiofiles.open('Files/Discord.txt', 'r') as f:
        async for line in f:
            if 'Discord_Username' in line:
                user = (line.replace(' ', '').strip().split('=')[1])
            elif 'Discord_Passcode' in line:
                password = (line.replace(' ', '').strip().split('=')[1])

    if not user:
        await client.close()
        finish.set()
        return

    try:
        code_channel = client.get_channel(bot_code_channel)
        async for message in code_channel.history(limit=None):
            if user == message.content.split(';', 1)[0] and password == message.content.split('=', 1)[1]:
                discord_id = int(message.content.split(';', 1)[1].split('=', 1)[0])
                discord_user = client.get_user(discord_id)
                confirm = 1

        if confirm:
            finish.set()
        else:
            print(f"{Fore.LIGHTYELLOW_EX}Please DM {Fore.LIGHTGREEN_EX}start{Fore.LIGHTYELLOW_EX} to NovaNotifier")
            create_task(Login_timeout(client))

    except:
        print(format_exc())


@client.event
async def on_message(message):
    global confirm, discord_user, finish
    if f"{message.author.name}#{message.author.discriminator}" == user and not message.guild:
        if message.content == 'start':
            await delete_duplicate()
            discord_user = client.get_user(message.author.id)
            code = token_hex(3)
            await code_channel.send(f"{discord_user.name}#{discord_user.discriminator};{discord_user.id}={code}")
            msg = (await discord_user.send(f"Discord Activated\nDiscord Passcode: {code}"))
            await msg.pin()
            async with aiofiles.open('Files/Discord.txt', 'w+') as f:
                await f.write(f"Discord_Username = {user}\nDiscord_Passcode = {code}")
            confirm = 1
            finish.set()
