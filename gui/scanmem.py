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

import os, re, tempfile, socket, json

SOCK_PATH = os.environ['SCANMEM_SOCKET'] # /tmp/scanmem-X.X~dev-socket

FIND_MATCH = ['eq', 'lt', 'gt', 'ne', 'le', 'ge', 'ic', 'dc']
TYPE_NAMES = ['i8', 'i16', 'i32', 'i64', 'f32', 'f64', 'str', 'a8u']
TYPE_SIZES = [1, 2, 4, 8, 4, 8, 0, 0]

class Scanmem():
    """Wrapper for libscanmem."""

    def __init__(self, pid = '', debug_mode = False):
        self._serv : socket.socket = None
        self._cpid : str = pid
        # public flags
        self.is_debug  : bool = debug_mode
        self.num_signed: bool = True
        self.match_type: int  = 0 # equal
        self.scan_scope: int  = 1 # Normal
        self.scan_type : int  = 2 # Int32
        # private flags
        self._is_firstRun = True
        self._is_scanning = False
        self._is_waiting = False
        self._is_exiting = False # currently for data_worker only, other 'threads' may also use this flag

    def read_memory(self, addr: int, nb: int):
        """
        Execute command using libscanmem.
        This function is NOT thread safe, send only one command at a time.
        
        cmd: command to run
        raw_out: if True, return in a string what libscanmem would print to stdout
        """
        tmp_name = emsg = ''

        with tempfile.NamedTemporaryFile(suffix='-dmem') as tmp_file:
            tmp_name = tmp_file.name

        data = self.send_command('dump %x %i %s' % (addr, nb, tmp_name))
        mbuf : bytes = None

        if 'error' in data:
            emsg : str = data['error']
        elif data['total_readed'] == 0:
            emsg : str = 'Cannot access target memory'
        else:
            with open(tmp_name, mode='rb') as dump_file:
                ____ = dump_file.seek(0)
                mbuf = dump_file.read()
        return (mbuf, emsg)

    def send_command(self, cmd: str, cap = 1024):
        """
        Sends commands to the backend via UNIX socket and receives JSON objects in response

        """ ; self._serv.sendall(cmd.encode() + b'\0')
        buf = self._serv.recv(cap)
        try:
            dat = json.loads(buf)
        except Exception as e:
            cmd = cmd.split(' ',1)[0]
            dat = dict([ ('error', f'`{cmd}` @ {e} => {buf}') ])
            pass
        finally:
            return dat

    def start_scanning(self, val: int|str):
        """
        ------

        """  ; self._is_scanning = True
        data = self.send_command(f'find {FIND_MATCH[self.match_type]}:{TYPE_NAMES[self.scan_type]} {val}')
        emsg = ''
        if 'error' in data:
            emsg : str = data['error']
        return (not self._is_firstRun, emsg)

    def get_scan_progress(self):
        pgss = 0.0; mcnt = 0
        data = self.send_command('info')
        emsg = ''
        if 'error' in data:
            emsg : str   = data['error']
        else:
            mcnt : int   = data['match_count']
            pgss : float = data['scan_progress']
        return (emsg, pgss, mcnt)

    def stop_scanning(self):
        """
        Sets the flag to interrupt the current scan at the next opportunity

        """  ; self._is_scanning = False
        data = self.send_command('stop')
        emsg = ''
        if 'error' in data:
            emsg : str = data['error']
        return (not self._is_firstRun, emsg)

    def exit_cleanup(self):
        """
        Frees resources allocated by libscanmem, should be called before disposing of this instance

        """  ; self._is_exiting = True
        data = self.send_command('exit')
        if 'error' in data:
            print('✖︎ ERROR: '+ data['error'])

    def reset_process(self):
        rcnt = 0
        data = self.send_command(f'rset [{self.scan_scope + 1}] {self._cpid}')
        emsg = link = ''
        if 'error' in data:
            emsg : str = data['error']
        else:
            rcnt : int = data['regions_count']
            link : str = data['exelink']
        return (emsg, rcnt, link)

    def get_list_matches(self, count: int):
        """
        Returns a generator of (match_id_str, addr_str, off_str, region_type, value, types_str) for each match, all strings.
        The function executes commands internally, it is NOT thread safe
        """
        line_templ = '{"match_id":%s,"addr":"%s","off":"%s","region_type":"%s","value":%s,"types":"%s"}'
        line_regex = re.compile(r'^\[ *(\d+)\] +([\da-f]+), +\d+ \+ +([\da-f]+), +(\w+), (.*), +\[([\w ]+)\]$')
        name_templ = emsg = ''

        with tempfile.NamedTemporaryFile(suffix='-mlist') as tmp_file:
            name_templ = tmp_file.name

        data = self.send_command(f'list {count} {name_templ}')
        mlst = []

        if 'error' in data:
            emsg : str = data['error']
        else:
            with open(name_templ, mode='r') as templ_file:
                ______ = templ_file.seek(0)
                for m in templ_file.readlines():
                    m = line_templ % line_regex.match(m).groups()
                    mlst.append(json.loads(m))
        return (mlst, emsg)

    def load_cheat_list(self, filepath: str):
        with open(filepath, mode='r') as f:
            dat = json.load(f)
            return dat['cheat_list']

    def store_cheat_list(self, filepath: str, cheat_list: list):
        dat = dict([('cheat_list', [])])
        for ch in cheat_list:
            dat['cheat_list'].append({
                'desc' : ch[1],
                'addr' : ch[2],
                'type' : ch[3],
                'value': ch[4]
            })
        with open(filepath, mode='w') as f:
            json.dump(dat, f)

    def switch(self, cmd: str):
        do_exit = not cmd or cmd.startswith('exit')
        res     = ''
        if self.is_debug:
            print('Scanmem @ '+ ('cleanup and exit..' if do_exit else f'[{cmd}]'))
        if do_exit:
            self.exit_cleanup()
            return ('', False)
        if cmd.startswith('list') or cmd.startswith('next'):
            idx = cmd.find('L')
            if not cmd.startswith('next'):
                self.dump_command(cmd if idx == -1 else cmd[:idx-1])
            res = self.extract_rows(5 if idx == -1 else int(cmd[idx+1:]))
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

    def socket_server(self):
        # Create unix socket server for connect scanmem client
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Bind the socket to the path
        server.bind(SOCK_PATH)
        # Listen for incoming connections
        server.listen(1)
        # accept connections
        self._serv,_ = server.accept()

    def close_server(self):
        # close the connection
        self._serv.close()
        # remove the socket file
        os.unlink(SOCK_PATH)
