
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
	"misc.py"
	${CMAKE_CURRENT_BINARY_DIR}/gameconqueror )

set(UI_SHARE
	${CMAKE_CURRENT_BINARY_DIR}/${XGD_DESKTOP} )

set(DISTRIB_DATADIR
	${CMAKE_INSTALL_PREFIX}/${DISTRIB_APPNAME} )

set(DISTRIB_LIBPATH
	${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/${DISTRIB_LIB} )

configure_file("GameConqueror.ui" ${UI_GTK_XML})
configure_file("gameconqueror.in" gameconqueror
	FILE_PERMISSIONS OWNER_EXECUTE OWNER_READ OWNER_WRITE
					 WORLD_EXECUTE WORLD_READ
					 GROUP_EXECUTE GROUP_READ )

configure_file("${XGD_DESKTOP}.in" ${XGD_DESKTOP}
	FILE_PERMISSIONS OWNER_EXECUTE OWNER_READ OWNER_WRITE
					 WORLD_EXECUTE WORLD_READ
					 GROUP_EXECUTE GROUP_READ )

# install gui script
install(FILES ${UI_DATA}    DESTINATION "${DISTRIB_APPNAME}/ui")
install(FILES ${PY_MODULES} DESTINATION "${DISTRIB_APPNAME}")
install(FILES ${UI_SHARE}   DESTINATION "${CMAKE_INSTALL_DATADIR}/applications")
