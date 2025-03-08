
set(LOCALE_install_dir
	"${CMAKE_INSTALL_DATADIR}/locale" )

add_custom_target(po-locales ALL
	WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

file(STRINGS "LINGUAS"  LINGUAS_LIST)
foreach(lang IN ITEMS ${LINGUAS_LIST})
	if (lang)
		message(STATUS " Adding msgfmt for: ${lang}")
		add_custom_command(
			TARGET po-locales PRE_BUILD

			COMMENT "Create locale for: ${lang}"
			COMMAND ${GETTEXT_MSGFMT_EXEC}
				--output-file=${lang}.gmo
				"${CMAKE_CURRENT_SOURCE_DIR}/${lang}.po"
		)
		install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${lang}.gmo"
			DESTINATION "${LOCALE_install_dir}/${lang}/LC_MESSAGES/"
			RENAME "${DISTRIB_APPNAME}.mo")
	endif()
endforeach()
