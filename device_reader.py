import evdev
import queue
import asyncio
import aiostream

from evdev import ecodes, UInput

# To ensure that while grabbing the mouse device we don't block streams
# that read events from the same device, we create a BaseReader instance
# that serves as the main reader and all other reader's event_queue is filled
# by this main reader. All Reader instance register themselves at the
# base_reader during init. And the user has to set their exit manually to
# prevent invalid state errors. When a registered reader tries to read from
# device, the base_reader checks if there's any value in the queue already set
# from other readers. If set, that value is set as the awaiting future result
# or else a callback is set to be called whenever the device file is ready
# to read. Now whenever that callback is called, the value is read
# and set to the calling reader's pending future and that same value is
# is pushed into the queue of other registered readers to be read during
# their next iteration.


class BaseReader:
    '''
    Class that reads from the actual device file and other reader's 
    register here to read events through this
    '''

    def __init__(self, device_path):
        self.dev = evdev.InputDevice(device_path)
        self.waiters = []

        def handle_exception(loop, context):
            msg = context.get("exception", context["message"])
            print(msg)

        asyncio.get_event_loop().set_exception_handler(handle_exception)

    def read(self, re):
        def callback():
            loop.remove_reader(self.dev.fileno())
            try:
                res = self.dev.read_one()
                for waiter in self.waiters:
                    # Go through all registered reader and check if they
                    # have a pending future to set the result
                    if waiter.pending_future:
                        try:
                            waiter.event_queue.put_nowait(res)
                            sav = waiter.event_queue.get(block=False)
                            waiter.pending_future.set_result(sav)
                        except AttributeError:
                            # When task is cancelled then pending_future
                            # is None so ignore this
                            pass
                        except Exception as ex:
                            try:
                                waiter.pending_future.set_exception(ex)
                            except asyncio.InvalidStateError:
                                # awaiting task has cancelled the future
                                # not ideal way to handle but WIP
                                pass
                    else:
                        # If no pending future then push it in the queue
                        # to read in next iteration
                        waiter.event_queue.put_nowait(res)
            except Exception as e:
                raise e from None

        try:
            saved_val = re.event_queue.get(block=False)
            try:
                re.pending_future.set_result(saved_val)
            except Exception as ex:
                re.pending_future.future.set_exception(ex)
        except queue.Empty:
            loop = asyncio.get_event_loop()
            loop.add_reader(self.dev.fileno(), callback)

    def grab(self):
        # Grabbing base_reader still makes it possible for all the
        # registered readers to simultaneously read without blocking
        self.dev.grab()

    def ungrab(self):
        self.dev.ungrab()


class Reader:
    def __init__(self, base_reader):
        self.base_reader = base_reader
        self.event_queue = queue.Queue()
        self.pending_future = None
        # Register at the base reader
        self.base_reader.waiters.append(self)

    def exit(self):
        # Needed to safely stop receiving events from BaseReader
        self.base_reader.waiters.remove(self)

    def __aiter__(self):
        return self

    def anext(self):
        return self.__anext__()

    async def __anext__(self):
        self.pending_future = asyncio.Future()
        # This either reads from device or from the queue and sets the future
        self.base_reader.read(self)
        result = await self.pending_future
        # Set it None to make sure it's not set again by other coroutines
        self.pending_future = None
        return result
