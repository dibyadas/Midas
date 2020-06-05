import evdev
from evdev import ecodes, UInput
import time
import asyncio
import os

notified = False
touchpad_path = '/dev/input/event6'

#width = 2940 = x
#height = 1260 = y

async def x_movement(device_path):
    dev = evdev.InputDevice(device_path)
    while True:
        try:
            for event in dev.read():
                if event.type == ecodes.EV_ABS and event.code == 0:
                    print(event)
        except BlockingIOError:
            await asyncio.sleep(0.005)


async def detect_key_hold(device_path, hold_time_sec=1):
    # Assume trig_x and trig_y are True
    # and become false when it's tapped anywhere else
    dev = evdev.InputDevice(device_path)
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
        continue


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


async def y_movement(device_path):
    dev = evdev.InputDevice(device_path)
    while True:
        try:
            for event in device2.read():
                if event.type == ecodes.EV_ABS and event.code == 1:
                    print(event)
        except BlockingIOError:
            await asyncio.sleep(0.005)


async def main():
        # async for event in x_movement():
        #     print(event)
        # t1 = asyncio.create_task(x_movement())
    t1 = asyncio.create_task(detect_key_hold('/dev/input/event6'))
    # t2 = asyncio.create_task(y_movement())
    t2 = asyncio.create_task(detect_key_tap('/dev/input/event6'))
    await asyncio.wait([t1, t2])
    # await t1
    # await t2

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
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

# async def x_movement():
#   async for event in device1.async_read_loop():
#       if event.type == ecodes.EV_ABS and event.code == 0:
#           yield event

# async def y_movement():
#   async for event in device2.async_read_loop():
#       if event.type == ecodes.EV_ABS and event.code == 1:
#           yield event

# async def from_streams(): # Merge multiple async streams
#   async with aiostream.stream.merge(x_movement(), y_movement()).stream() as merged:
#       async for event in merged:
#           print(event)

# asyncio.run(from_streams())
