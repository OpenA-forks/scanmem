AC_INIT([scanmem],[0.18~dev],[https://github.com/scanmem/scanmem])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE([-Wall foreign])
AC_CONFIG_SRCDIR([main.c])
AC_CONFIG_HEADERS([config.h])
AC_USE_SYSTEM_EXTENSIONS
AC_HEADER_STDBOOL

PACKAGE_VERSION_SHORT="${PACKAGE_VERSION%~*}"
PACKAGE_VERSION_MAJOR="${PACKAGE_VERSION%.*}"

pkg_b=$(expr length "${PACKAGE_VERSION_SHORT}~ ")
pkg_m=$(expr length "${PACKAGE_VERSION_MAJOR}. ")

PACKAGE_VERSION_MINOR=`expr substr "$PACKAGE_VERSION_SHORT" $pkg_m 8`
PACKAGE_VERSION_BUILD=`expr substr "$PACKAGE_VERSION"       $pkg_b 8`

AM_PROG_AR #fix the linker warnings
LT_INIT

IT_PROG_INTLTOOL
AM_PROG_CC_C_O

AC_CHECK_FUNCS(getline secure_getenv)

if test "x$ac_cv_func_getline" = "xno"; then
  AC_CHECK_FUNCS(fgetln)
  if test "x$ac_cv_func_fgetln" = "xno"; then
    AC_MSG_ERROR([Cannot build without working getline().])
  else
    AC_MSG_NOTICE([Using the fgetln()-based getline() replacement.])
  fi
fi
AM_CONDITIONAL([HAVE_GETLINE], [test "x$ac_cv_func_getline" != "xno"])

AC_CHECK_HEADERS(fcntl.h limits.h stddef.h sys/ioctl.h sys/time.h)

AC_FUNC_ALLOCA
AC_FUNC_STRTOD

AC_TYPE_INT8_T
AC_TYPE_INT16_T
AC_TYPE_INT32_T
AC_TYPE_INT64_T
AC_TYPE_UINT8_T
AC_TYPE_UINT16_T
AC_TYPE_UINT32_T
AC_TYPE_UINT64_T
AC_TYPE_OFF_T
AC_TYPE_PID_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T

AC_C_BIGENDIAN

# Detect the host OS
android="no"
AC_CANONICAL_HOST
case "$host_os" in
  *android*)
    android="yes"
    AC_MSG_NOTICE([Android detected])
    ;;
  linux*)
    AC_MSG_NOTICE([Linux detected])
    ;;
  *)
    AC_MSG_NOTICE([Your platform is not currently supported])
    ;;
esac

# Allows disabling procmem support
AC_ARG_ENABLE(procmem, [AS_HELP_STRING([--disable-procmem],
                         [forcefully disable proc/pid/mem support])])
AS_IF([test "x$enable_procmem" = "xno"], [
  AC_DEFINE(HAVE_PROCMEM, [0], [Enable /proc/pid/mem support])
])

AS_IF([test "x$android" = "xno"], [
  AS_IF([test "x$enable_procmem" != "xno"], [
    # also need to check if the file is zero'ed (some hardened systems)
    AC_CHECK_FILE([/proc/self/maps], [], [
      echo "This system does not seem to have /proc/pid/maps files."
      exit 1
    ])

    # also need to check this file works
    AC_CHECK_FILE([/proc/self/mem], [
      # LARGEFILE support required for this to work
      AC_SYS_LARGEFILE
      AC_DEFINE(HAVE_PROCMEM, [1], [Enable /proc/pid/mem support])
    ],[
      # This will hurt performance.
      echo "This system does not seem to have /proc/pid/mem files."
      echo "Falling back to ptrace() only support."
      AC_DEFINE(HAVE_PROCMEM, [0], [Enable /proc/pid/mem support])
    ])
  ])
    # malloc optimizations without Android
    AC_FUNC_MALLOC
    AC_FUNC_REALLOC
], [
  # supported on Android
  AC_SYS_LARGEFILE
  # /proc/pid/mem is there but reading interesting data fails
  AC_DEFINE(HAVE_PROCMEM, [0], [Enable /proc/pid/mem support])
])


# Check for termcap and readline or bypass checking for the libraries.
AC_ARG_WITH([readline], [AS_HELP_STRING([--without-readline],
                            [build without readline])])
