import discord as selfdiscord
from discord.ext import commands
import sys
import io
import re
import os
import requests
from os.path import exists
from PIL import Image
from datetime import datetime
sys.path.append(".")

'''
IMPORTANT
install development version of discord.py-self:
$ git clone https://github.com/dolfies/discord.py-self
$ cd discord.py-self
$ python3 -m pip install -U .[voice]
'''

#initialization
client = commands.Bot(command_prefix='cl',self_bot = True, request_guilds = False, member_cache_flags = selfdiscord.MemberCacheFlags.none())
client.remove_command('help')


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(status=selfdiscord.Status.invisible, edit_settings= False, afk=True)


#commands
@client.command()
async def help(ctx):
    if ctx.message.author != client.user:
        return
    
    help_list = "mke [emoji_url, emoji_name]\nmks [message_id, sticker_name]\nmv [old_name, new_name]\nlistdir [opt: search]\nrm [filename+.(filetype)]"
    await ctx.send(help_list)


@client.command()
#note that you can manually add emojis in the folder but caution with casing as linux filesystem are case-senstitive
async def mke(ctx, emoji_url, emoji_name):
    if ctx.message.author != client.user:
        return
    
    #creates directory if it doesn't exist yet
    if not exists("Emotes"):
        os.mkdir("Emotes")


    filepath = f"Emotes/{emoji_name.lower()}.png"
    response = requests.get(emoji_url)
    if response.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(response.content)
    else:
        await ctx.send("Failed to download the sticker.")
        return
    
    #resize sticker
    try:
        with Image.open(filepath) as img:
            img = img.resize((48, 48))
            img.save(filepath)
    except Exception as e:
        await ctx.send(f"An error occurred while resizing: {e}")

    await ctx.message.delete()
    await ctx.send(file=selfdiscord.File(filepath, filename="emote.png"))


@mke.error
async def mke_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid.")


@client.command()
async def mks(ctx, message_id: int, sticker_name):
    if ctx.message.author != client.user:
        return
    
    #creates directory if it doesn't exist yet
    if not exists("Emotes"):
        os.mkdir("Emotes")

    msg_obj = await ctx.fetch_message(message_id)
    #checks if msg has stickers
    if not msg_obj.stickers:
        await ctx.send("stickern't")
        return
    else:
        sticker_url = msg_obj.stickers[0].url

    # Download and save the sticker
    sticker_path = f"Emotes/{sticker_name.lower()}_sticker.png"
    response = requests.get(sticker_url)
    if response.status_code == 200:
        with open(sticker_path, "wb") as f:
            f.write(response.content)
    else:
        await ctx.send("Failed to download the sticker.")
        return
    
    #resize sticker
    try:
        with Image.open(sticker_path) as img:
            img = img.resize((160, 160))
            img.save(sticker_path)
    except Exception as e:
        await ctx.send(f"An error occurred while resizing: {e}")
    
    await ctx.message.delete()
    await ctx.send(file=selfdiscord.File(sticker_path, filename="emote.png"))


@mks.error
async def mks_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid.")


@client.command()
async def mv(ctx, old_name, new_name):
    if ctx.message.author != client.user:
        return
    
    os.rename("Emotes/" + old_name + ".png", "Emotes/" + new_name + ".png")
    await ctx.delete(ctx.message)
    await ctx.send(old_name + ".png" + " -> " + new_name + ".png", delete_after = 5)


@client.command()
async def listdir(ctx, search = None):
    if ctx.message.author != client.user:
        return
    
    dir_iterator = os.scandir("Emotes")
    dir_string_list = ""

    for i, dir in enumerate(dir_iterator):
        if i > 15: #prevents from listing too much if unfiltered
            break
        if search:
            if search not in dir.name:
                continue

        dir_stat = dir.stat()
        name = dir.name
        byte_size = dir_stat.st_size
        modified_time = dir_stat.st_mtime
        modified_time_date = datetime.utcfromtimestamp(modified_time).strftime('%Y-%m-%d')
        dir_string_list += f"{name:<30}{str(round(byte_size/1000, 2)) + ' KB':<10} {modified_time_date}\n"
    await ctx.send(dir_string_list, delete_after = 15)


@client.command()
async def rm(ctx, name):
    if ctx.message.author != client.user:
        return
    
    os.remove(f"Emotes/{name}")
    await ctx.message.edit(ctx.message + '- ✅')


#events
@client.event
async def on_message(message):
    if message.author != client.user:
        return
    str_msg = message.content
    message_channel = message.channel

    #searches for the pattern of an actual emote and when it finds one, just return the function(no processing needed)
    has_actual_emoji = re.search(r'<:\w*:\d*>', str_msg)
    if has_actual_emoji is not None:
        return

    #bot can only process one emote per message as with the limitation of how image are displayed in discord and is coded as such:
    if str_msg.find(":") != str_msg.rfind(":"):
        emote_begin = str_msg.find(":")
        emote_end = str_msg.rfind(":")
        emote = str_msg[emote_begin+1:emote_end]

        image = find_image(emote)
        if image == None:
            return
        
        if str_msg[:emote_begin] + str_msg[emote_end+1:] == "": #if empty message after stripping the emote
            await message.delete()
        else:
            await message.edit(str_msg[:emote_begin] + str_msg[emote_end+1:])
        await message_channel.send(file=selfdiscord.File(image, filename="emote.png"))

    await client.process_commands(message)


def find_image(emote):
    #initialization check for sticker flag
    is_sticker = False
    if emote[0] == "!":
        is_sticker = True
        emote = emote[1:]
    
    
    if is_sticker:
        filepath_sticker = f"Emotes/{emote.lower()}_sticker.png"
        if not exists(filepath_sticker):
            return
        image = Image.open(filepath_sticker)

    else:
        filepath = f"Emotes/{emote.lower()}.png"
        if not exists(filepath):
            return
        image = Image.open(filepath)
        if image.size != (48, 48):
            image = image.resize((48, 48))
            image.save(filepath)

    image_binary = io.BytesIO()
    image.save(image_binary, format="PNG")
    image_binary.seek(0)
    image.close()
    return image_binary


#replace os.getenv("TOKEN") with your user token.
client.run(os.getenv("TOKEN"))
