import evdev
from evdev import ecodes, UInput

async def x_movement(device_path):  # filter all the mouse movements in X axis
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS and event.code == 0:
            yield event


async def y_movement(device_path):  # filter all the mouse movements in X axis
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS and event.code == 1:
            yield event


async def tap_detector(device_path):  # filter the tap events
    dev = evdev.InputDevice(device_path)
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY and event.code == 330:
            yield event
