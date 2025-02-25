
#include <getopt.h>
#include <stdlib.h>
#include <stdbool.h>

struct opt_params {
	unsigned procid:22, _r:3, // max_pid = 4,194,304

	print_help:1, wrong_opt:1, onerr_exit:1,
	print_vers:1, wrong_pid:1, debug_mode:1, is_usr_root:1;
};

struct opt_params parse_parameters(int argc, char *const argv[], char **cmd_list, const char **ipc_path)
{
	struct opt_params vars = {0,0,0,0,0,0,0,0};
	struct option lopts[] = {
		{"pid", required_argument, NULL, 'p'}, // target pid
		{"ipc", required_argument, NULL, 's'}, // interactive connection via socket
		{"cmd", required_argument, NULL, 'c'}, // commands to run at the beginning
		{"version",   no_argument, NULL, 'v'}, // print version
		{"help",      no_argument, NULL, 'h'}, // print help summary
		{"dbg",       no_argument, NULL, 'd'}, // enable debug mode
		{"eno",       no_argument, NULL, 'e'}, // exit on initial command failure
		{ NULL,                 0, NULL,'\0'},
	};
	// process command line
	for (int li = 0; optind < argc;)
	{
		switch (getopt_long_only(argc, argv, "", lopts, &li))
		{ // parse any pid specified after arguments
		case -1: optarg = argv[optind++];
			// ignore if pid sets by option flag
			if (vars.procid)
				break;
		case 'p':
			// check if that parsed correctly
			if ((li = atoi(optarg)) > 0) {
				vars.procid = li;
			} else
				vars.wrong_pid = true;
			break;
		case 's': *ipc_path = optarg; break;
		case 'c': *cmd_list = optarg; break;

		case 'd': vars.debug_mode = true; break;
		case 'e': vars.onerr_exit = true; break;
		case 'v': vars.print_vers = true; break;
		case 'h': vars.print_help = true; break;
		default : vars.wrong_opt  = true; // '?'
		}
	}
	return vars;
}
