import aiostream
import asyncio
import evdev
import curses
from curses.textpad import rectangle
from device_reader import Reader

rat_y = 20/1260  # height of terminal area 20 lines
rat_x = 80/2940  # width of terminal area 80 lines

ex = (630, 1500)


def convert(ex):
    return (int(ex[0]*rat_y), int(ex[1]*rat_x))


touchpad_path = '/dev/input/event5'


async def x_movement(reader):
    # dev = evdev.InputDevice(touchpad_path)
    async for event in reader:
        if event.type == evdev.ecodes.EV_ABS and event.code == 0:
            yield event.value


async def y_movement(reader):
    # dev = evdev.InputDevice(touchpad_path)
    async for event in reader:
        if event.type == evdev.ecodes.EV_ABS and event.code == 1:
            yield event.value


async def from_streams(base_reader):  # Merge multiple async streams
    r1 = Reader(base_reader)
    r2 = Reader(base_reader)
    async_zip_iterator = aiostream.stream.ziplatest(y_movement(r1), x_movement(r2))
    async with async_zip_iterator.stream() as merged:
        count = 0
        async for event in merged:
            if count == 5:	  # yield every 5 iterates for better performance
                yield event
                count = 0
            else:
                count += 1
            # print(convert(event))


async def pad(base_reader):
    curses.initscr()
    stdscr = curses.newwin(200, 200)
    stdscr.clear()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    curses.start_color()
    rectangle(stdscr, 0, 0, 20, 80)
    stdscr.refresh()
    async for coord in from_streams(base_reader):
        pp = convert(coord)
        if not (pp[0] <= 0 or pp[1] <= 0):
            stdscr.clear()
            rectangle(stdscr, 0, 0, 20, 80)
            rectangle(stdscr, pp[0]-1, pp[1]-1, pp[0]+1, pp[1]+1)
            stdscr.refresh()
        await asyncio.sleep(0.005)


# loop = asyncio.get_event_loop()
# try:
#     stdscr.clear()
#     curses.noecho()
#     curses.cbreak()
#     stdscr.keypad(1)
#     curses.start_color()
#     # loop.run_until_complete(pad())
#     # loop.close()
# except KeyboardInterrupt:
#     pass
# finally:
#     stdscr.keypad(0)
#     curses.echo()
#     curses.nocbreak()
#     curses.endwin()
