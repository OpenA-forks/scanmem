

#ifndef _SYS_H
# define _SYS_H

# include <pwd.h>
# include <errno.h>
# include <string.h>
# include <unistd.h>
# include <stdbool.h>

# include <sys/types.h>
# include <sys/stat.h>

#if HAVE_SYS_SOCK_H
# include <sys/socket.h>
# include <sys/un.h>
#endif
# define SYS_MAXBUF 1024

#if HAVE_SECURE_GETENV
# define _GET_ENV secure_getenv
#else
# define _GET_ENV getenv
#endif

# define SYS_PATH_L 1024
# define SYS_PATH_C '/'

struct sys_path {
	unsigned short dirpos;
	char path[SYS_PATH_L];
};

/*
 * Try to find our config folder in order:
 * - XDG config dir
 * - <system-given home>/.config
 *
 * In normal cases the dir will end up being: $HOME/.config/scanmem
 */
static inline uid_t sys_access_config_dir(struct sys_path *cfg)
{
	const char *home_dir, *conf_dir = "/";
	uid_t usr_id = getuid();

	if (!(home_dir = _GET_ENV("XDG_CONFIG_HOME"))) {
		home_dir = getpwuid(usr_id)->pw_dir;
		conf_dir = "/.config/";
	}
	cfg->dirpos  = strlen(
		conf_dir = strcat(strcpy(cfg->path, home_dir), conf_dir)
	);
	if (mkdir(conf_dir, 0755) == -1)
		/* maybe exists */;
	return usr_id;
}

# define sys_trunc_dir_path(p) ((p)->path[p->dirpos] = '\0')
# define sys_restor_to_file(p) ((p)->path[p->dirpos] = SYS_PATH_C)

static inline const char *sys_extend_path(struct sys_path *dir, const char *name, bool is_dirname)
{
	int i = 0, k = dir->dirpos;
	while (k < SYS_PATH_L && (dir->path[k] = name[i]) != '\0')
		i++, k++;
	if (is_dirname)
		dir->dirpos = k;
	return dir->path;
}

/* Recursive `mkdir()` implementation, from
 * https://stackoverflow.com/a/9210960/3288954
 * Takes a full file path as input */
static inline int sys_mkpath(struct sys_path *dir, mode_t mode)
{
	char *p = dir->path;
	for (int c = 0; p[c] != '\0'; c++) {
		if (p[c] == '/') {
			p[c] = '\0';
			if (mkdir(p, mode) == -1 && errno != EEXIST) {
				p[c] = '/';
				return false;
			}
			p[c] = '/';
		}
	}
	return true;
}

static inline bool sys_mkcdir(struct sys_path *dir, mode_t mode)
{
	sys_trunc_dir_path(dir);
	bool ok = true;
	if (mkdir(dir->path, mode) == -1 && errno != EEXIST)
		ok = false;
	sys_restor_to_file(dir);
	return ok;
}

static inline int sys_connect_sock(const char *ipc_path)
{
	int client_fd, stat_c;
	struct sockaddr_un serv_addr = {
		.sun_family = AF_UNIX
	};
	if ((client_fd = socket(AF_UNIX, SOCK_STREAM, 0)) != -1) {
		strncpy(
			serv_addr.sun_path, ipc_path, sizeof(serv_addr.sun_path) - 1
		);
		if ((stat_c = connect(client_fd, (struct sockaddr*)&serv_addr, sizeof(serv_addr))) == -1)
			client_fd = -2;
	}
	return client_fd;
}

#endif // _SYS_H
