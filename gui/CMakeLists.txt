
set(XGD_DESKTOP
	"org.scanmem.gameconqueror.desktop" )

set(XML_METAINFO
	"org.scanmem.gameconqueror.metainfo.xml" )

set(POLICY_KIT
	"org.freedesktop.gameconqueror.policy" )

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

set(GC_policy
	${CMAKE_CURRENT_BINARY_DIR}/${POLICY_KIT} )

set(GC_desktop
	${CMAKE_CURRENT_BINARY_DIR}/${XGD_DESKTOP} )

set(GC_metainfo
	${CMAKE_CURRENT_BINARY_DIR}/${XML_METAINFO} )

set(POLICY_install_dir
	${CMAKE_INSTALL_DATADIR}/polkit-1/actions)

set(DESKTOP_install_dir 
	${CMAKE_INSTALL_DATADIR}/applications)

set(METAINFO_install_dir
	${CMAKE_INSTALL_DATADIR}/metainfo)

set(GC_install_dir
	${CMAKE_INSTALL_DATADIR}/${DISTRIB_APPNAME})

set(DISTRIB_DATADIR
	${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_DATADIR} )

set(DISTRIB_LIBPATH
	${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/${DISTRIB_LIB} )

configure_file("GameConqueror.ui" ${UI_GTK_XML})
configure_file("gameconqueror.in" ${GC_name}.sh)
configure_file("${XGD_DESKTOP}.in" ${XGD_DESKTOP})
configure_file("${XML_METAINFO}.in" ${XML_METAINFO})
configure_file("${POLICY_KIT}.in.in" ${POLICY_KIT})

if(WITH_LOCALES)
	add_custom_target(
		gc-potfiles ALL WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}

		COMMAND ${GETTEXT_MSGFMT_EXEC} --xml
			-d ${CMAKE_SOURCE_DIR}/po --template=${GC_metainfo}
			-o ${XML_METAINFO}.pot

		COMMAND ${GETTEXT_MSGFMT_EXEC} --desktop
			-d ${CMAKE_SOURCE_DIR}/po --template=${GC_desktop}
			-o ${XGD_DESKTOP}.pot

		COMMAND ${GETTEXT_MSGFMT_EXEC} --xml
			-d ${CMAKE_SOURCE_DIR}/po --template=${GC_policy}
			-o ${POLICY_KIT}.pot
	)
	set(GC_metainfo ${GC_metainfo}.pot)
	set(GC_desktop  ${GC_desktop}.pot)
	set(GC_policy   ${GC_policy}.pot)
endif()

# install gui script
install(FILES ${UI_DATA}     DESTINATION "${GC_install_dir}/ui")
install(FILES ${PY_MODULES}  DESTINATION "${GC_install_dir}")

install(FILES ${GC_policy}   DESTINATION "${POLICY_install_dir}"   RENAME ${POLICY_KIT})
install(FILES ${GC_desktop}  DESTINATION "${DESKTOP_install_dir}"  RENAME ${XGD_DESKTOP} PERMISSIONS ${PROGRAM_PERMISSIONS_DEFAULT})
install(FILES ${GC_metainfo} DESTINATION "${METAINFO_install_dir}" RENAME ${XML_METAINFO})

install(FILES ${GC_scrypt}   DESTINATION "${CMAKE_INSTALL_BINDIR}" RENAME ${GC_name} PERMISSIONS ${PROGRAM_PERMISSIONS_DEFAULT})
