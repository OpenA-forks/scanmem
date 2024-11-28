#!/usr/bin/env python3
"""
    A time speed hacking tool for linux

    - 2024 OpenA @ https://github.com/OpenA-forks/scanmem
    - This code is distributed under the GNU GPL3.0
"""

import re, sys, time, tty, termios, asyncio

# Commands and escape codes
ESCAPE      = 27  # Escape
CANCEL      = 24  # CTRL+X ~ 0x18
QUIT        = 113 # 'q'
PAUSE       = 112 # 'p'
# Escape sequences for terminal keyboard navigation
ARROW_UP    = '[A'
ARROW_DOWN  = '[B'
ARROW_RIGHT = '[C'
ARROW_LEFT  = '[D'

class SpeedHack:

    # set time every 0.01 second, 10 times faster than normal
    def __init__(self, speed = 1, cycle = 0.01):
        self._clk_id = time.CLOCK_REALTIME
        self._speed  = speed if speed >  0    else 1
        self._cycle  = cycle if cycle >= 0.01 else 0.01
        self._paused = False
        self._debug  = False
        self._quit   = False
        self._timestamp = 0.0

    def isRunning(self): return not self._quit
    def isActive (self): return not self._paused

    def timestamp(self):
        return self._timestamp
    def quit(self):
        self._quit = True
    def deactive(self, y = True):
        self._paused = y

    def timeup(self):
        t = time.clock_gettime(self._clk_id)
        t += self._speed # * cycle
        self._timestamp = t
        if not self._debug:
            time.clock_settime(self._clk_id, t)
        return t

    def onkeypress(self, ro = sys.stdin):
        while True:
            ic = ord(ro.read(1)[0])
            if ic == QUIT or ic == CANCEL:
                print('exiting...', end='\r\n')
                break
            elif ic == ESCAPE:
                ar = ro.read(2)
                if ar == ARROW_UP or ar == ARROW_RIGHT:
                    t = self.timeup()
                    c = self._cycle
                    print(f'timehack {t}\r\n', end='\r\n')
                    time.sleep(c)

    async def timeloop(self, wo: asyncio.StreamWriter):
        z = False
        t = c = 0.0
        w = None
        while self.isRunning():
            if self.isActive():
                t = self.timeup()
                c = self._cycle
                w = bytearray(f'timehack {t}\r\n', 'utf-8')
                z = False
            else:
                c = 0.5
                w = b'Paused...\r\n' if not z else None
                z = True
            if w != None:
                "***",wo.write(w)
                await wo.drain()
            await asyncio.sleep(c)
        "***",wo.write(b'exiting...\r\n')
        await wo.drain()

    async def keyhook(self, ro: asyncio.StreamReader):
        while True:
            ic = (await ro.read(1))[0]
            if ic == QUIT or ic == CANCEL:
                self.quit()
                break
            elif ic == PAUSE:
                if self.isActive():
                    self.deactive(True)
                else:
                    self.deactive(False)

    async def make_io_tasks(self, _in = sys.stdin, _out = sys.stdout):
        loop   = asyncio.get_event_loop()
        reader = asyncio.StreamReader(limit=255, loop=loop)
        proto  = asyncio.StreamReaderProtocol(stream_reader=reader, loop=loop)
        dummy  = asyncio.Protocol()
        "*****", await loop.connect_read_pipe (lambda: proto, _in )
        port,_ = await loop.connect_write_pipe(lambda: dummy, _out)
        writer = asyncio.StreamWriter(port, proto, reader, loop)
        task1  = loop.create_task(self.keyhook (reader))
        task2  = loop.create_task(self.timeloop(writer))
        await task1 # key handler
        await task2 # timehack

if __name__ == '__main__':
    # init params
    l = g = False
    s = 1
    c = 0.01
    # parsing arguments
    for arg in sys.argv[1:]:
        if   arg[:2] == '-s': s = int  (re.match(r'^=?(\d+)'       , arg[2:]).group(1))
        elif arg[:2] == '-c': c = float(re.match(r'^=?(\d+\.?\d+?)', arg[2:]).group(1))
        elif arg[:2] == '-l': l = True # async stdin/out mode
        elif arg[:2] == '-G': g = True # debug hidden mode
        elif arg[:2] == '-h':
            print(" ")
            print(" -s[=Int]    # Time Incriment (def: +1s)")
            print(" -c[=Float]  # Cycle Interval (min: 0.01 = 10ms)")
            print(" -l          # Time loop mode (def: manual t incriment w arrow keys)")
            print(" -h          # Show Help", end="\n \r\n")
            exit()

    "**", print( "~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~" )
    if l: print( "; toggle pause @ p" )
    else: print( "; time up      @ ↑ →" )
    "**", print( "; quit program @ q, ctrl+x", end="\n;\n")
    "**", print(f"; speed={s}; cycle={c}", end="\n~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~\n")

    fi_attr = sys.stdin.fileno()
    tc_orig = termios.tcgetattr(fi_attr)
    sp_hack = SpeedHack(s,c)

    try:
        # Enter raw mode (key events sent directly as characters)
        tty.setraw(fi_attr)

        if g: sp_hack._debug = True
        if l: asyncio.run( sp_hack.make_io_tasks() )
        else: sp_hack.onkeypress()

    # Always clean up
    finally:
        termios.tcsetattr(fi_attr, termios.TCSADRAIN, tc_orig)
