
#include "config.h"

#include <string.h>
#include <unistd.h>

#include "messages.h"
#include "procmaps.h"

#define Cpy_ExtraData(_T,_M,_E) memcpy(malloc(sizeof(_T)+_E), _M, sizeof(_T))

/*
 * get the load address for regions of the same ELF file
 *
 * When the ELF loader loads an executable or a library into
 * memory, there is one region per ELF segment created:
 * .text (r-x), .rodata (r--), .data (rw-) and .bss (rw-). The
 * 'x' permission of .text is used to detect the load address
 * (region start) and the end of the ELF file in memory. All
 * these regions have the same regfile. The only exception
 * is the .bss region. Its regfile is empty and it is
 * consecutive with the .data region. But the regions .bss and
 * .rodata may not be present with some ELF files. This is why
 * we can't rely on other regions to be consecutive in memory.
 * There should never be more than these four regions.
 * The data regions use their variables relative to the load
 * address. So determining it makes sense as we can get the
 * variable address used within the ELF file with it.
 * But for the executable there is the special case that there
 * is a gap between .text and .rodata. Other regions might be
 * loaded via mmap() to it. So we have to count the number of
 * regions belonging to the exe separately to handle that.
 * References:
 * http://en.wikipedia.org/wiki/Executable_and_Linkable_Format
 * http://wiki.osdev.org/ELF
 * http://lwn.net/Articles/531148/
 */

