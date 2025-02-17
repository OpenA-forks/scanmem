cmake_minimum_required(VERSION 3.20)

# Library name and version
project(scanmem
	VERSION 0.18
	LANGUAGES C
	HOMEPAGE_URL "https://github.com/scanmem/scanmem"
)
set(PROJECT_CFLAGS  -O2)
set(PROJECT_DEFS    -D_GNU_SOURCE)
set(PROJECT_WERROR  -Wall)
set(PROJECT_INCLUDE ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR})
set(PROJECT_BUILDVER "dev")
set(PROJECT_CLI_SRC  "menu.h" "menu.c" "main.c")

set(DISTRIB_APPNAME "GameConqueror")
set(DISTRIB_BIN "")
set(DISTRIB_LIB "")
set(DISTRIB_MAN "")

set(PROJECT_HEADERS
	"commands.h"
	"list.h"
	"sets.h"
	"maps.h"
	"handlers.h"
	"scanmem.h"
	"interrupt.h"
	"scanroutines.h"
	"targetmem.h"
	"licence.h"
	"value.h"
	"common.h"
	"show_message.h" )

set(PROJECT_SOURCES
	"commands.c"
	"ptrace.c"
	"handlers.c"
	"interrupt.c"
	"maps.c"
	"scanmem.c"
	"scanroutines.c"
	"sets.c"
	"targetmem.c"
	"value.c"
	"common.c"
	"show_message.c" )

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_REQUIRED_DEFINITIONS ${PROJECT_DEFS})
set(CMAKE_EXTRA_INCLUDE_FILES "signal.h")
if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
	set_property(CACHE CMAKE_INSTALL_PREFIX PROPERTY VALUE "/opt/Scanmem")
endif()

include(GNUInstallDirs)
include(CheckTypeSize)
include(CheckIncludeFile)
include(CheckSymbolExists)
include(CheckFunctionExists)

# check sys headers
check_include_file("sys/stat.h"   HAVE_SYS_STAT_H)
check_include_file("sys/time.h"   HAVE_SYS_TIME_H)
check_include_file("sys/types.h"  HAVE_SYS_TYPES_H)
check_include_file("sys/ioctl.h"  HAVE_SYS_IOCTL_H)
check_include_file("sys/socket.h" HAVE_SYS_SOCK_H)
# check libc headers
check_include_file("fcntl.h"    HAVE_FCNTL_H)
check_include_file("signal.h"   HAVE_SIGNAL_H)
check_include_file("alloca.h"   HAVE_ALLOCA_H)
check_include_file("limits.h"   HAVE_LIMITS_H)
check_include_file("pthread.h"  HAVE_PTHREAD_H)
check_include_file("inttypes.h" HAVE_INTTYPES_H)
# check types size
check_type_size("int64_t"      SIZE_INT64_T)
check_type_size("intptr_t"     SIZE_INTPTR_T)
check_type_size("ssize_t"      SIZE_SSIZE_T)
check_type_size("pid_t"        SIZE_PID_T)
check_type_size("sighandler_t" SIZE_SIGHANDLER_T)
# check constants
check_symbol_exists("strdupa"  "string.h" HAVE_STRDUPA)
check_symbol_exists("strndupa" "string.h" HAVE_STRNDUPA)
# check functions
check_function_exists("strtod"   HAVE_STRTOD)
check_function_exists("getline"  HAVE_GETLINE)

if (NOT HAVE_GETLINE)
	# Using the fgetln()-based getline() replacement.
	check_function_exists("fgetln" HAVE_FGETLN)
	if (NOT HAVE_FGETLN)
		message(FATAL_ERROR "Cannot build without working getline() or fgetln().")
	endif()
endif()

find_package(Git QUIET)
if(GIT_FOUND)
	execute_process(
		#COMMAND git rev-parse --short HEAD
		COMMAND git config --get remote.origin.url
		OUTPUT_VARIABLE REPO_URL
		OUTPUT_STRIP_TRAILING_WHITESPACE
		ERROR_QUIET
	)
	set(PROJECT_HOMEPAGE_URL ${REPO_URL})
endif()

#
# Optional: -DBUILD_CFLAGS="-O2"
#
option(BUILD_CFLAGS "Set compiler flags manually" OFF)
if (BUILD_CFLAGS)
	set(PROJECT_CFLAGS ${BUILD_CFLAGS})
