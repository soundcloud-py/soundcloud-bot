# Made using https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py as an example

import asyncio

import discord
import youtube_dl

from discord.ext import commands
import config
import os

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
    
    @classmethod
    async def sc(cls, url, ctx, channel=0, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename))
        chan = bot.get_channel(channel)
        sec = 0
        minu = 0
        hur = 0
        for f in range(int(data['duration'])):
            sec += 1
            if sec == 60:
                minu += 1
                sec = 0
                if minu == 60:
                    hur +=1
                    minu = 0
        await chan.send('Now playing: {} by {}\n**----------**\n**Views:** `{}` | **Likes:** `{}` | **Reposts:** `{}`\n**Duration:** `{}hr:{}min:{}sec`'.format(data['title'], data['uploader'], data['view_count'], data['like_count'], data['repost_count'], hur, minu, sec))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()


    @commands.command()
    async def play(self, ctx, *, url):
        """Play a song from Soundcloud"""
        channel = ctx.message.channel.id

        async with ctx.typing():
            await YTDLSource.sc(url, ctx, channel, loop=self.bot.loop)
            
    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from soundcloud (Not as Stable)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def pause(self, ctx):
        """Pause Current Song"""
        ctx.voice_client.pause()
    
    @commands.command()
    async def resume(self, ctx):
        """Resume Current Song"""
        ctx.voice_client.resume()
        
    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

bot = commands.Bot(command_prefix=commands.when_mentioned_or("sc!"),
                   description='Soundcloud Bot made by Artucuno#1898')

bot.remove_command("help")

@bot.command()
async def help(ctx):
    """"""
    await ctx.send("__**Soundcloud**__\n"
                   "\n"
                   "play   | Play a song from Soundcloud\n"
                   "stream | Stream a song from Soundcloud\n"
                   "volume | Set sound volume\n"
                   "pause  | Pause the song\n"
                   "resume | Resume the song\n"
                   "stop   | Stop playing song and leave voice channel\n"
                   "\n"
                   "<https://github.com/soundcloud-py/soundcloud-bot>")
    if ctx.message.author.id == config.ownerid:
        await ctx.send("__**Owner Commands**__\n"
                       "update | Update bot")

@bot.command()
async def update(ctx):
    """"""
    if ctx.message.author.id == config.ownerid:
        await ctx.send("Updating... Check console for more information!")
        code = os.system('git pull origin master')
        if code == 0:
            await ctx.send("Update completed! `Already up to date!`")
        if code == 32768:
            await ctx.send("Error. `.git` file does not exist!")
        else:
            await ctx.send("?: Code: {}".format(code))
    else:
        await ctx.send("You are not the bot owner! Check the config file to change this!")

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(Music(bot))
bot.run('token)
