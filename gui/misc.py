"""
    Misc functions for Game Conqueror
    
    Copyright (C) 2010,2011,2013 Wang Lu <coolwanglu(a)gmail.com>
    Copyright (C) 2013 Mattias <mattiasmun(a)gmail.com>
    Copyright (C) 2016 Andrea Stacchiotti <andreastacchiotti(a)gmail.com>

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

import os, socket, struct, platform

SEARCH_SCOPE_NAMES = ['Basic', 'Normal', 'ReadOnly', 'Full']

LOCK_FLAG_TYPES = ['=', '+', '-']

SCAN_VALUE_TYPES = ['int8', 'int16', 'int32', 'int64', 'float', 'float32', 'float64', 'number', 'bytearray', 'string']

MEMORY_TYPES = ['int8', 'uint8','int16', 'uint16', 'int32', 'uint32','int64', 'uint64','float32', 'float64', 'bytearray', 'string']

# 0: sizes in bytes of integer and float types
# 1: struct format characters for convert typenames
TYPESIZES_G2S = {
    'int8' :(1,'b'), 'uint8' :(1,'B'),
    'int16':(2,'h'), 'uint16':(2,'H'),
    'int32':(4,'i'), 'uint32':(4,'I'), 'float32':(4,'f'),
    'int64':(8,'q'), 'uint64':(8,'Q'), 'float64':(8,'d')
}
# convert type names used by scanmem into ours
TYPENAMES_S2G = {
    'I8' :'int8' ,'I8s' :'int8' ,'I8u' :'uint8',
    'I16':'int16','I16s':'int16','I16u':'uint16',
    'I32':'int32','I32s':'int32','I32u':'uint32','F32':'float32',
    'I64':'int64','I64s':'int64','I64u':'uint64','F64':'float64',

    'bytearray':'bytearray',
    'string':'string'
}

# check command syntax, data range etc.
# return a valid scanmem command
# raise if something is invalid
def check_scan_command(data_type: str, cmd: str, is_first_scan=True):

    if cmd == '':
        raise ValueError('No value provided')
    if data_type == 'string':
        return '" '+ cmd

    cmd = cmd.strip()
    # hack for snapshot/update (TODO: make it possible with string)
    if cmd == '?':
        return 'snapshot' if is_first_scan else 'update'

    if data_type == 'bytearray':
        bytes = cmd.split(' ')
        for byte in bytes:
            if byte.strip() == '':
                continue
            if len(byte) != 2:
                raise ValueError('Bad value: %s' % byte)
            if byte == '??':
                continue
            try:
               _tmp = int(byte,16)
            except:
                raise ValueError('Bad value: %s' % byte)
        return cmd
    else: # for numbers
        is_operator_cmd = cmd in {'=', '!=', '>', '<', '+', '-'}
        if not is_first_scan and is_operator_cmd:
            return cmd

        if is_first_scan and (is_operator_cmd or cmd[:2] in {'+ ', '- '}):
            raise ValueError('Command \"%s\" is not valid for the first scan' % cmd[:2])

        # evaluating the command
        range_nums = cmd.split("..")
        if len(range_nums) == 2:
            # range detected
            num_1 = eval_operand(range_nums[0])
            num_2 = eval_operand(range_nums[1])
            cmd = str(num_1) + ".." + str(num_2)
            check_int(data_type, num_1)
            check_int(data_type, num_2)
        else:
            # regular command processing
            if cmd[:2] in {'+ ', '- ', '> ', '< '}:
                num = cmd[2:]
                cmd = cmd[:2]
            elif cmd[:3] ==  '!= ':
                num = cmd[3:]
                cmd = cmd[:3]
            else:
                num = cmd
                cmd = ''
            num = eval_operand(num)
            cmd += str(num)
            check_int(data_type, num)

        # finally
        return cmd

# evaluate the expression
def eval_operand(s: str):
    try:
        v = eval(s)
        if isinstance(v, int) or isinstance(v, float):
            return v
    except:
        pass
    raise ValueError('Bad value: %s' % s)

# check if a number is a valid integer
# raise an exception if not
def check_int(data_type: str, num: str):
    if data_type[0:3] == 'int':
        if not isinstance(num, int):
            raise ValueError('%s is not an integer' % num)
        if data_type == 'int':
            width = 64
        else:
            width = int(data_type[3:])
        if num > ((1<<width)-1) or num < -(1<<(width-1)):
            raise ValueError('%s is too bulky for %s' % (num, data_type))
    return

# return the size in bytes of the value in memory
def get_type_size(data_type: str, data: bytearray | str | int):
    # int or float type; fixed length
    if data_type in TYPESIZES_G2S:
        return TYPESIZES_G2S[data_type][0]
    elif data_type == 'bytearray':
        return (len(data.strip())+1)/3
    elif data_type == 'string':
        return len(data.encode())
    return -1

# parse bytes dumped by scanmem into number, string, etc.
def bytes2value(data_type: str, data: bytearray | str | int):
    if data_type is None:
        return None
    elif data_type in TYPESIZES_G2S:
        return struct.unpack(TYPESIZES_G2S[data_type][1], data)[0]
    elif data_type == 'string':
        return data.decode(errors='replace')
    elif data_type == 'bytearray':
        data = bytearray(data)
        return ' '.join(['%02x' %(i,) for i in data])
    else:
        return data

# return negative if unknown
def get_pointer_width():
    bits = platform.architecture()[0]
    if bits.endswith('bit'):
        try:
            nb = int(bits[:-3])
            if nb in {8,16,32,64}:
                return nb
        except:
            pass
    return -1

def read_proc_maps(pid: int | str):
    maps = []
    for line in open(f'/proc/{pid}/maps').readlines():
        info = line.split(' ', 5)
        start, end = [int(h,16) for h in info[0].split('-')]
        maps.append({
            'start_addr': start,
            'end_addr'  : end,
            'flags'     : info[1],
            'offset'    : info[2],
            'dev'       : info[3],
            'inode'     : int(info[4]),
            'pathname'  : '' if len(info) < 6 else info[5].lstrip(), # don't use strip
            'size'      : end - start
        })
    return maps

def get_process_list(exclude_usr: str = 'root'):
    for proc in os.popen('ps -wweo pid=,user:16=,command= --sort=-pid').readlines():
        tok = proc.split(maxsplit=2)
        pid = tok[0].strip()
        usr = tok[1].strip() if len(tok) >= 2 else '<???>'
        exe = tok[2].strip() if len(tok) >= 3 else ''
        if exclude_usr and (usr == exclude_usr):
            continue
        # process name may be empty, but not the name of the executable
        if not exe:
            exelink = os.path.join('/proc',pid,'exe')
            if os.path.exists(exelink):
                exe = os.path.realpath(exelink)
        yield (int(pid), usr, exe)

def wait_connection(soc_path: str):
    # Create the Unix socket server for connect scanmem backend
    server  = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Bind the socket to the path
    server.bind(soc_path)
    # Listen for incoming connections
    server.listen(1)
    # accept connections
    return server.accept()