endif()

#
# Optional: -DUSE_PROCMEM=1
#
option(USE_PROCMEM "Force using /proc/{pid}/mem support" ON)
if (USE_PROCMEM)
	list(APPEND PROJECT_DEFS -DUSE_PROCMEM)
	set(HAVE_PROCMEM ON CACHE FILEPATH "Enable /proc/{pid}/mem support")
else()
	unset(HAVE_PROCMEM CACHE)
endif()

#
# Optional: -DUSE_IREADLINE=1
#
option(USE_IREADLINE "Force using internal readline" OFF)
if(USE_IREADLINE)
	list(APPEND PROJECT_CLI_SRC "readline.h" "readline.c")
endif()

option(BUILD_RELEASE "Build without debug logs and turn warnings to errors" OFF)
if(BUILD_RELEASE)
	# lots of warnings and all warnings as errors
	set(PROJECT_WERROR -Werror)
	set(PROJECT_BUILDVER "rel")
endif()

#
# Optional: -DBUILD_SHARED=1
#
option(BUILD_SHARED "Build scanmem as shared library" OFF)
if(NOT BUILD_SHARED)
	add_library(scanmem STATIC ${PROJECT_SOURCES} ${PROJECT_HEADERS})
	list(APPEND DISTRIB_LIB "libscanmem.a")
else()
	add_library(scanmem SHARED ${PROJECT_SOURCES} ${PROJECT_HEADERS})
	list(APPEND DISTRIB_LIB "libscanmem.so")
endif()

#
# Optional: -DWITH_GUI=1
#
option(WITH_GUI "Enable GameConquerror UI module" OFF)
if (WITH_GUI)
	#add_subdirectory(po)
	add_subdirectory(gui)
	list(APPEND DISTRIB_BIN "gameconqueror")
	list(APPEND DISTRIB_MAN "gui/gameconqueror.1")
endif()

#
# Optional: -DBUILD_CLI=1
#
option(BUILD_CLI "Build scanmem command line tool" ON)
if(BUILD_CLI)
	add_executable(scanmem-cli ${PROJECT_CLI_SRC})

	if(NOT USE_IREADLINE)
		# Check for readline or bypass checking for the libraries.
		check_include_file("readline/readline.h" HAVE_RL_READLINE_H)
		check_include_file("readline/history.h" HAVE_RL_HISTORY_H)
		if(HAVE_RL_READLINE_H AND HAVE_RL_HISTORY_H)
			target_link_libraries(scanmem-cli PRIVATE readline)
			set(HAVE_LIBREADLINE ON CACHE FILEPATH "Build with libreadline")
		else()
			message(FATAL_ERROR
				"libreadline could not be found, which is required to continue."
				"The libreadline-dev package may be required.")
		endif()
	endif()
	list(APPEND DISTRIB_BIN "scanmem")
	list(APPEND DISTRIB_MAN "scanmem.1")
endif()

configure_file(config.h.in config.h)

message("\nConfigurations:\n\
\n\
.: Install prefix     = ${CMAKE_INSTALL_PREFIX}\n\
:. Compiler flags     = ${PROJECT_CFLAGS}\n\
.: Build program libs = ${DISTRIB_LIB};${DISTRIB_BIN}\n\
:. Build warning opts = ${PROJECT_WERROR}\n\
.: Build defines list = ${PROJECT_DEFS}\n\
")

target_include_directories(scanmem SYSTEM AFTER PUBLIC ${PROJECT_INCLUDE})
target_compile_options    (scanmem PRIVATE ${PROJECT_CFLAGS} ${PROJECT_WERROR})
target_compile_definitions(scanmem PRIVATE ${PROJECT_DEFS})

if(BUILD_CLI)
	set_target_properties (scanmem-cli PROPERTIES OUTPUT_NAME scanmem)
	target_compile_options(scanmem-cli PRIVATE ${PROJECT_CFLAGS} ${PROJECT_WERROR})
	target_link_libraries (scanmem-cli PRIVATE scanmem)
	# install program
	install(TARGETS scanmem-cli DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
# install library
install(TARGETS scanmem DESTINATION ${CMAKE_INSTALL_LIBDIR})
# install data files
if(DISTRIB_MAN)
	install(FILES ${DISTRIB_MAN} DESTINATION ${CMAKE_INSTALL_DATADIR}/man/man1)
endif()
