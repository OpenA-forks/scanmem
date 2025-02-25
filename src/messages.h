

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

#endif // _MESSAGES_H
