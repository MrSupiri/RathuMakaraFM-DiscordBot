import threading
from flask import Flask, request, jsonify
import json
from MusicBot import MusicBot
from utils import *
import asyncio

bot = MusicBot()
app = Flask(__name__)


@app.route('/API/bot/get/player/')
def player_info():
    bot.logger.info(f"API Request for {request.path} from {request.remote_addr}")
    if bot and bot.MusicPlayer:
        if bot.MusicPlayer.current:
            d = {"Now Playing": {"song": bot.MusicPlayer.current.song_name,
                                 "uploader": bot.MusicPlayer.current.song_name,
                                 "thumbnail": bot.MusicPlayer.current.song_thumbnail,
                                 "url": bot.MusicPlayer.current.song_webpage_url,
                                 "duration": bot.MusicPlayer.current.song_duration,
                                 "progress": bot.MusicPlayer.progress(),
                                 "extractor": bot.MusicPlayer.current.song_extractor,
                                 "requester": bot.MusicPlayer.current.requester.name,
                                 "pause": bot.MusicPlayer.is_pause
                                 },
                 'Queue': []}
        else:
            d = {"Now Playing": {"song": None, "uploader": None, "thumbnail": None, "url": None, "duration": None,
                                 "progress": None, "extractor": None, "requester": None},
                 'Queue': []}
        for song in bot.MusicPlayer.queue:
            d['Queue'].append({"song": song.song_name,
                               "uploader": song.song_name,
                               "thumbnail": song.song_thumbnail,
                               "url": song.song_webpage_url,
                               "duration": song.song_duration,
                               "extractor": song.song_extractor,
                               "requester": song.requester.name})

    else:
        d = {"Now Playing": {"song": None, "uploader": None, "thumbnail": None, "url": None, "duration": None,
                             "progress": None, "extractor": None, "requester": None},
             'Queue': []}

    return jsonify(d)


@app.route('/API/bot/get/user/', methods=["POST"])
def user_info():
    try:
        bot.logger.info(f"API Request for {request.path} from {request.remote_addr}")

        if not request.content_type == 'application/json':
            bot.logger.info(f"Bad Request from {request.remote_addr}: Content-type {request.content_type} is invalid")

            return json.dumps({'error': 'Content-type must be application/json'}), 400, {
                'ContentType': 'application/json'}

        data = request.get_json(force=True)
        bot.logger.info(f"API Request: {request.path} => {data}")

        if 'authkey' not in data or 'user_id' not in data:
            bot.logger.info(f"Bad Request from {request.remote_addr}: Missing some key attributes")
            return json.dumps({'error': 'Missing key attributes'}), 400, {'ContentType': 'application/json'}

        if web_api_auth_key != data['authkey']:
            return json.dumps({'error': 'Invalid Auth Key'}), 401, {'ContentType': 'application/json'}

        user = bot.get_user(int(data['user_id']))
        if not user:
            return json.dumps({'error': 'User was not found'}), 404, {'ContentType': 'application/json'}

        guild = bot.get_guild(GUILD_ID)
        if not guild:
            return json.dumps({'error': 'Server was not found'}), 404, {'ContentType': 'application/json'}
        member = guild.get_member(user.id)
        if not member:
            return json.dumps({'error': 'User was not found on the server'}), 404, {'ContentType': 'application/json'}

        d = {
            'name': user.name,
            'roles': [y.id for y in member.roles],
            'is_bot': user.bot,
            'dm_channel': user.dm_channel,
            'created_at': user.created_at,
            'default_avatar_url': user.default_avatar_url,
            'is_blocked': user.is_blocked()
        }
        return jsonify(d)

    except Exception as e:
        bot.logger.error("Error While Processing a API Request")
        bot.logger.exception(e)
        return json.dumps({'error': 'Internal Server Error'}), 400, {'ContentType': 'application/json'}


@app.route('/API/bot/request/', methods=["POST"])
def bot_command():
    try:
        if not request.content_type == 'application/json':
            bot.logger.info(f"Bad Request from {request.remote_addr}: Content-type {request.content_type} is invalid")

            return json.dumps({'failed': 'Content-type must be application/json'}), 400, {
                'ContentType': 'application/json'}

        data = request.get_json(force=True)

        bot.logger.info(f"API Request: {request.path} => {data}")

        if 'authkey' not in data or 'cmd' not in data or 'user_id' not in data or 'args' not in data:
            bot.logger.info(f"Bad Request from {request.remote_addr}: Missing some key attributes")
            return json.dumps({'error': 'Missing key attributes'}), 400, {'ContentType': 'application/json'}

        if web_api_auth_key != data['authkey']:
            return json.dumps({'error': 'Invalid Auth Key'}), 401, {'ContentType': 'application/json'}

        user = bot.get_user(int(data['user_id']))
        if not user:
            return json.dumps({'error': 'User was not found'}), 404, {'ContentType': 'application/json'}

        guild = bot.get_guild(GUILD_ID)
        if not guild:
            return json.dumps({'error': 'Server was not found'}), 404, {'ContentType': 'application/json'}
        member = guild.get_member(user.id)
        if not member:
            return json.dumps({'error': 'User was not found on the server'}), 404, {'ContentType': 'application/json'}

        if data['cmd'] != "request" and not [y.id for y in member.roles if
                                             y.id in bot_commanders]:
            return json.dumps({'error': 'User Don\'t have permission for this action'}), 401, {'ContentType': 'application/json'}

        result = asyncio.run_coroutine_threadsafe(
            parse_cmd(data['cmd'], data['args'], user), bot.loop)

        if result.result():
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    except Exception as e:
        bot.logger.error("Error While Processing a API Request")
        bot.logger.exception(e)
        return json.dumps({'error': 'Internal Server Error'}), 400, {'ContentType': 'application/json'}


async def parse_cmd(cmd, args, author):
    if cmd == 'play':
        result = await bot.cmd_play(args, download=True, author=author)

    elif cmd == 'playnow':
        result = await bot.cmd_play(args, download=False, play_now=True, author=author)

    elif cmd == 'playnext':
        result = await bot.cmd_play(args, download=False, play_next=True, author=author)

    elif cmd == 'playlist':
        result = await bot.cmd_play(args, playlist=True, author=author)

    elif cmd == 'volume':
        result = await bot.cmd_volume(args, author=author)

    elif cmd == 'skip':
        result = await bot.cmd_skip(author=author)

    elif cmd == 'pause':
        result = await bot.cmd_pause(author=author)

    elif cmd == 'resume':
        result = await bot.cmd_resume(author=author)

    elif cmd == 'clearQueue':
        result = await bot.cmd_clear_queue(author=author)

    elif cmd == 'stream':
        result = await bot.cmd_play(args, None, author=author)

    elif cmd == 'remove' or cmd == 'rm':
        result = await bot.cmd_remove_from_queue(args, author=author)

    elif cmd == 'move' or cmd == 'm':
        result = await bot.cmd_move_song(args, author=author)

    elif cmd == 'request' or cmd == 'req':
        result = await bot.cmd_request(args, None, author=author)
    else:
        return False
    return result


if __name__ == "__main__":
    def start_server():
        app.run(host=web_api_ip)


    thread = threading.Thread(target=start_server)
    thread.start()
    bot.run(bot_auth_key)
