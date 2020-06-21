import os
import time
import evdev
import asyncio
import aiostream
from evdev import ecodes, UInput
from concurrent.futures._base import TimeoutError

from streams import x_movement, y_movement, tap_detector
from utils import sanitize_and_notify, execute_command

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

async def confirmation_tap(dev):
    timeout_stream = aiostream.stream.timeout(dev.async_read_loop(), 1)
    async with timeout_stream.stream() as timed:
        try:
            async for event in timed:
                if event.type == ecodes.EV_KEY and event.code == 330:
                    print('confirmed.. executing')
                    return True, event 
        except TimeoutError:
            print("no confimation received... refreshing..")
            return False, None


async def from_streams(touchpad_path):  # Merge multiple async streams
    await asyncio.sleep(0.5)
    dev = evdev.InputDevice(touchpad_path)
    dev.grab()
    try:
        coord_set = []
        flag = False
        start_time = 0
        end_time = 0
        # async with async_merge_tap_detect.stream() as merged:
        timestamp_vals = {}
        async for event in dev.async_read_loop():
            if event.type == ecodes.EV_ABS and event.code == 0:
                try:
                    timestamp_vals[f'{event.timestamp()}']
                    timestamp_vals[f'{event.timestamp()}'][0] = event.value
                except KeyError:
                    timestamp_vals[f'{event.timestamp()}'] = [event.value, 0]
            elif event.type == ecodes.EV_ABS and event.code == 1:
                try:
                    timestamp_vals[f'{event.timestamp()}']
                    timestamp_vals[f'{event.timestamp()}'][1] = event.value
                except KeyError:
                    timestamp_vals[f'{event.timestamp()}'] = [0, event.value]
            elif event.type == ecodes.EV_KEY and event.code == 330:
                # print(event)
                if event.value == 1:
                    start_time = event.timestamp()
                elif event.value == 0:
                    end_time = event.timestamp()
                    # print(end_time, start_time, end_time - start_time)
                    if (end_time - start_time) < 0.3:
                        timestamp_vals = {}
                        continue
                    detected_gesture = sanitize_and_notify(timestamp_vals)
                    # flagger_time = end_time
                    tapped, event = await confirmation_tap(dev)
                    if tapped:
                        print('exec gesture')
                        start_time = event.timestamp()
                        execute_command(detected_gesture)
                        dev.ungrab()
                        return
                    else:
                        print('clear gesture')
                        os.system("notify-send 'Clearing gestures...'")
                    end_time = 0
                    timestamp_vals = {}
    except Exception as e:
        print(e)


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
