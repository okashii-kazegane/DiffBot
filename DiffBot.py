# Python 3.6
import discord
from discord.ext import commands
import re
import sys
import os
from pathlib import Path
import json
import secrets
import random
import time
import dropbox

if len(sys.argv) >= 2:
    TOKEN = sys.argv[1]
else:
    TOKEN = os.environ['DIFFBOT_TOKEN']

if len(sys.argv) == 3:
    DROPBOX_TOKEN = sys.argv[2]
else:
    DROPBOX_TOKEN = os.environ['DROPBOX_TOKEN']

dbx = dropbox.Dropbox(DROPBOX_TOKEN)

json_diffconfig_file_name = "diffconfig.json"

dbxFolderName = '/DiffBotData'

diffbot = commands.Bot(command_prefix='diffbot.', max_messages=20000000)


@diffbot.event
async def on_ready():
    print('Logged in as')
    print(diffbot.user.name)
    print(diffbot.user.id)
    print('------')
    random.seed(time.time())





def dropbox_upload_config(guild, file_name):
    with open(Path(guild.name, file_name), 'rb') as f:
        dbx.files_upload(f.read(),dbxFolderName+'/'+str(guild.name)+'/'+file_name, mode=dropbox.files.WriteMode.overwrite, mute=True)

def dropbox_download_config(guild, file_name):
    dbx.files_download_to_file(Path(guild.name, file_name), dbxFolderName+'/'+str(guild.name)+'/'+file_name)

async def setup_diffconfig(guild):
    if not os.path.exists(str(guild.name)):
        try:
            os.makedirs(str(guild.name))
            dropbox_download_config(guild, json_diffconfig_file_name)
        except:
            default_diffconfig = dict()
            default_diffconfig['log_channel_id'] = secrets.token_urlsafe(24)
            with open(Path(guild.name, json_diffconfig_file_name), 'w+') as diffconfig_file:
                json.dump(default_diffconfig, diffconfig_file)
            dropbox_upload_config(guild, json_diffconfig_file_name)

async def get_diffconfig(guild):
    await setup_diffconfig(guild)
    with open(Path(guild.name, json_diffconfig_file_name), 'r') as diffconfig_file:
        diffconfig = json.load(diffconfig_file)
    return diffconfig

async def update_diffconfig(guild, diffconfig):
    with open(Path(guild.name, json_diffconfig_file_name), 'w+') as diffconfig_file:
        json.dump(diffconfig, diffconfig_file)
    dropbox_upload_config(guild, json_diffconfig_file_name)





async def embedMessage(channel, titleStr, nameStr, valueStr):
    retStr = str("""```css\n{}```""".format(valueStr))
    embed = discord.Embed(title=titleStr)
    embed.add_field(name=nameStr,value=retStr)
    await channel.send(embed=embed)

async def is_author_guild_admin(ctx):
    if not ctx.message.author.guild_permissions.administrator:
        await ctx.message.channel.send( "You do not have sufficient permissions.")
        return False
    else:
        return True

@diffbot.command()
async def info(ctx):
    if not await is_author_guild_admin(ctx):
        return
    await ctx.send(("Hello, I am DiffBot.  I am a bot built to help record edits on your guild. \n"
                    "For more info, you can visit my website at http://diffbot.rain-ffxiv.com\n"
                    "If you have any issues, email oka@rain-ffxiv.com\n\n"
                    "__**Administrator commands:**__\n"
                    " - **diffbot.info** - that's this command!\n"
                    " - **diffbot.set_log_channel *#channel-mention*** - Bot will log edits and deletions in the specified channel.\n\n"))

def stripChannelMention(mention):
    if mention.startswith('<#') and mention.endswith('>'):
        mention = mention[2:-1]
    return int(mention)





@diffbot.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == diffbot.user:
        return

    await diffbot.process_commands(message)


@diffbot.event
async def on_message_edit(before, after):
    diffconfigs = await get_diffconfig(before.guild)
    log_channel = diffbot.get_channel(int(diffconfigs['log_channel_id']))
    if log_channel is not None:
        if before.channel.id == log_channel.id:
            return
        if before.content != after.content:
            titleStr = "{} has edited a message in the {} channel ".format(before.author,
                                                                           before.channel)
            nameStr = before.content
            valueStr = after.content
            try:
                await embedMessage(log_channel, titleStr, nameStr, valueStr)
            except:
                await log_channel.send("__**{} has edited a message in the {} channel**__".format(before.author,
                                                                                                  before.channel))
                await log_channel.send("*{}*".format(before.content))
                await log_channel.send("**{}**".format(after.content))

@diffbot.event
async def on_raw_message_edit(payload):
    editChannel = diffbot.get_channel(payload.channel_id)
    editGuild = editChannel.guild
    diffconfigs = await get_diffconfig(editGuild)
    log_channel = diffbot.get_channel(int(diffconfigs['log_channel_id']))
    if log_channel is not None:
        if payload.channel_id == log_channel.id:
            return
        if payload.cached_message is not None and payload.cached_message.content and payload.cached_message.content.strip():
            #titleStr = "{} has edited a message in the {} channel ".format(payload.cached_message.author,
            #                                                               payload.cached_message.channel)
            #valueStr = payload.cached_message.content
            #nameStr = "Cached message:"#str(payload.data)
            #try:
            #    await embedMessage(log_channel, titleStr, nameStr, valueStr)
            #except:
            #    await log_channel.send("__**{} has edited a message in the {} channel**__".format(payload.cached_message.author,
            #                                                                               payload.cached_message.channel))
            #    await log_channel.send("**{}**".format(payload.cached_message.content))
            #    #await log_channel.send("*{}*".format(str(payload.data)))
            return
        else:
            await log_channel.send("**An uncached message was edited in the channel <#{}>**".format(payload.channel_id, payload.channel_id))      

@diffbot.event
async def on_raw_message_delete(payload):
    diffconfigs = await get_diffconfig(diffbot.get_guild(payload.guild_id))
    log_channel = diffbot.get_channel(int(diffconfigs['log_channel_id']))
    if log_channel is not None:
        if payload.channel_id == log_channel.id:
            return
        if payload.cached_message is not None and payload.cached_message.content and payload.cached_message.content.strip():
            titleStr = "{} has deleted a message in the {} channel ".format(payload.cached_message.author,
                                                                           payload.cached_message.channel)
            valueStr = payload.cached_message.content
            nameStr = "Cached message:"#str(payload)	
            try:
                await embedMessage(log_channel, titleStr, nameStr, valueStr)
            except:
                await log_channel.send("__**{} has deleted a message in the {} channel**__".format(payload.cached_message.author,
                                                                                                   payload.cached_message.channel))
                await log_channel.send("**{}**".format(payload.cached_message.content))
        else:
            await log_channel.send("**An uncached message was deleted in the channel <#{}>**".format(payload.channel_id, payload.channel_id))      

@diffbot.command()
async def set_log_channel(ctx, channel_mention):
    if not await is_author_guild_admin(ctx):
        return
    diffconfigs = await get_diffconfig(ctx.message.guild)
    found_channel = diffbot.get_channel(stripChannelMention(channel_mention))
    if found_channel is not None:
        diffconfigs['log_channel_id'] = found_channel.id
        await update_diffconfig(ctx.message.guild, diffconfigs)
        await ctx.message.channel.send("Deleted message log channel is set to **#{}**".format(found_channel.name))
    else:
        await ctx.message.channel.send("That is an invalid channel.")








diffbot.run(TOKEN, reconnect=True)
