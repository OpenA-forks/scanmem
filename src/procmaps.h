/*
    Reading the data from /proc/pid/maps into a regions list.

    Copyright (C) 2006,2007,2009 Tavis Ormandy <taviso@sdf.lonestar.org>
    Copyright (C) 2009           Eli Dupree <elidupree@charter.net>
    Copyright (C) 2009,2010      WANG Lu <coolwanglu@gmail.com>
    Copyright (C) 2014-2016      Sebastian Parschauer <s.parschauer@gmx.de>

    This file is part of libscanmem.

    This library is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this library.  If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef PROCMAPS_H
# define PROCMAPS_H
# include <stdbool.h>
# include <sys/types.h>

# include "list.h"

# define REGION_TYPE_NAMES { "misc", "code", "exe", "heap", "stack" }

// determine which regions we need
enum region_scan_level {
	REGION_ALL,                       // All regions, including non-writable regions
	REGION_ALL_RW,                    // each of them
	REGION_HEAP_STACK_EXECUTABLE,     // heap, stack, executable
	REGION_HEAP_STACK_EXECUTABLE_BSS  // heap, stack, executable, bss
};

enum region_type {
	REGION_TYPE_MISC,
	REGION_TYPE_CODE,
	REGION_TYPE_EXE,
	REGION_TYPE_HEAP,
	REGION_TYPE_STACK
};

enum memdump_out_type {
	MEMDUMP_TO_STDOUT,
	MEMDUMP_TO_BUFFER,
	MEMDUMP_TO_FILE
};

typedef unsigned char region_scan_level_t;
typedef unsigned char region_type_t;

// a region obtained from /proc/pid/maps, these are searched for matches
typedef struct {
	void *start;             // Start address. Hack: If HAVE_PROCMEM is defined, this is actually an (unsigned long) offset into /proc/{pid}/mem
	unsigned long size;      // segment size
	unsigned long load_addr; // e.g. load address of the executable
	unsigned int  id;        // unique identifier
	region_type_t type;
	union region_rwec {
		struct { bool read:1, write:1, exec:1, shared:1, private:1; };
		unsigned char v;
	} flags;
	char filename[1]; // associated file, must be last
} region_t;

bool sm_read_procmaps(list_t *regions, pid_t procid, enum region_scan_level scan_lvl, bool json_msg);

/**
 * reads bytes from `proc/{pid}/mem` and writes to out.
 *
 * @param out       can be memory allocated buffer, or just a string with a filepath
 * @param out_type  defines that kind of `out` is
 */
bool sm_read_procmem(void *out, pid_t procid, enum memdump_out_type out_type, uintptr_t base_addr, size_t nbytes, bool json_msg);

#endif