bool sm_read_procmaps(list_t *regions, pid_t procid, region_scan_level_t scan_level, bool json_msg)
{
	FILE *maps;

	unsigned int code_regions = 0, reg_len = 0, dev_major, offset;
	unsigned int  exe_regions = 0, ecode   = 0, dev_minor, inode;

	unsigned long prev_end = 0, cur_end = 0, cur_start = 0;
	unsigned long load_exe = 0, ld_addr = 0;

	bool is_exe = false;

# define MAX_LNKBUF_L 256
# define _RWEC proclnk

	char exename[MAX_LNKBUF_L], linebuf[MAX_LNKBUF_L*2];
	char binname[MAX_LNKBUF_L], proclnk[MAX_LNKBUF_L/8], *regfile;

	// check if target is valid and region is not null
	if (!procid || !regions || !(regions->size >= 0))
		return false; // if we have uninitialized data pointer, reading size maybe throw a signal

	// initialise to zero
	for (int i = 0; i < MAX_LNKBUF_L; i++)
		exename[i] = binname[i] = '\0';

	// construct the maps regfile
	int k = snprintf(proclnk, sizeof(proclnk), "/proc/%u/maps", procid) - 4;

	// attempt to open the maps file
	if (!(maps = fopen(proclnk, "r"))) {
		SM_Message(json_msg ? "{"F_JSON_STR("error","%s `%s`")"}" :
		/* - - - - - - - - - -*/ F_TEXT_MSG("error","%s `%s`"),
			lStr("failed to open"), proclnk);
		return false;
	} else if (!json_msg)
		SM_Info("maps file located at %s opened", proclnk);

	proclnk[k+0] = 'e', proclnk[k+2] = 'e',
	proclnk[k+1] = 'x', proclnk[k+3] = '\0';

	// get executable name
	if((k = readlink(proclnk, exename, sizeof(proclnk))) == -1) {
		k = 0; // readlink may fail for special processes,
	} else {
		SM_Debug("%s", exename);
	}
	exename[k] = '\0';

	// read every line of the maps file
	while (fgets(linebuf, sizeof(linebuf), maps) && ecode == 0)
	{
		region_t *map, mm = {
			.id   = regions->size, // add a unique identifier
			.type = REGION_TYPE_MISC,
			.size = 0,
			.start = NULL,
			.filename[0] = '\n' // match end of line if region filepath is empty
		};
		// clearing buffer, before write permissions chars
		_RWEC[0] =_RWEC[1] =_RWEC[2] =_RWEC[3] =_RWEC[4] = '\0';

		if (sscanf(linebuf, "%lx-%lx %4c %x %x:%x %u %c", &cur_start, &cur_end,
			_RWEC, &offset, &dev_major, &dev_minor, &inode, mm.filename
		) < 6) {
			continue;
		}
		// find the filepath by givin char
		reg_len = strlen(regfile = strchr(linebuf, mm.filename[0]));
		// clear end line character from region filepath
		if (reg_len != 0 && regfile[reg_len-1] == '\n')
			reg_len -= 1,   regfile[reg_len  ] =  '\0';
		// initialize region start and size
		mm.start = (void *) cur_start;
		mm.size = cur_end - cur_start;
		// setup other permissions
		mm.flags.read    = (_RWEC[0] == 'r');
		mm.flags.write   = (_RWEC[1] == 'w');
		mm.flags.exec    = (_RWEC[2] == 'x');
		mm.flags.shared  = (_RWEC[3] == 's');
		mm.flags.private = (_RWEC[3] == 'p');
		// detect further regions of the same ELF file and its end
		if (code_regions > 0) {
			if (mm.flags.exec ||
				(strncmp(regfile, binname, MAX_LNKBUF_L) && (reg_len || cur_start != prev_end)) 
			|| code_regions >= 4) {
				code_regions = 0;
				is_exe = false;
				// exe with .text and without .data is impossible
				if (exe_regions > 1)
					exe_regions = 0;
			} else {
				code_regions++;
				if (is_exe)
					exe_regions++;
			}
		}
		if (code_regions == 0) {
			// detect the first region belonging to an ELF file
			if (mm.flags.exec && reg_len) {
				code_regions++;
				if (!strncmp(regfile, exename, MAX_LNKBUF_L)) {
					exe_regions = 1;
					load_exe = cur_start;
					is_exe = true;
				}
				strncpy(binname, regfile, MAX_LNKBUF_L);
				binname[MAX_LNKBUF_L - 1] = '\0'; // just to be sure
				// detect the second region of the exe after skipping regions
			} else
			if (exe_regions == 1 && reg_len && !strncmp(regfile, exename, MAX_LNKBUF_L))
			{
				code_regions = ++exe_regions;
				ld_addr = load_exe;
				is_exe = true;
				strncpy(binname, regfile, MAX_LNKBUF_L);
				binname[MAX_LNKBUF_L - 1] = '\0'; // just to be sure
			}
			if (exe_regions < 2)
				ld_addr = cur_start;
		}
		prev_end = cur_end;
		// must have permissions to read and be non-zero size
		if (mm.flags.read && mm.size)
		{
			bool useful = false;
			// determine region type
			if (is_exe)
				mm.type = REGION_TYPE_EXE;
			else if (code_regions > 0)
				mm.type = REGION_TYPE_CODE;
			else if (!strcmp(regfile, "[heap]"))
				mm.type = REGION_TYPE_HEAP;
			else if (!strcmp(regfile, "[stack]"))
				mm.type = REGION_TYPE_STACK;

			if (scan_level != REGION_ALL && !mm.flags.write)
			{
				// Only REGION_ALL scans non-writable memory regions
				continue;
			}
			// determine if this region is useful
			switch (scan_level) {
			case REGION_ALL:    useful = true; break;
			case REGION_ALL_RW: useful = true; break;
			case REGION_HEAP_STACK_EXECUTABLE_BSS:
				if (!reg_len) {
					useful = true;
					break;
				}
				// fall through
			case REGION_HEAP_STACK_EXECUTABLE:
				if (mm.type == REGION_TYPE_HEAP || mm.type == REGION_TYPE_STACK) {
					useful = true;
				} else
				// test if the region is mapped to the executable
				if (mm.type == REGION_TYPE_EXE || !strncmp(regfile, exename, MAX_LNKBUF_L))
					useful = true;
				break;
			}
			if (useful) {
				mm.filename[0] = '\0';
				mm.load_addr = ld_addr;
				// allocate a new region structure
				if (!(map = Cpy_ExtraData(region_t, &mm, reg_len))) {
					ecode = 1;
				} else
				// okay, add this guy to our list
				if (l_append(regions, regions->tail, map) == -1) {
					ecode = 2;
				} else
				// save pathname
				if (reg_len) {
					// the pathname is concatenated with the structure
					strncpy(map->filename, regfile, reg_len);
					map->filename[reg_len] = '\0';
				}
# ifdef DEBUG
				SM_Debug("id(%d):%i\taddr(%d):%p\tsize(%d):%lu\ttype(%d):%i\tld(%d):%lx\t%s(%d)\t%s:%u/%lu",
					mm.id        == map->id       , mm.id,
					mm.start     == map->start    , mm.start,
					mm.size      == map->size     , mm.size,
					mm.type      == map->type     , mm.type,
					mm.load_addr == map->load_addr, mm.load_addr, _RWEC,
					mm.flags.v   == map->flags.v  , regfile, reg_len, strlen(map->filename)
				);
# endif
			}
		}
	};
	// close `/proc/{pid}/maps`
	fclose(maps); 

	if (ecode) {
		const char *err_msg[] = {
			"failed to allocate memory for region",
			"failed to save region"
		};
		SM_Message(json_msg ? "{"F_JSON_STR("error","%s")"}" :
		/* - - - - - - - - - */  F_TEXT_MSG("error","%s"), lStr(err_msg[ecode-1]));
	}
	else if (json_msg)
		SM_Message("{"F_JSON_NUM("regions_count","%lu")","F_JSON_STR("exelink","%s")"}", regions->size, exename);
	else
		SM_Message( F_TEXT_MSG("info","%lu %s"), regions->size, lStr("suitable regions found"));

	return !ecode;
}
