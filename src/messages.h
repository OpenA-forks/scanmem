

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

# define L_MIN(_A,_B) (_A)>=(_B)?(_B):(_A)
# define L_MAX(_A,_B) (_A)>=(_B)?(_A):(_B)

# define _4_FMT(_F,_i,_S) _F[_i+0]=(_S)[0],_F[_i+1]=(_S)[1],_F[_i+2]=(_S)[2],_F[_i+3]=(_S)[3]
# define _6_FMT(_F,_i,_S) _4_FMT(_F,_i,_S),_F[_i+4]=(_S)[4],_F[_i+5]=(_S)[5]
# define _8_FMT(_F,_i,_S) _6_FMT(_F,_i,_S),_F[_i+6]=(_S)[6],_F[_i+7]=(_S)[7]

# define _CMP_4(_B,_i,_S) (_B[_i+0]==(_S)[0]&&_B[_i+1]==(_S)[1]&&_B[_i+2]==(_S)[2]&&_B[_i+3]==(_S)[3])
# define _CMP_5(_B,_i,_S) (_CMP_4(_B,_i,_S) &&_B[_i+4]==(_S)[4])
# define _CMP_6(_B,_i,_S) (_CMP_5(_B,_i,_S) &&_B[_i+5]==(_S)[5])
# define _CMP_7(_B,_i,_S) (_CMP_6(_B,_i,_S) &&_B[_i+6]==(_S)[6])
# define _CMP_8(_B,_i,_S) (_CMP_7(_B,_i,_S) &&_B[_i+7]==(_S)[7])

void sm_message(const char *fmt, ...);

#endif // _MESSAGES_H
