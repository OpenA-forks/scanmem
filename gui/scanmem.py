"""
    scanmem.py: python wrapper for libscanmem
    
    Copyright (C) 2010,2011,2013 Wang Lu <coolwanglu(a)gmail.com>
    Copyright (C) 2018 Sebastian Parschauer <s.parschauer(a)gmx.de>
    Copyright (C) 2020 Andrea Stacchiotti <andreastacchiotti(a)gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import ctypes, os, re, sys, tempfile, socket, time, threading

LIB_PATH = os.environ['SCANMEM_LIBDIR'] # libscanmem.so
SOC_PATH = os.environ['SCANMEM_SOCKET'] # /tmp/scanmem-X.X~dev-socket
IS_DEBUG = os.environ['SCANMEM_DEBUG']

class Scanmem():
    """Wrapper for libscanmem."""
    
    LIBRARY_FUNCS = {
        'sm_init' : (ctypes.c_bool, ),
        'sm_cleanup' : (None, ),
        'sm_set_backend' : (None, ),
        'sm_backend_exec_cmd' : (None, ctypes.c_char_p),
        'sm_get_num_matches' : (ctypes.c_ulong, ),
        'sm_get_version' : (ctypes.c_char_p, ),
        'sm_get_scan_progress' : (ctypes.c_double, ),
        'sm_set_stop_flag' : (None, ctypes.c_bool),
        'sm_process_is_dead' : (ctypes.c_bool, ctypes.c_int32)
    }

    def __init__(self):
        self._itr = self._th = None
        self._lib = self.load_library()
        self._lib.sm_set_backend()
        self._lib.sm_init()
        self.exec_command('reset')

    def get_version(self):
        return '{"version":"%s"}'% self._lib.sm_get_version().decode()

    @staticmethod
    def load_library():
        lib = ctypes.CDLL(LIB_PATH)
        for k,v in Scanmem.LIBRARY_FUNCS.items():
            f = getattr(lib, k)
            f.restype = v[0]
            f.argtypes = v[1:]
        return lib

    def dump_command(self, cmd: str, raw_out=False):
        """
        Execute command using libscanmem.
        This function is NOT thread safe, send only one command at a time.
        
        cmd: command to run
        raw_out: if True, return in a string what libscanmem would print to stdout
        """
        with tempfile.TemporaryFile() as directed_file:
            backup_stdout_fileno = os.dup(sys.stdout.fileno())
            os.dup2(directed_file.fileno(), sys.stdout.fileno())

            self._lib.sm_backend_exec_cmd(ctypes.c_char_p(cmd.encode()))

            os.dup2(backup_stdout_fileno, sys.stdout.fileno())
            os.close(backup_stdout_fileno)
            directed_file.seek(0)
            if not raw_out:
                self._itr = self.gen_match_rows(directed_file.readlines())
            else:
                return '{"raw":[%s]}'% ','.join(map(str,directed_file.read()))

    def exec_command(self, cmd: str):
        self._lib.sm_backend_exec_cmd(ctypes.c_char_p(cmd.encode()))

    def get_match_info(self, cpid: str):
        pid = ctypes.c_int32(int(cpid))
        isd = self._lib.sm_process_is_dead(pid)
        cnt = self._lib.sm_get_num_matches()
        return '{"found":%d,"is_process_dead":%d}'% (cnt, isd)

    def get_scan_progress(self):
        pgs = self._lib.sm_get_scan_progress()
        return '{"scan_progress":%f}'% float(pgs)

    def set_stop_flag(self, stop_flag=True):
        """
        Sets the flag to interrupt the current scan at the next opportunity
        """
        self._lib.sm_set_stop_flag(stop_flag)

    def exit_cleanup(self):
        """
        Frees resources allocated by libscanmem, should be called before disposing of this instance
        """
        self._lib.sm_cleanup()
        self._itr = None

    def process_reset(self, cpid: str):
        self.exec_command('reset')
        if cpid and int(cpid) > 0:
            self.exec_command(f'pid {cpid}')

    @staticmethod
    def gen_match_rows(lines: list[bytes]):
        """
        Returns a generator of (match_id_str, addr_str, off_str, region_type, value, types_str) for each match, all strings.
        The function executes commands internally, it is NOT thread safe
        """
        line_templ = '{"match_id":%s,"addr":"%s","off":"%s","region_type":"%s","value":%s,"types":"%s"}'
        line_regex = re.compile(r'^\[ *(\d+)\] +([\da-f]+), +\d+ \+ +([\da-f]+), +(\w+), (.*), +\[([\w ]+)\]$')

        for line in lines:
            row = line.decode()
            yield (line_templ % line_regex.match(row).groups())

    def extract_rows(self, num: int = 5):
        rows = []
        for item in self._itr:
            rows.append(item)
            if len(rows) == num:
                break
        return ','.join(rows)

    def wrk_scan_matching(self, val: str):
        self._th = threading.Thread(target=self._lib.sm_backend_exec_cmd,
                              name='scanmem-worker',
                              args=(ctypes.c_char_p(val.encode()),))
        self._th.start()

    def switch(self, cmd: str):
        do_exit = not cmd or cmd.startswith('exit')
        res     = ''
        if IS_DEBUG:
            print('Scanmem @ '+ ('cleanup and exit..' if do_exit else f'[{cmd}]'))
        if do_exit:
            self.exit_cleanup()
            return ('', False)
        if cmd.startswith('list') or cmd.startswith('next'):
            idx = cmd.find('L')
            if not cmd.startswith('next'):
                self.dump_command(cmd if idx == -1 else cmd[:idx-1])
            res = self.extract_rows(5 if idx == -1 else ord(cmd[idx+1:]))
        elif cmd.startswith('dump'):
            res = self.dump_command(cmd, True)
        elif cmd.startswith('info'):
            res = self.get_match_info(cmd[4:].strip())
        elif cmd.startswith('pgss'):
            res = self.get_scan_progress()
        elif cmd.startswith('stop'):
            self.set_stop_flag()
        elif cmd.startswith('find'):
            self.wrk_scan_matching(cmd[5:])
        elif cmd.startswith('reset'):
            self.process_reset(cmd[5:].strip())
        else: # possible options separated by lines
            for opt in cmd.splitlines():
                self.exec_command(opt.strip())
        return (res, True)

    def listener(self, connect: socket.socket):
        loop = True
        while loop: # receive data from the server
            data = connect.recv(1024)
            try:
                resp, loop = self.switch(data.decode())
            except Exception as e:
                resp = '{"error":"%s"}'% e.args[0]
            finally:
                # Send a response back to the server
                connect.sendall(f'[{resp}]'.encode())


if __name__ == '__main__':
    # Create unix socket for connect GameConqueror server
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(SOC_PATH)
    try:
        backend = Scanmem()
        backend.listener(client)
    finally:
        client.shutdown(socket.SHUT_WR)
        time.sleep(1)
        client.close()
