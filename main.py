import asyncio
import os
import aiostream
import moosegesture

from generators import detect_key_hold, detect_key_tap, from_streams
from streams import x_movement, y_movement, tap_detector

touchpad_path = '/dev/input/event5'
# width = 2940 = x
# height = 1260 = y


def handle_exception(loop, context):
    # msg = context.get("exception", context["message"])
    # print(msg)
    pass  # This gets called when from_streams() task is cancelled
    # because the Futures are trying to write but the coroutine
    # is no longer running but it doesn't really matter so
    # we just silently ignore it

tasks = asyncio.gather(detect_key_hold(touchpad_path))
                       # detect_key_tap(touchpad_path))

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
try:    
    loop.run_until_complete(tasks)
except KeyboardInterrupt:
    loop.close()
