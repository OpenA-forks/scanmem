
set(XGD_DESKTOP
	"org.scanmem.gameconqueror.desktop" )

set(UI_GTK_XML
	"gtk.interface.gameconqueror.xml" )

set(UI_DATA
	"icons/GameConqueror.svg"
	"icons/GC-logo.svg"
	"icons/GC-mono.svg"
	${CMAKE_CURRENT_BINARY_DIR}/${UI_GTK_XML} )

set(PY_MODULES
	"GameConqueror.py"
	"speedhack.py"
	"scanmem.py"
	"hexview.py"
	"misc.py" )

set(GC_name "gameconqueror" )

set(GC_scrypt
	${CMAKE_CURRENT_BINARY_DIR}/${GC_name}.sh )

set(GC_symlink
	${CMAKE_CURRENT_BINARY_DIR}/${GC_name}+syml )

set(MENU_ITEMS
	${CMAKE_CURRENT_BINARY_DIR}/${XGD_DESKTOP} )

set(DISTRIB_MENUDIR
	${CMAKE_INSTALL_DATADIR}/applications)

set(DISTRIB_APPDIR
	${CMAKE_INSTALL_DATADIR}/${DISTRIB_APPNAME})

set(DISTRIB_DATADIR
	${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_DATADIR}/${DISTRIB_APPNAME} )

set(DISTRIB_LIBPATH
	${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/${DISTRIB_LIB} )

configure_file("GameConqueror.ui" ${UI_GTK_XML})
configure_file("gameconqueror.in" ${GC_name}.sh)
configure_file("${XGD_DESKTOP}.in" ${XGD_DESKTOP})

add_custom_target(gc+symlink ALL COMMAND
	${CMAKE_COMMAND} -E create_symlink ${DISTRIB_DATADIR}/${GC_name}.sh ${GC_name}+syml )

# install gui script
install(FILES ${UI_DATA}    DESTINATION "${DISTRIB_APPDIR}/ui")
install(FILES ${PY_MODULES} DESTINATION "${DISTRIB_APPDIR}")
install(FILES ${MENU_ITEMS} DESTINATION "${DISTRIB_MENUDIR}" PERMISSIONS ${PROGRAM_PERMISSIONS_DEFAULT})
install(FILES ${GC_scrypt}  DESTINATION "${DISTRIB_APPDIR}"  PERMISSIONS ${PROGRAM_PERMISSIONS_DEFAULT})
install(FILES ${GC_symlink} DESTINATION "${CMAKE_INSTALL_BINDIR}" RENAME ${GC_name})
