
dist_appIcon_DATA = icons/GameConqueror.svg

appName_DATA = scanmem.py speedhack.py misc.py hexview.py GameConqueror.py
dist_bin_SCRIPTS = gameconqueror
dist_appGcUI_DATA = $(UI_GTK_XML) $(dist_appIcon_DATA)\
	icons/GC-logo.svg\
	icons/GC-mono.svg

dist_desktop_in_files = org.scanmem.gameconqueror.desktop.in
dist_desktop_DATA = $(dist_desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@
dist_polkit_in_files = org.freedesktop.gameconqueror.policy.in
dist_polkit_DATA = $(dist_polkit_in_files:.policy.in=.policy)
@INTLTOOL_POLICY_RULE@
dist_appdata_in_files = org.scanmem.gameconqueror.metainfo.xml.in
dist_appdata_DATA = $(dist_appdata_in_files:.xml.in=.xml)
@INTLTOOL_XML_RULE@
dist_man_MANS = gameconqueror.1
dist_doc_DATA = README TODO COPYING

appIcondir = $(datadir)/icons/hicolor/scalable/apps
appNamedir = $(datadir)/$(DISTRIB_APPNAME)
appGcUIdir = $(appNamedir)/ui

desktopdir=$(datadir)/applications
polkitdir=$(datadir)/polkit-1/actions
appdatadir=$(datadir)/metainfo

install-data-hook:
	@echo "Remember to run gtk-update-icon-cache if icons don't show up."