AM_CONDITIONAL([WITH_READLINE], [test "x$with_readline" != "xno"])
AS_IF([test "x$with_readline" != "xno"], [
  # termcap is sometimes required by readline
  AC_CHECK_LIB([termcap], [tgetent], [], [])
  AC_CHECK_LIB([readline], [readline], [], [
    echo "libreadline could not be found, which is required to continue."
    echo "The libreadline-dev package may be required."
    exit 1
  ])
])

GETTEXT_PACKAGE=GameConqueror
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], ["$GETTEXT_PACKAGE"],
                   [The domain to use with gettext])

AC_CONFIG_FILES([
  Makefile
  test/Makefile
  po/Makefile.in
])


# copied from ubuntu-tweak

dnl AS_AC_EXPAND(VAR, CONFIGURE_VAR)
dnl
dnl example
dnl AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
dnl will set SYSCONFDIR to /usr/local/etc if prefix=/usr/local

AC_DEFUN([AS_AC_EXPAND],
[
  EXP_VAR=[$1]
  FROM_VAR=[$2]

  dnl first expand prefix and exec_prefix if necessary
  prefix_save=$prefix
  exec_prefix_save=$exec_prefix

  dnl if no prefix given, then use /usr/local, the default prefix
  if test "x$prefix" = "xNONE"; then
    prefix=$ac_default_prefix
  fi
  dnl if no exec_prefix given, then use prefix
  if test "x$exec_prefix" = "xNONE"; then
    exec_prefix=$prefix
  fi

  full_var="$FROM_VAR"
  dnl loop until it doesn\'t change anymore
  while true; do
    new_full_var="`eval echo $full_var`"
    if test "x$new_full_var" = "x$full_var"; then break; fi
    full_var=$new_full_var
  done

  dnl clean up
  full_var=$new_full_var
  AC_SUBST([$1], "$full_var")

  dnl restore prefix and exec_prefix
  prefix=$prefix_save
  exec_prefix=$exec_prefix_save
])
# end copy


# GameConqueror configuration

AC_ARG_ENABLE(gui, [AS_HELP_STRING([--enable-gui],
                            ["enable $GETTEXT_PACKAGE, the gui front-end of scanmem"])])
AM_CONDITIONAL([ENABLE_GUI], [test "x$enable_gui" = "xyes"])
AS_IF([test "x$enable_gui" = "xyes"], [
  AS_AC_EXPAND(DISTRIB_DATADIR, "$datadir")
  AS_AC_EXPAND(DISTRIB_APPNAME, "$GETTEXT_PACKAGE")
  AS_AC_EXPAND(DISTRIB_LIBPATH, "$libdir/libscanmem.so")

  AS_AC_EXPAND(PROJECT_HOMEPAGE_URL,  "$PACKAGE_BUGREPORT")
  AS_AC_EXPAND(PROJECT_VERSION,       "$PACKAGE_VERSION_SHORT")
  AS_AC_EXPAND(PROJECT_VERSION_MAJOR, "$PACKAGE_VERSION_MAJOR")
  AS_AC_EXPAND(PROJECT_VERSION_MINOR, "$PACKAGE_VERSION_MINOR")
  AS_AC_EXPAND(PROJECT_BUILDVER,      "$PACKAGE_VERSION_BUILD")

  AS_AC_EXPAND(UI_GTK_XML,   "gtk.interface.gameconqueror.xml")
  AS_AC_EXPAND(XGD_DESKTOP,  "org.scanmem.gameconqueror.desktop")
  AS_AC_EXPAND(XML_METAINFO, "org.scanmem.gameconqueror.metainfo.xml")
  AS_AC_EXPAND(POLICY_KIT,   "org.freedesktop.gameconqueror.policy")

  AM_PATH_PYTHON([3.7])
  AC_CONFIG_FILES([
    gui/Makefile
    gui/${UI_GTK_XML}:gui/GameConqueror.ui
    gui/gameconqueror
    gui/${XML_METAINFO}.in:gui/${XML_METAINFO}.in
    gui/${XGD_DESKTOP}.in:gui/${XGD_DESKTOP}.in
    gui/${POLICY_KIT}.in:gui/${POLICY_KIT}.in.in
  ])
])

AC_OUTPUT
