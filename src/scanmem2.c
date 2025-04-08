
#include <stdarg.h>

#include "config.h"
#include "scanmem2.h"

#include "scanmem.c"

void sm_message(const char *fmt, ...)
{
	va_list  args;
	va_start(args  , fmt);
	vfprintf(stderr, fmt, args);
	va_end  (args);
}

bool sm_reset_process(globals_t *p)
{
	bool json_flag = p->options.backend;
	// reset matches and regions
	if (p->matches)
		 free(p->matches);
	l_destroy(p->regions);

	// reset scan progress and matches
	p->scan_progress = 0.0;
	p->matches = NULL;
	p->num_matches = 0;

	// create a new linked list of regions
	if (!(p->regions = l_init())) {
		SM_Message(json_flag ? "{"F_JSON_STR("error","%s")"}" :
		/* ------------------- */ F_TEXT_MSG("error","%s"),
			lStr("sorry, there was a problem allocating memory."));
		return false;
	} else
	// read in maps if a pid is known
	if (p->target && !sm_read_procmaps(p->regions, p->target, p->options.region_scan_level, json_flag)) {
		p->target = 0;
		SM_Message(json_flag ? "{"F_JSON_STR("error","%s")","F_JSON_STR("warn","%s")"}" :
		/* ------------------- */ F_TEXT_MSG("error","%s")   F_TEXT_MSG("warn","%s"),
			lStr("sorry, there was a problem getting a list of regions to search."),
			lStr("the pid may be invalid, or you don't have permission."));
		return false;
	}
	return true;
}
