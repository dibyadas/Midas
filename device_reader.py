import evdev 
import queue
import asyncio
import aiostream

from evdev import ecodes, UInput

class BaseReader:
    '''
    The idea is to have one object reading from the
    device file and filling events into all the waiting iterator's queue.
    '''
    def __init__(self, device_path):
        self.dev = evdev.InputDevice(device_path)
        self.waiters = []

        def handle_exception(loop, context):
            msg = context.get("exception", context["message"])
            print(msg)

        asyncio.get_event_loop().set_exception_handler(handle_exception)

    def flush(self):
    	self.waiters = []

    def read(self, re):
        def callback():
            loop.add_reader(self.dev.fileno(), callback)
            try:
                # import time
                # print(time.time(),'s')
                res = self.dev.read_one()
                re.event_queue.put(res)
                # saved_vals = re.event_queue.get(block=False)
                saved_vals = res
                try:
                    re.pending_future.set_result(saved_vals)
                except AttributeError: # for timeout 
                    pass
                except Exception as ex:
                    re.pending_future.set_exception(ex)

                for waiter in self.waiters:
                    if waiter.pending_future:
                        if waiter is not re:
                            try:
                                waiter.event_queue.put_nowait(res)
                                sav = waiter.event_queue.get(block=False)
                                waiter.pending_future.set_result(sav)
                            except Exception as ex:
                                waiter.pending_future.set_exception(ex)
                    else:
                        waiter.event_queue.put_nowait(saved_vals)
            except Exception as e:
                print(e)
                # raise e from None

        try:
            saved_val = re.event_queue.get(block=False)
            try:
                re.pending_future.set_result(saved_val)
            except Exception as ex1:
                re.pending_future.future.set_exception(ex1)
        except queue.Empty:
            loop = asyncio.get_event_loop()
            loop.add_reader(self.dev.fileno(), callback)

    def grab(self):
        self.dev.grab()

    def ungrab(self):
        self.dev.ungrab()

class Reader:
    def __init__(self, base_reader):
        self.base_reader = base_reader
        self.event_queue = queue.Queue()
        self.pending_future = None
        self.base_reader.waiters.append(self)

    def exit(self):
    	self.base_reader.waiters.remove(self)

    def __aiter__(self):
        return self

    def anext(self):
        return self.__anext__()

    async def __anext__(self):
        self.pending_future = asyncio.Future()
        self.base_reader.read(self)
        result = await self.pending_future
        self.pending_future = None
        return result