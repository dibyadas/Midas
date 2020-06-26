import os
import time
import evdev
import asyncio

from evdev import ecodes, UInput
from concurrent.futures._base import TimeoutError
from aiostream.stream import ziplatest, merge, timeout

from device_reader import BaseReader, Reader
from utils import sanitize_and_notify, execute_command, reload_config
from streams import x_movement, y_movement, tap_detector


async def detect_key_hold(device_path, hold_time_sec=0.4):
    '''
    Asyncio coroutine task to detect trigger to start gesture detection

    '''
    base_reader = BaseReader(device_path)
    reader = Reader(base_reader)

    gesture_task = None
    area_patch = True

    area_x, area_y = 2850, 50

    state = {}
    async for event in reader:
        # borrowed from evdev's author's comment
        if event.type == ecodes.EV_KEY:
            # When the key is pressed, record its timestamp.
            if event.code == 330 and event.value == 1:
                state[event.code] = event.timestamp(), event
            # When it's released, remove it from the state map.
            if event.value == 0 and event.code in state:
                del state[event.code]
                area_patch = True

        if event.type == ecodes.EV_ABS:
            if event.code == 0:  # For ABS_X
                if not event.value in range(area_x-100, area_x+100):
                    area_patch = False
            if event.code == 1:  # For ABS_Y
                if not event.value in range(area_y-100, area_y+100):
                    area_patch = False
            # Check if any keys have been held
            # longer than hold_time_sec seconds.
        now = time.time()
        for code, ts_event in list(state.items()):
            timestamp, event = ts_event
            if (now - timestamp) >= hold_time_sec and area_patch:
                del state[code]  # only trigger once
                area_patch = True

                if gesture_task is None:
                    os.system(f'notify-send "Tracking gestures..."')
                    gesture_task = asyncio.create_task(
                        from_streams(device_path, base_reader))
                else:
                    os.system(f'notify-send "Gesture tracking stopped"')
                    gesture_task.cancel()
                    await gesture_task
                    gesture_task = None


async def confirmation_tap(base_reader):
    '''
    Asyncio coroutine task to wait for user's confirmation tap
    '''
    reader = Reader(base_reader)

    # Time window of 1 sec for the user to confirm by tapping
    # or cancel & refresh if the user doesn't
    timeout_stream = timeout(reader, 1)

    async with timeout_stream.stream() as timed:
        try:
            async for event in timed:
                # The first event for a tap so the user
                if event.type == ecodes.EV_KEY and event.code == 330:
                    print('confirmed.. executing')
                    ret_val = True, event
                    break
        except TimeoutError:
            print("no confimation received... refreshing..")
            ret_val = False, None
        finally:
            reader.exit()
            return ret_val


async def from_streams(touchpad_path, base_reader=1):
    '''
    Asyncio coroutine task to read from all streams &
    detect and then execute the command based on the confirmation tap
    '''
    try:
        # Wait for half a second before processing the events
        await asyncio.sleep(0.5)
        # Grab the touchpad to draw gesture until this coroutine is cancelled
        base_reader.grab()
        # Init all the readers
        x_movement_reader = Reader(base_reader)
        y_movement_reader = Reader(base_reader)
        tap_detector_reader = Reader(base_reader)

        # Reload gesture command map
        reload_config()

        # Store the received coordinates
        coordinates_set = []
        start_time = end_time = 0

        # Zip the X and Y axis events for clarity.
        # It is processed separtely though when sanitizing the input
        zip_xy = ziplatest(y_movement(x_movement_reader),
                           x_movement(y_movement_reader))
        # Read the tap events as well to indicate
        # the start and end of gesture drawing
        merge_tap_xy = merge(zip_xy,
                             tap_detector(tap_detector_reader))

        async with merge_tap_xy.stream() as merged:
            async for event in merged:
                # The zip_xy events are in the form of tuples
                # while the tap events are evdev event objects
                if not isinstance(event, tuple):
                    if event.value == 1:
                        start_time = event.timestamp()
                    elif event.value == 0:
                        end_time = event.timestamp()
                        # If the draw is too short, ignore and reset
                        # cause it's not meaningful
                        if (end_time - start_time) < 0.3:
                            coordinates_set = []
                            continue

                        detected_gesture = sanitize_and_notify(coordinates_set)
                        print(f'Detected gesture :- {detected_gesture}')

                        coordinates_set = []
                        if detected_gesture is None:
                            continue
                        # If gesture detected then wait for a confirmation tap
                        tapped, event = await confirmation_tap(base_reader)

                        if tapped:
                            os.system(f"notify-send 'Confirmed... Executing - {detected_gesture}'")
                            execute_command(detected_gesture)
                        else:
                            os.system("notify-send 'Clearing gestures...'")
                else:
                    coordinates_set.append(event)

    except asyncio.CancelledError:
        # Exit all readers from the base_reader once they are done
        x_movement_reader.exit()
        y_movement_reader.exit()
        tap_detector_reader.exit()
        # Ungrab and yield touchpad to the user
        base_reader.ungrab()


async def detect_key_tap(device_path, hold_time_sec=0.1):
    # dev = evdev.InputDevice(device_path)
    base_reader = BaseReader(device_path)
    reader = Reader(base_reader)

    keymap = [[1, 2, 3, ecodes.KEY_BACKSPACE], [
        4, 5, 6, 0], [7, 8, 9, ecodes.KEY_ENTER]]
    x_locs = []
    y_locs = []
    state = {}

    async for event in reader:
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

        now = time.time()
        for code, ts_event in list(state.items()):
            timestamp, event = ts_event
            if (now - timestamp) >= hold_time_sec:
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
