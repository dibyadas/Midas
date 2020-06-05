import aiostream
import asyncio
import evdev
import curses
from curses.textpad import rectangle

curses.initscr()
stdscr = curses.newwin(200, 200)


rat_y = 20/1260  # height of terminal area 20 lines
rat_x = 80/2940  # width of terminal area 80 lines

ex = (630, 1500)


def convert(ex):
    return (int(ex[0]*rat_y), int(ex[1]*rat_x))


touchpad_path = '/dev/input/event6'


async def x_movement():
    dev = evdev.InputDevice(touchpad_path)
    async for event in dev.async_read_loop():
        if event.type == evdev.ecodes.EV_ABS and event.code == 0:
            yield event.value


async def y_movement():
    dev = evdev.InputDevice(touchpad_path)
    async for event in dev.async_read_loop():
        if event.type == evdev.ecodes.EV_ABS and event.code == 1:
            yield event.value


async def from_streams():  # Merge multiple async streams
    async_zip_iterator = aiostream.stream.zip(y_movement(), x_movement())
    async with async_zip_iterator.stream() as merged:
        count = 0
        async for event in merged:
            if count == 5:  # yield every 5 iterates for better performance
                yield event
                count = 0
            else:
                count += 1
            # print(convert(event))


async def pad():
    rectangle(stdscr, 0, 0, 20, 80)
    stdscr.refresh()
    async for coord in from_streams():
        pp = convert(coord)
        if pp[0] <= 0 or pp[1] <= 0:
            await asyncio.sleep(0.0005)
            continue
        stdscr.clear()
        rectangle(stdscr, 0, 0, 20, 80)
        rectangle(stdscr, pp[0]-1, pp[1]-1, pp[0]+1, pp[1]+1)
        stdscr.refresh()
        await asyncio.sleep(0.0005)


loop = asyncio.get_event_loop()
try:
    stdscr.clear()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    curses.start_color()
    loop.run_until_complete(pad())
    loop.close()
except KeyboardInterrupt:
    pass
finally:
    stdscr.keypad(0)
    curses.echo()
    curses.nocbreak()
    curses.endwin()
