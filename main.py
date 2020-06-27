import asyncio
import os
import aiostream
import moosegesture

from utils import reload_config
from generators import detect_key_hold, detect_key_tap

touchpad_path = '/dev/input/event5'
gesture_command_map_file = 'gesture_map.yml'


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    print(msg)
    # print(context)
    pass  # This gets called when from_streams() task is cancelled
    # because the Futures are trying to write but the coroutine
    # is no longer running but it doesn't really matter so
    # we just silently ignore it


reload_config(gesture_command_map_file)
tasks = asyncio.gather(detect_key_hold(touchpad_path))
# detect_key_tap(touchpad_path))

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
try:
    loop.run_until_complete(tasks)
except KeyboardInterrupt:
    loop.close()
