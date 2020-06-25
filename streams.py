from evdev import ecodes
from device_reader import Reader
import evdev


async def x_movement(reader):  # filter events in X axis
    async for event in reader:
        if event.type == ecodes.EV_ABS and event.code == 0:
            yield event


async def y_movement(reader):  # filter events in Y axis
    async for event in reader:
        if event.type == ecodes.EV_ABS and event.code == 1:
            yield event


async def tap_detector(reader):  # filter tap events
    async for event in reader:
        if event.type == ecodes.EV_KEY and event.code == 330:
            yield event

# async def x_movement(device_path):  # filter events in X axis
#     dev = evdev.InputDevice(device_path)
#     async for event in dev.async_read_loop():
#         if event.type == ecodes.EV_ABS and event.code == 0:
#             yield event


# async def y_movement(device_path):  # filter events in Y axis
#     dev = evdev.InputDevice(device_path)
#     async for event in dev.async_read_loop():
#         if event.type == ecodes.EV_ABS and event.code == 1:
#             yield event


# async def tap_detector(device_path):  # filter tap events
#     dev = evdev.InputDevice(device_path)
#     async for event in dev.async_read_loop():
#         if event.type == ecodes.EV_KEY and event.code == 330:
#             yield event