import evdev
from evdev import ecodes, UInput
import time
import asyncio
import os
import aiostream
import moosegesture

notified = False
touchpad_path = '/dev/input/event6'

# width = 2940 = x
# height = 1260 = y

async def detect_key_hold(device_path, hold_time_sec=0.5):
    # Assume trig_x and trig_y are True
    # and become false when it's tapped anywhere else
    dev = evdev.InputDevice(device_path)
    gesture_task = None
    trig_x = True
    trig_y = True
    area_x = 2850
    area_y = 50
    state = {}
    while True:
        try:
            for event in dev.read():
                if event.type == ecodes.EV_KEY:
                    # When the key is pressed, record its timestamp.
                    if event.code == 330 and event.value == 1:
                        state[event.code] = event.timestamp(), event
                    # When it's released, remove it from the state map.
                    if event.value == 0 and event.code in state:
                        del state[event.code]
                        trig_x = trig_y = True
                if event.type == ecodes.EV_ABS:
                    if event.code == 0:  # For ABS_X
                        if not event.value in range(area_x-100, area_x+100):
                            trig_x = False
                    if event.code == 1:  # For ABS_Y
                        if not event.value in range(area_y-100, area_y+100):
                            trig_y = False
        except BlockingIOError:
            # If nothing to read then suspend the coroutine
            # for some time to allow the other coroutines to run
            await asyncio.sleep(0.05)
            # Check if any keys have been held
            # for longer than hold_time_sec seconds.
        now = time.time()
        for code, ts_event in list(state.items()):
            ts, event = ts_event
            if (now - ts) >= hold_time_sec and trig_x and trig_y:
                del state[code]  # only trigger once
                trig_y = trig_x = True
                # yield event
                print(f"Triggered! Event :- {event}")
                if gesture_task is None:
                    gesture_task = asyncio.create_task(from_streams())
                else:
                    gesture_task.cancel()
                    gesture_task = None


def handle_exception(loop, context):
    pass  # This gets called when from_streams() task is cancelled
          # because the Futures are trying to write but the coroutine
          # is no longer running but it doesn't really matter so
          # we just silently ignore it


async def detect_key_tap(device_path, hold_time_sec=0.1):
    dev = evdev.InputDevice(device_path)
    keymap = [[1, 2, 3, ecodes.KEY_BACKSPACE], [
        4, 5, 6, 0], [7, 8, 9, ecodes.KEY_ENTER]]
    x_locs = []
    y_locs = []
    state = {}
    while True:
        try:
            for event in dev.read():
                if event.type == ecodes.EV_KEY:
                    if event.code == 330 and event.value == 1:
                        x_locs = []
                        y_locs = []
                        state[event.code] = event.timestamp(), event
                    if event.value == 0 and event.code in state:
                        del state[event.code]
                        x_locs = []
                        y_locs = []
                if event.type == ecodes.EV_ABS:
                    if event.code == 0:
                        x_locs.append(event.value)
                    if event.code == 1:
                        y_locs.append(event.value)
        except BlockingIOError:
            # If nothing to read then suspend the coroutine
            # for some time to allow the other coroutine to run
            await asyncio.sleep(0.05)
        now = time.time()
        for code, ts_event in list(state.items()):
            ts, event = ts_event
            if (now - ts) >= hold_time_sec:
                del state[code]  # only trigger once
                try:
                    avg_x = sum(x_locs)/len(x_locs)
                    avg_y = sum(y_locs)/len(y_locs)
                except ZeroDivisionError:
                    # Sometimes happens when no events
                    # are collected in one of the lists
                    continue
                # print(int(avg_y), int(avg_x), int(avg_y/420), int(avg_x/916))
                # yield keymap[int(avg_y/420)][int(avg_x/916)]
                print(keymap[int(avg_y/420)][int(avg_x/916)])
        continue


# async def x_movement(device_path):
#     dev = evdev.InputDevice(device_path)
#     while True:
#         try:
#             for event in dev.read():
#                 if event.type == ecodes.EV_ABS and event.code == 0:
#                     # print(event)
#                     yield event
#         except BlockingIOError:
#             await asyncio.sleep(0.005)


# async def y_movement(device_path):
#     dev = evdev.InputDevice(device_path)
#     while True:
#         try:
#             for event in dev.read():
#                 if event.type == ecodes.EV_ABS and event.code == 1:
#                     # print(event)
#                     yield event
#         except BlockingIOError:
#             await asyncio.sleep(0.005)


