SUBDIRS = icons

gameconquerordir=$(datadir)/gameconqueror
python_PYTHON = scanmem.py speedhack.py misc.py hexview.py GameConqueror.py
pythondir = $(gameconquerordir)
dist_bin_SCRIPTS = gameconqueror
dist_gameconqueror_DATA = GameConqueror.ui  icons/GC-logo.svg\
                    icons/GameConqueror.svg icons/GC-mono.svg 
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
EXTRA_DIST = gameconqueror.in

desktopdir=$(datadir)/applications
polkitdir=$(datadir)/polkit-1/actions
appdatadir=$(datadir)/metainfo
