

#ifndef _MESSAGES_H
# define _MESSAGES_H
# include <stdio.h>

#ifdef HAVE_INTLTOOL_H
# include <libintl.h>
# define lStr(_X) dgettext("scanmem", _X)
# define SM_Error(_M)  printf("✖︎ %s: %s.\n\n", lStr("ERROR"), lStr(_M))
# define SM_Warn(_M,_D) printf("⚠︎ %s: %s.\n\t(%s).\n\n", lStr("WARN"), lStr(_M), lStr(_D))
#else
# define lStr(_X) _X
# define SM_Error(_M)  puts("✖︎ ERROR: " _M ".\n")
# define SM_Warn(_M,_D) puts("⚠︎ WARN: " _M ".\n\t(" _D ").\n")
#endif
# define SM_Hint(_M,_N) printf("💡 %s.\n"_N, lStr(_M))
# define SM_Info(_F,...) printf(" ✔︎ " _F ".\n", __VA_ARGS__)
# define SM_Message(_F,...) fprintf(stderr, _F, __VA_ARGS__)

#ifdef DEBUG
# define SM_Demsg(_M)     puts  ("🐞 ~ " _M)
# define SM_Debug(_F,...) printf("🐞 ~ " _F "\n", __VA_ARGS__)
#else
# define SM_Demsg(_M)
# define SM_Debug(...)
#endif

# define F_TEXT_MSG(_A,_F)     _A  ": "  _F ".\n"
# define F_JSON_NUM(_A,_F) "\""_A"\":"   _F 
# define F_JSON_STR(_A,_F) "\""_A"\":\"" _F "\""

void sm_message(const char *fmt, ...);

#endif // _MESSAGES_H