async def x_movement(device_path):
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS and event.code == 0:
            yield event


async def y_movement(device_path):
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS and event.code == 1:
            yield event


async def tap_detector(device_path):
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY and event.code == 330:
            yield event


def sanitize(coord_set):
    # print(coord_set)
    timestamp_vals = {}
    for _, x_event in coord_set:
        # print(x_event.timestamp())
        if x_event is not None:
            timestamp_vals[f'{x_event.timestamp()}'] = [x_event.value]
            # raise e from None
    for y_event, _ in coord_set:
        try:
            if y_event is not None:
                try:
                    timestamp_vals[f'{y_event.timestamp()}'][1] = y_event.value
                except IndexError as e:
                    # raise e from None
                    timestamp_vals[f'{y_event.timestamp()}'].append(y_event.value)
        except KeyError:
            pass

    sanitized_tuple_list = []
    # print(timestamp_vals) 
    for item in timestamp_vals.values():
        if len(item) == 2:
            # continue
            sanitized_tuple_list.append(tuple(item))
    # print(sanitized_tuple_list)
    detected_gesture = moosegesture.getGesture(sanitized_tuple_list)
    print(f'Gesture is :- {detected_gesture}')
    gesture_map = {('DR', 'UR', 'DR', 'UR'): 'W', 
                   ('UR', 'DR', 'UR', 'DR'): 'M',
                   ('D',): 'I',
                   ('DR','UR'): 'V',
                   ('UR','DR'): 'Inverted V',
                   ('L', 'DL', 'D', 'DR', 'R'): 'C',
                   ('D', 'R'): 'L',
                   ('UR', 'D', 'UR'): 'Thunder',
                   ('D', 'L'): 'Mirror L'}
    closest_match = moosegesture.findClosestMatchingGesture(
        detected_gesture, gesture_map.keys(), maxDifference=4)
    # print(gesture_map[closest_match[0]])
    if closest_match is not None:
        os.system(f'notify-send "Gesture Detected :- {gesture_map[closest_match[0]]}"')
    else:
        print("No gesture detected")
    # (lambda x: (x[0].value, x[1].value))


async def from_streams():  # Merge multiple async streams
    try:
        async_zip_x_y = aiostream.stream.ziplatest(y_movement(touchpad_path),
                                                   x_movement(touchpad_path))
        async_merge_tap_detect = aiostream.stream.merge(
            async_zip_x_y, tap_detector(touchpad_path))
        coord_set = []
        flag = True
        async with async_merge_tap_detect.stream() as merged:
            async for event in merged:
                # print(event)
                if not isinstance(event, tuple):
                    if event.value == 0:
                        sanitize(coord_set)
                        coord_set = []
                    # if event.type == ecodes.EV_KEY and event.code == 330:
                        # print(event)
                else:
                    # coord_set.append(event)
                    if event is None:
                        print(time.time())
                    else:
                        coord_set.append(event)
                    # print(event)
    except Exception as e:
        print(e)

# for event in merged:
#     if event.type == EV_KEY and event.code == 330:
#         if event.value == 1:


# async def main():
        # async for event in x_movement():
        #     print(event)
        # t1 = asyncio.create_task(x_movement())
    # t2 = asyncio.create_task(y_movement())
    # t1 = asyncio.create_task(detect_key_hold(touchpad_path))
    # t2 = asyncio.create_task(detect_key_tap(touchpad_path))
    # t3 = asyncio.create_task(from_streams())
    # await asyncio.wait([t3, t2, t1])

    # await t1
    # await t2
    # await t3
tasks = asyncio.gather(detect_key_hold(touchpad_path),
                       detect_key_tap(touchpad_path))

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
try:
    loop.run_until_complete(tasks)
except KeyboardInterrupt:    
    loop.close()

# ui = UInput()
# for event in detect_number_press():
#     # os.system('notify-send "Triggered!"')
#     # print(f'{event.code} was pressed')
#     if event == 0:
#         code = 11
#     elif event in range(1,10):
#         code = event + 1
#     else:
#         code = event
#     ui.write(ecodes.EV_KEY, code, 1)
#     ui.write(ecodes.EV_KEY, code, 0)
#     ui.syn()


# for event in device1.read_loop():
#     print(event)


# asyncio.run(from_streams())
# ams())
