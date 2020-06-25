import os
import time
import evdev
import asyncio

from evdev import ecodes, UInput
from concurrent.futures._base import TimeoutError
from aiostream.stream import ziplatest, merge, timeout

from streams import x_movement, y_movement, tap_detector
from utils import sanitize_and_notify, execute_command
from device_reader import BaseReader, Reader

async def detect_key_hold(device_path, hold_time_sec=0.1):
    # Assume trig_x and trig_y are True
    # and become false when it's tapped anywhere else
    dev = evdev.InputDevice(device_path)
    # dev2.register(dev)
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
                # print(f"Triggered! Event :- {event}")
                # if gesture_task is None:
                os.system(f'notify-send "Tracking gestures..."')
                await asyncio.create_task(from_streams(device_path))
                os.system(f'notify-send "Gesture tracking stopped"')
                # else:           
                #     gesture_task.cancel()
                #     gesture_task = None

async def confirmation_tap(base_reader):
    # await asyncio.sleep(0.1)
    reader = Reader(base_reader)
    # while True:
    #     try:
    #         item = await asyncio.wait_for(reader.anext(), 1)
    #         print(item)
    #     except StopAsyncIteration:
    #         return False, None
    #     else:
    #         return True, item
    timeout_stream = timeout(reader, 1)
    # dev = evdev.InputDevice(base_reader)
    # timeout_stream = timeout(dev.async_read_loop(), 1)
    async with timeout_stream.stream() as timed:
        try:
            async for event in timed:
                # print(event)
                if event.type == ecodes.EV_KEY and event.code == 330:
                    print('confirmed.. executing')
                    reader.exit()
                    return True, event 
        except TimeoutError:
            print("no confimation received... refreshing..")
            reader.exit()
            return False, None



async def from_streams(touchpad_path):  # Merge multiple async streams
    await asyncio.sleep(0.5)
    base_reader = BaseReader(touchpad_path)
    base_reader.grab()
    coord_set = []
    start_time = 0
    end_time = 0
    count = 0
    zip_xy = ziplatest(y_movement(base_reader),
                       x_movement(base_reader))
    merge_tap_xy = merge(zip_xy,
                         tap_detector(base_reader))
    # zip_xy = ziplatest(y_movement(touchpad_path),
    #                    x_movement(touchpad_path))
    # merge_tap_xy = merge(zip_xy,
    #                      tap_detector(touchpad_path))

    async with merge_tap_xy.stream() as merged:
        async for event in merged:
            # print(event)
            if not isinstance(event, tuple):
                if event.value == 1:
                    start_time = event.timestamp()
                elif event.value == 0:
                    end_time = event.timestamp()
                    if (end_time - start_time) < 0.3:
                        coord_set = []
                        continue
                    # print(coord_set)
                    detected_gesture = sanitize_and_notify(coord_set)
                    print(f'Detected gesture :- {detected_gesture}')
                        
                    coord_set = []
                    if detected_gesture is None:
                        continue
                    tapped, event = await confirmation_tap(base_reader)
                    if tapped:
                        # print('executing gesture')
                        execute_command(detected_gesture)
                    else:
                        os.system("notify-send 'Clearing gestures...'")
                    # base_reader.flush()
                        # print('cleared gesture')
                # if event.type == ecodes.EV_KEY and event.code == 330:
                    # print(event)
            else:
                coord_set.append(event)
                # if event is None:
                #     print(time.time())
                # else:
                #     if count == 2:
                #         coord_set.append(event)
                #         count = 0
                #     else:
                #         count += 1

    # except Exception as e:
    #     print(e)


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
