/*
    Scanmem main function, option parsing and help text.

    Copyright (C) 2006,2007,2009 Tavis Ormandy <taviso@sdf.lonestar.org>
    Copyright (C) 2009           Eli Dupree <elidupree@charter.net>
    Copyright (C) 2009-2013      WANG Lu <coolwanglu@gmail.com>
    Copyright (C) 2016           Sebastian Parschauer <s.parschauer@gmx.de>

    This file is part of scanmem.
 
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
*/
#include "config.h"

#include "common.h"
#include "scanmem.h"
#include "commands.h"
#include "show_message.h"

#include "menu.h"

#include "sys.h"
#include "messages.h"
#include "parseopt.c"

#ifdef HAVE_READLINE
# define HIST_MAX_SIZE 1000
# include <readline/history.h>
#else
# include "readline.h"
#endif

# define HINT_ENTER_PID  "Enter the process ID using the `pid` command to get started"
# define HINT_TYPE_VALUE "Type a value to start scanning"
# define HINT_ENTER_HELP "Enter `help` at the prompt for further assistance"

# define COPYRIGHT_TEXT \
	"\n<~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~(!)~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~>\n"\
	"Copyright (C) 2006-2017 Scanmem authors\n"\
	"See " SCANMEM_HOMEPAGE "/blob/main/AUTHORS for a full author list\n\n"\
	"scanmem comes with ABSOLUTELY NO WARRANTY; for details type `show warranty'.\n"\
	"This is free software, and you are welcome to redistribute it\n"\
	"under certain conditions; type `show copying' for details."\
	"\n<~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~x~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~>\n"

// print quick or full help usage message
static void print_help(bool is_quick)
{
# define POSSIBLE_OPTS \
	" -pid={Int}    %s\n"\
	" -ipc={Str}    %s\n"\
	" -cmd=[;]      %s `;`\n"\
	" -help         %s\n"\
	" -version      %s\n"

	if (!is_quick) {
		printf("\n%s\n\n%s — " SCANMEM_HOMEPAGE "/issues\n",
			lStr("scanmem is an interactive debugging utility\nthat finds and modify variables in an executing process."),
			lStr("Report bugs to"));
	}
	printf("\nUsage: scanmem [ -opt[='val'] ...] {pid}\n\n" POSSIBLE_OPTS "\n%s\n\n",
		// options descriptions 
		lStr("the target process id"),
		lStr("path to remote socket interface"),
		lStr("list of commands separated by"),
		lStr("show this help"),
		lStr("show program version"),
		// hint
		lStr(HINT_ENTER_HELP));
}

static bool iter_exec_commands(globals_t *vars, char *cmd, bool exit_on_err)
{
	// this will initialize matches and regions
	if (!sm_execcommand(vars, "reset")) {
		vars->target = 0;
	}
	// iterate list of commands
	if (cmd && (cmd = strtok(cmd, ";\n")))
	do {
		if (vars->matches) {
			printf("%ld> %s\n", vars->num_matches, cmd);
		} else {
			printf("> %s\n", cmd);
		}
		if (!sm_execcommand(vars, cmd)) {
			if (exit_on_err)
				return false;
			SM_Hint(vars->target ? HINT_TYPE_VALUE : HINT_ENTER_PID, "");
			SM_Hint(HINT_ENTER_HELP, "\n");
		}
		fflush(stdout);
		fflush(stderr);

	} while ((cmd = strtok(NULL, ";\n")));
	// returns exit flag
	return !vars->exit;
}

static int iter_main_loop(globals_t *vars, struct sys_path *cfg_dir)
{
# ifdef HAVE_READLINE
	const char *hist_file = sys_extend_path(cfg_dir, "/history", false);
	// recover history from history file
	read_history(hist_file);
# endif
	// main loop, read input and process commands
	do {
		char *cmd;
		// reads in a commandline from the user and returns a pointer to it in *line
		if (!getcommand(vars, &cmd)) {
			SM_Error("failed to read in a command");
			return EXIT_FAILURE;
		}
		// returning failure is not fatal, it just means the command could not complete.
		if (!sm_execcommand(vars, cmd)) {
			SM_Hint(vars->target ? HINT_TYPE_VALUE : HINT_ENTER_PID, "");
			SM_Hint(HINT_ENTER_HELP, "\n");
		}
		free(cmd);
		fflush(stdout);
		fflush(stderr);

	} while(!vars->exit);

#ifdef HAVE_READLINE
	/* write history: create directory if needed.
	 * Permissions used are mandated by the FD spec:
	 * https://standards.freedesktop.org/basedir-spec/latest/ar01s04.html
	 */
	if (sys_mkcdir(cfg_dir, 0700)) {
		write_history(hist_file);
		history_truncate_file(hist_file, HIST_MAX_SIZE);
	}
#endif
	return EXIT_SUCCESS;
}

static int iter_main_sock(globals_t *vars, const char *ipc_port) {
	return EXIT_SUCCESS;
}

void print_output() {
	/* ... */
}

int main(int argc, char *const argv[])
{
	/*~*/ char *cmd_iter;
	const char *ipc_port;
	struct opt_params opts = parse_parameters(argc, argv, &cmd_iter, &ipc_port);
	struct sys_path sm_appcfg;

	if (opts.print_help || opts.wrong_opt) {
		print_help( opts.wrong_opt );
		return opts.wrong_opt ? EXIT_FAILURE : EXIT_SUCCESS;
	}
	if (opts.print_vers) {
		puts(SCANMEM_VERSION);
		return EXIT_SUCCESS;
	}
	if (sys_access_config_dir(&sm_appcfg) == 0) {
		opts.is_usr_root = true;
	}
	sys_extend_path(&sm_appcfg, "scanmem", true);

	(&sm_globals)->printversion = print_output;
	(&sm_globals)->target = (pid_t)opts.procid;

	int ret = EXIT_SUCCESS;
	// LIB Initialization
	if (!sm_init()) {
		SM_Error("Initialization failed");
		ret = EXIT_FAILURE;
	} else
	// Start of interactive mode
	if (ipc_port) {
		ret = iter_main_sock(&sm_globals, ipc_port);
	} else {
		puts(COPYRIGHT_TEXT);
		if (!opts.is_usr_root) {
			SM_Warn("Run scanmem as root if memory regions are missing",
					"See the man page for more details");
		}
		// check if there is a target already specified
		if (opts.wrong_pid) {
			SM_Error("Invalid PID specified");
		}
		SM_Hint(opts.procid ? HINT_TYPE_VALUE : HINT_ENTER_PID, "");
		SM_Hint(HINT_ENTER_HELP, "\n");

		// execute commands passed by `-cmd=[;]`, returns exit flag
		if (iter_exec_commands(&sm_globals, cmd_iter, opts.onerr_exit))
			ret = iter_main_loop(&sm_globals, &sm_appcfg);
	}
// exit_cleanup:
	sm_cleanup();
	return ret;
}
