"""
    Game Conqueror: a graphical game cheating tool, using scanmem as its backend
    
    Copyright (C) 2009-2011,2013 Wang Lu <coolwanglu(a)gmail.com>
    Copyright (C) 2010 Bryan Cain
    Copyright (C) 2013 Mattias Muenster <mattiasmun(a)gmail.com>
    Copyright (C) 2014-2018 Sebastian Parschauer <s.parschauer(a)gmx.de>
    Copyright (C) 2016-2017 Andrea Stacchiotti <andreastacchiotti(a)gmail.com>
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, sys, socket, misc, locale, gettext, threading, json, gi
# check toolkit version
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, Pango

SOCK_PATH   = os.environ['SCANMEM_SOCKET']
GETTEXT_PKG = os.environ['SCANMEM_GETTEXT']
LOCALE_DIR  = os.environ['SCANMEM_LOCALEDIR']
UI_GTK_PATH = os.environ['SCANMEM_UIGTK']
VERSION     = os.environ['SCANMEM_VERSION']
IS_DEBUG    = os.environ['SCANMEM_DEBUG']
HOMEPAGE    = os.environ['SCANMEM_HOMEPAGE']

from hexview import HexView

# In some locale, ',' is used in float numbers
locale.setlocale(locale.LC_NUMERIC, 'C')
locale.bindtextdomain(GETTEXT_PKG, LOCALE_DIR)
gettext.install(GETTEXT_PKG, LOCALE_DIR, names=('_'))

PROGRESS_INTERVAL = 100 # for scan progress updates
DATA_WORKER_INTERVAL = 500 # for read(update)/write(lock)
HEXEDIT_SPAN = 1024 # hexview half-height
SCAN_RESULT_LIST_LIMIT = 10000 # maximal number of entries that can be displayed

class UIBuilder(Gtk.Builder):

    def __init__(self):
        super(UIBuilder, self).__init__()

        self.set_translation_domain(GETTEXT_PKG)
        self.add_from_file(UI_GTK_PATH)

        self.    main_window = self.get_object('MainWindow')
        self.procList_dialog = self.get_object('ProcessListDialog')
        self.addCheat_dialog = self.get_object('AddCheatDialog')
        self.   about_dialog = self.get_object('AboutDialog')
        self. process_label  = self.get_object('Process_Label')
        self.   value_input  = self.get_object('Value_Input')
        self.    scan_button = self.get_object('Scan_Button')
        self.    stop_button = self.get_object('Stop_Button')
        self.   reset_button = self.get_object('Reset_Button')
        self.   scan_options = self.get_object('ScanOption_Frame')
        self.   scan_progbar = self.get_object('ScanProgress_ProgressBar')

        # set version
        self.about_dialog.set_version(VERSION)
        self.about_dialog.set_website(HOMEPAGE)


    ############################
    # core functions
    def show_error(self, msg: str):
        dialog = Gtk.MessageDialog(modal = True, text = msg,
                                   message_type  = Gtk.MessageType.ERROR,
                                   transient_for = self.main_window)

        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.run()
        dialog.destroy()

    def open_file_dialog(self, title:str, on_file_open, for_save=False):
        gtk_stock_name =     Gtk.STOCK_OPEN if not for_save else Gtk.STOCK_SAVE
        action = Gtk.FileChooserAction.OPEN if not for_save else Gtk.FileChooserAction.SAVE
        dialog = Gtk.FileChooserDialog(title=f'{title} ...', action=action,
                                       transient_for=self.main_window)

        dialog.add_button(gtk_stock_name  , Gtk.ResponseType.OK)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            try:
                with open(dialog.get_filename(), 'r' if not for_save else 'w') as f:
                    on_file_open(f)
            except:
                pass
        dialog.destroy()

    @staticmethod
    # append a column to `treeview`, with given `title`
    # the latter two should be a list of tuples, i.e. [(key1, val1), (key2, val2), ..]
    def treeview_append_column(treeview, title: str,
                               sort_id   = -1,
                               resizable = True,
                               hex_col   = False,
                               rend_class: type=Gtk.CellRendererText,
                               attributes: list=None,
                               properties: list=None,
                               signals   : list=None):
        # create renderer of given type
        render = rend_class()
        column = Gtk.TreeViewColumn(title)
        column.set_resizable(resizable)
        column.pack_start(render, True)
        treeview.append_column(column)
        if sort_id != -1:
            column.set_sort_column_id(sort_id)
        if hex_col:
            column.set_cell_data_func(render, UIBuilder.format16, sort_id)
        if attributes:
            for k,v in attributes:
                column.add_attribute(render, k,v)
        if properties:
            for k,v in properties:
                render.set_property(k,v)
        if signals:
            for k,v in signals:
                render.connect(k,v)

    @staticmethod
    # convert [a,b,c] into a liststore that [[a],[b],[c]], where a,b,c are strings
    def new_simple_str_liststore(keys: list[str]):
        stor = Gtk.ListStore(str)
        for key in keys:
            stor.append([key])
        return stor

    @staticmethod
    # data is optional data to callback
    def new_popup_menu(itemprops: list[ tuple[str] ]):
        menu = Gtk.Menu()
        for name,call,data in itemprops:
            item = Gtk.MenuItem(label=name)
            menu.append(item)
            item.connect('activate', call, data)
        menu.show_all()
        return menu

    @staticmethod
    # set active item of the `combobox` such that the value at `col` is `name`
    def combobox_set_active_item(combobox, name, col=0):
        model = combobox.get_model()
        iter = model.get_iter_first()
        while model.get_value(iter, col) != name:
            iter = model.iter_next(iter)
        if iter is None:
            raise ValueError(f'Cannot locate item: {name}')
        combobox.set_active_iter(iter)

    @staticmethod
    # format number in base16 (callback for TreeView)
    def format16(col, cell, model, iter, cid: int):
        xv = model.get_value(iter, cid)
        cell.set_property('text', '%x' % xv)

    @staticmethod
    # sort column according to datatype (callback for TreeView)
    def treeview_sort_cmp(treemodel, iter1, iter2, user_data):
        sort_col, isnumeric = user_data

        v1 = treemodel.get_value(iter1, sort_col)
        v2 = treemodel.get_value(iter2, sort_col)

        if (isnumeric):
            v1 = float(v1)
            v2 = float(v2)

        if v1 >  v2: return 1
        if v1 == v2: return 0
        return -1


class GameConqueror():
    def __init__(self, connect: socket.socket):

        self.lock_data_type = 'int32'
        self.scan_data_type = 'int32'
        self.search_scope   = 1 # normal
        self.clipboard      = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        ##################################
        # init GUI
        gcui = UIBuilder()

        # init memory editor
        self.memoryeditor_window = gcui.get_object('MemoryEditor_Window')
        self.memoryeditor_hexview = HexView()
        self.memoryeditor_window.get_child().pack_start(self.memoryeditor_hexview, True, True, 0)
        self.memoryeditor_hexview.show_all()
        self.memoryeditor_address_entry = gcui.get_object('MemoryEditor_Address_Entry')
        self.memoryeditor_hexview.connect('char-changed', self.memoryeditor_hexview_char_changed_cb)

        ###
        # Set scan data type
        self.scan_data_type_combobox = gcui.get_object('ScanDataType_ComboBoxText')
        for entry in misc.SCAN_VALUE_TYPES:
            self.scan_data_type_combobox.append_text(entry)
        # apply setting
        UIBuilder.combobox_set_active_item(self.scan_data_type_combobox, self.scan_data_type)

        ###
        # set search scope
        self.search_scope_scale = gcui.get_object('SearchScope_Scale')
        # apply setting
        self.search_scope_scale.set_value(self.search_scope)

        # init scanresult treeview
        # we may need a cell data func here
        # create model
        self.scanresult_tv = gcui.get_object('ScanResult_TreeView')
        # liststore contents:                     addr,                value, type, valid, offset,              region type, match_id
        self.scanresult_liststore = Gtk.ListStore(GObject.TYPE_UINT64, str,   str,  bool,  GObject.TYPE_UINT64, str,         int)
        self.scanresult_tv.set_model(self.scanresult_liststore)
        # init columns
        UIBuilder.treeview_append_column(self.scanresult_tv, 'Address', 0, hex_col=True,
                                    attributes=[('text', 0)],
                                    properties=[('family', 'monospace')])

        UIBuilder.treeview_append_column(self.scanresult_tv, 'Value', 1,
                                    attributes=[('text', 0)],
                                    properties=[('family', 'monospace')])

        UIBuilder.treeview_append_column(self.scanresult_tv, 'Offset', 4, hex_col=True,
                                    attributes=[('text', 4)],
                                    properties=[('family', 'monospace')])

        UIBuilder.treeview_append_column(self.scanresult_tv, 'Region Type', 5,
                                    attributes=[('text', 5)],
                                    properties=[('family', 'monospace')])
        # init CheatList TreeView
        self.cheatlist_tv = gcui.get_object('CheatList_TreeView')
        # cheatlist contents:                    locked, description, addr,                type, value, valid
        self.cheatlist_liststore = Gtk.ListStore(bool,   str,         GObject.TYPE_UINT64, str,  str,   bool)
        self.cheatlist_tv.set_model(self.cheatlist_liststore)
        self.cheatlist_editing = False
        # Lock
        UIBuilder.treeview_append_column(self.cheatlist_tv, 'Lock', 0,
                                    rend_class = Gtk.CellRendererToggle,
                                    attributes = [('active',0)],
                                    properties = [('activatable' , True ),
                                                  ('radio'       , False),
                                                  ('inconsistent', False)],
                                    signals    = [('toggled', self.cheatlist_toggle_lock_cb)])
        # Description
        UIBuilder.treeview_append_column(self.cheatlist_tv, 'Description', 1,
                                    attributes = [('text',1)],
                                    properties = [('editable', True)],
                                    signals    = [('edited'          , self.cheatlist_edit_description_cb),
                                                  ('editing-started' , self.cheatlist_edit_start),
                                                  ('editing-canceled', self.cheatlist_edit_cancel)])
        # Address
        UIBuilder.treeview_append_column(self.cheatlist_tv, 'Address', 2, hex_col=True,
                                    attributes = [('text',2)],
                                    properties = [('family', 'monospace')])
        # Type
        UIBuilder.treeview_append_column(self.cheatlist_tv, 'Type', 3, rend_class = Gtk.CellRendererCombo,
                                    attributes = [('text',3)],
                                    properties = [('editable'   , True ),
                                                  ('has-entry'  , False),
                                                  ('model'      , UIBuilder.new_simple_str_liststore(misc.MEMORY_TYPES)),
                                                  ('text-column', 0)],
                                    signals    = [('edited'           , self.cheatlist_edit_type_cb),
                                                  ('editing-started'  , self.cheatlist_edit_start),
                                                  ('editing-canceled' , self.cheatlist_edit_cancel)])
        # Value 
        UIBuilder.treeview_append_column(self.cheatlist_tv, 'Value', 4,
                                    attributes = [('text',4)],
                                    properties = [('editable', True),
                                                  ('family', 'monospace')],
                                    signals    = [('edited'          , self.cheatlist_edit_value_cb),
                                                  ('editing-started' , self.cheatlist_edit_start),
                                                  ('editing-canceled', self.cheatlist_edit_cancel)])
        # init ProcessList
        self.processfilter_input = gcui.get_object('ProcessFilter_Input')
        self.userfilter_input = gcui.get_object('UserFilter_Input')
        # init ProcessList_TreeView
        self.processlist_tv = gcui.get_object('ProcessList_TreeView')
        self.processlist_liststore = Gtk.ListStore(int, str, str)
        self.processlist_filter = self.processlist_liststore.filter_new(root=None)
        self.processlist_filter.set_visible_func(self.processlist_filter_func, data=None)
        self.processlist_tv.set_model(Gtk.TreeModelSort(model=self.processlist_filter))
        self.processlist_tv.set_search_column(2)
        # make processes tree
        UIBuilder.treeview_append_column(self.processlist_tv, 'PID'    , 0, attributes=[('text',0)]) # first col
        UIBuilder.treeview_append_column(self.processlist_tv, 'User'   , 1, attributes=[('text',1)]) # second col
        UIBuilder.treeview_append_column(self.processlist_tv, 'Process', 2, attributes=[('text',2)]) # third col
        # get list of things to be disabled during scan
        self.disablelist = [gcui.reset_button, self.cheatlist_tv , gcui.get_object('processGrid'),
                            gcui.value_input , self.scanresult_tv, gcui.get_object('buttonGrid'),
                            self.memoryeditor_window]
        # init AddCheatDialog
        self.addcheat_address_input = gcui.get_object('Address_Input')
        self.addcheat_address_input.override_font(Pango.FontDescription("Monospace"))

        self.addcheat_description_input = gcui.get_object('Description_Input')
        self.addcheat_length_spinbutton = gcui.get_object('Length_SpinButton')

        self.addcheat_type_combobox = gcui.get_object('Type_ComboBoxText')
        for entry in misc.MEMORY_TYPES:
            self.addcheat_type_combobox.append_text(entry)
        UIBuilder.combobox_set_active_item(self.addcheat_type_combobox, self.lock_data_type)
        self.Type_ComboBoxText_changed_cb(self.addcheat_type_combobox)

        # init popup menu for scanresult
        self.scanresult_popup = UIBuilder.new_popup_menu([
            ('Add to cheat list'    , self.scanresult_popup_cb, 'add_to_cheat_list'),
            ('Browse this address'  , self.scanresult_popup_cb, 'browse_this_address'),
            ('Scan for this address', self.scanresult_popup_cb, 'scan_for_this_address'),
            ('Remove this match'    , self.scanresult_delete_selected_matches, '')
        ])
        # init popup menu for cheatlist
        self.cheatlist_popup = UIBuilder.new_popup_menu([
            ('Browse this address', self.cheatlist_popup_cb, 'browse_this_address'),
            ('Copy address'       , self.cheatlist_popup_cb, 'copy_address'),
            ('Remove this entry'  , self.cheatlist_popup_cb, 'remove_entry')
        ])
        gcui.connect_signals(self)
        gcui.main_window.connect('destroy', self.exit)

        ###########################
        # init others (backend, flag...)
        self._maps: list = None
        self._cnt = 0 # found count
        self._pid = 0 # target pid
        self._bg = connect
        self._ui = gcui

        self.is_scanning = False
        self.exiting_flag = False # currently for data_worker only, other 'threads' may also use this flag
        self.is_first_scan = True

        self._watch_id = GLib.timeout_add(DATA_WORKER_INTERVAL, self.data_worker)
        self.command_lock = threading.RLock()


    ###########################
    # GUI callbacks

    # Memory editor

    def MemoryEditor_Button_clicked_cb(self, button, data=None):
        if self._pid == 0:
            self._ui.show_error('Please select a process')
            return
        self.browse_memory()
        return True

    def MemoryEditor_Handle_Address_cb(self, widget, data=None):
        txt = self.memoryeditor_address_entry.get_text().strip()
        if txt == '':
            return
        try:
            addr = int(txt, 16)
            self.browse_memory(addr)
        except:
            self._ui.show_error('Invalid address')

    # Manually add cheat

    def ConfirmAddCheat_Button_clicked_cb(self, button, data=None):
        addr = self.addcheat_address_input.get_text()
        try:
            addr = int(addr, 16)
            addr = GObject.Value(GObject.TYPE_UINT64, addr)
        except (ValueError, OverflowError):
            self._ui.show_error('Please enter a valid address.')
            return False

        descript = self.addcheat_description_input.get_text() or 'No Description'
        typestr = self.addcheat_type_combobox.get_active_text()
        length = self.addcheat_length_spinbutton.get_value_as_int()
        if 'int' in typestr: value = 0
        elif 'float' in typestr: value = 0.0
        elif typestr == 'string': value = ' ' * length
        elif typestr == 'bytearray': value = '00 ' * length
        else: value = None

        self.add_to_cheat_list(addr, value, typestr, descript)
        self._ui.addCheat_dialog.hide()
        return True

    def CloseAddCheat_Button_clicked_cb(self, button, data=None):
        self._ui.addCheat_dialog.hide()
        return True

    # Main window

    def ManuallyAddCheat_Button_clicked_cb(self, button, data=None):
        self._ui.addCheat_dialog.show()
        return True

    def RemoveAllCheat_Button_clicked_cb(self, button, data=None):
        self.cheatlist_liststore.clear()
        return True

    def LoadCheat_Button_clicked_cb(self, button, data=None):
        self._ui.open_file_dialog('Select CheatList', self.read_cheat_list, False)
        return True

    def SaveCheat_Button_clicked_cb(self, button, data=None):
        self._ui.open_file_dialog('Save CheatList As', self.write_cheat_list, True)
        return True

    def SearchScope_Scale_format_value_cb(self, scale, value, data=None):
        return misc.SEARCH_SCOPE_NAMES[int(value)]

    def Value_Input_activate_cb(self, entry, data=None):
        self.do_scan()
        return True

    def ScanResult_TreeView_popup_menu_cb(self, widget, data=None):
        pathlist = self.scanresult_tv.get_selection().get_selected_rows()[1]
        if len(pathlist):
            self.scanresult_popup.popup(None, None, None, None, 0, 0)
            return True
        return False

    def ScanResult_TreeView_button_press_event_cb(self, widget, event, data=None):
        # add to cheat list
        (model, pathlist) = self.scanresult_tv.get_selection().get_selected_rows()
        if event.button == 1 and event.get_click_count()[1] > 1: # left double click
            for path in pathlist:
                (addr, value, typestr) = model.get(model.get_iter(path), 0, 1, 2)
                self.add_to_cheat_list(addr, value, typestr)
        elif event.button == 3: # right click
            path = self.scanresult_tv.get_path_at_pos(int(event.x),int(event.y))
            if path is not None:
                self.scanresult_popup.popup(None, None, None, None, event.button, event.get_time())
                return path[0] in pathlist
        return False

    def CheatList_TreeView_button_press_event_cb(self, widget, event, data=None):
        if event.button == 3: # right click
            pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
            path = self.cheatlist_tv.get_path_at_pos(int(event.x),int(event.y))
            if path is not None:
                self.cheatlist_popup.popup(None, None, None, None, event.button, event.get_time())
                return path[0] in pathlist
        return False

    def CheatList_TreeView_popup_menu_cb(self, widget, data=None):
        pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
        if len(pathlist):
            self.cheatlist_popup.popup(None, None, None, None, 0, 0)
            return True
        return False

    def Scan_Button_clicked_cb(self, button, data=None):
        self.do_scan()
        return True

    def Stop_Button_clicked_cb(self, button, data=None):
        self.command_lock.acquire()
        self.command_send('stop')
        self.is_scanning = False
        self.command_lock.release()
        return True

    def Reset_Button_clicked_cb(self, button, data=None):
        self.reset_scan()
        return True

    def Logo_EventBox_button_release_event_cb(self, widget, data=None):
        self._ui.about_dialog.run()
        self._ui.about_dialog.hide()
        return True

    # Process list

    def ProcessFilter_Input_changed_cb(self, widget, data=None):
        self.ProcessList_Refilter_Generic()

    def UserFilter_Input_changed_cb(self, widget, data=None):
        self.ProcessList_Refilter_Generic()

    def ProcessList_Refilter_Generic(self):
        self.processlist_filter.refilter()
        self.processlist_tv.set_cursor(0)

    def ProcessList_TreeView_row_activated_cb(self, treeview, path, view_column, data=None):
        (model, iter) = self.processlist_tv.get_selection().get_selected()
        if iter is not None:
            (pid, process) = model.get(iter, 0, 2)
            self.select_process(pid, process)
            self._ui.procList_dialog.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    def SelectProcess_Button_clicked_cb(self, button, data=None):
        self.processlist_liststore.clear()
        for plist in misc.get_process_list():
            self.processlist_liststore.append(plist)
        self._ui.procList_dialog.show()
        while True:
            res = self._ui.procList_dialog.run()
            if res == Gtk.ResponseType.OK: # -5
                (model, iter) = self.processlist_tv.get_selection().get_selected()
                if iter is None:
                    self._ui.show_error('Please select a process')
                    continue
                else:
                    (pid, process) = model.get(iter, 0, 2)
                    self.select_process(pid, process)
                    break
            else: # for None and Cancel
                break
        self._ui.procList_dialog.hide()
        return True

    #######################
    # customed callbacks
    # (i.e. not standard event names are used)

    # Callback to hide window when 'X' button is pressed
    def hide_window_on_delete_event_cb(self, widget, event, data=None):
        widget.hide()
        return True

    # Memory editor

    def memoryeditor_hexview_char_changed_cb(self, hexview, offset, charval):
        addr = hexview.base_addr + offset
        self.write_value(addr, 'int8', charval)
        # return False such that the byte the default handler will be called, and will be displayed correctly 
        return False

    def memoryeditor_key_press_event_cb(self, window, event, data=None):
        keycode = event.keyval
        pressedkey = Gdk.keyval_name(keycode)
        if pressedkey == 'w' and (event.state & Gdk.ModifierType.CONTROL_MASK):
            self.memoryeditor_window.hide()
        elif pressedkey == 'Escape':
            self.memoryeditor_window.hide()

    def MemoryEditor_Refresh_Button_clicked_cb(self, button, data=None):
        dlength = len(self.memoryeditor_hexview.payload)
        data = self.read_memory(self.memoryeditor_hexview.base_addr, dlength)
        if data is None:
            self.memoryeditor_window.hide()
            self._ui.show_error('Cannot read memory')
            return
        old_addr = self.memoryeditor_hexview.get_current_addr()
        self.memoryeditor_hexview.payload = bytes(data)
        self.memoryeditor_hexview.show_addr(old_addr)


    # Manually add cheat

    def focus_on_next_widget_cb(self, widget, data=None):
        widget.get_toplevel().child_focus(Gtk.DirectionType.TAB_FORWARD)
        return True

    def Type_ComboBoxText_changed_cb(self, combo_box):
        data_type = combo_box.get_active_text()
        if data_type in misc.TYPESIZES_G2S:
            self.addcheat_length_spinbutton.set_value(misc.TYPESIZES_G2S[data_type][0])
            self.addcheat_length_spinbutton.set_sensitive(False)
        else:
            self.addcheat_length_spinbutton.set_sensitive(True)

    # Main window

    def cheatlist_edit_start(self, a, b, c):
        self.cheatlist_editing = True
    def cheatlist_edit_cancel(self, a):
        self.cheatlist_editing = False

    def scanresult_delete_selected_matches(self, menuitem, data=None):
        (model, pathlist) = self.scanresult_tv.get_selection().get_selected_rows()
        match_id_list = ','.join(str(model.get_value(model.get_iter(path), 6)) for path in pathlist)
        self.command_lock.acquire()
        self.command_send(f'delete {match_id_list}')
        self.update_scan_result()
        self.command_lock.release()

    def scanresult_popup_cb(self, menuitem, data=None):
        (model, pathlist) = self.scanresult_tv.get_selection().get_selected_rows()
        if data == 'add_to_cheat_list':
            for path in reversed(pathlist):
                (addr, value, typestr) = model.get(model.get_iter(path), 0, 1, 2)
                self.add_to_cheat_list(addr, value, typestr)
            return True
        addr = model.get_value(model.get_iter(pathlist[0]), 0)
        if data == 'browse_this_address':
            self.browse_memory(addr)
            return True
        elif data == 'scan_for_this_address':
            self.scan_for_addr(addr)
            return True
        return False

    def value_input_key_press_event_cb(self, main_window, event, data=None):
        keycode = event.keyval
        pressedkey = Gdk.keyval_name(keycode)
        if pressedkey == 'j' and (event.state & Gdk.ModifierType.CONTROL_MASK):
            if self.cheatlist_tv.is_focus() == self.scanresult_tv.is_focus():
                self.scanresult_tv.grab_focus()
                self.scanresult_tv.set_cursor(0)
            else:
                self._ui.value_input.grab_focus()

    def ScanResult_TreeView_key_press_event_cb(self, scanresult_tv, event, data=None):
        keycode = event.keyval
        pressedkey = Gdk.keyval_name(keycode)
        if pressedkey == 'Return':
            (model, pathlist) = self.scanresult_tv.get_selection().get_selected_rows()
            for path in reversed(pathlist):
                (addr, value, typestr) = model.get(model.get_iter(path), 0, 1, 2)
                self.add_to_cheat_list(addr, value, typestr)
        elif pressedkey in {'Delete', 'BackSpace'}:
            self.scanresult_delete_selected_matches(None)
        elif pressedkey == 'j' and (event.state & Gdk.ModifierType.CONTROL_MASK):
            self.cheatlist_tv.grab_focus()
            if self.cheatlist_tv.get_cursor()[0] is not None:
                curpos = self.cheatlist_tv.get_cursor()[0]
                valcol = self.cheatlist_tv.get_column(5)
                self.cheatlist_tv.set_cursor(curpos, valcol)

    def CheatList_TreeView_key_press_event_cb(self, cheatlist_tv, event, data=None):
        keycode = event.keyval
        pressedkey = Gdk.keyval_name(keycode)
        if pressedkey in {'Delete', 'BackSpace'}:
            (model, pathlist) = self.cheatlist_tv.get_selection().get_selected_rows()
            for path in reversed(pathlist):
                self.cheatlist_liststore.remove(model.get_iter(path))
        elif pressedkey == 'j' and (event.state & Gdk.ModifierType.CONTROL_MASK):
            self.scanresult_tv.grab_focus()
            if self.scanresult_tv.get_cursor()[0] is not None:
                self.scanresult_tv.set_cursor(0)

    def cheatlist_popup_cb(self, menuitem, data=None):
        self.cheatlist_editing = False
        (model, pathlist) = self.cheatlist_tv.get_selection().get_selected_rows()
        if data == 'remove_entry':
            for path in reversed(pathlist):
                self.cheatlist_liststore.remove(model.get_iter(path)) 
            return True
        addr = model.get_value(model.get_iter(pathlist[0]), 2)
        if data == 'browse_this_address':
            self.browse_memory(addr)
            return True
        elif data == 'copy_address':
            addr = '%x' %(addr,)
            self.clipboard.set_text(addr, len(addr))
            return True
        return False

    def cheatlist_toggle_lock(self, row):
        if self.cheatlist_liststore[row][5]: # valid
            locked = self.cheatlist_liststore[row][0]
            locked = not locked
            self.cheatlist_liststore[row][0] = locked
        if locked:
            #TODO: check value(valid number & not overflow), if failed, unlock it and do nothing
            pass
        else:
            #TODO: update its value?
            pass
        return True

    def cheatlist_toggle_lock_cb(self, cellrenderertoggle, row_str, data=None):
        pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
        if not row_str:
            return True
        cur_row = int(row_str)
        # check if the current row is part of the selection
        found = False
        for path in pathlist:
            row = path[0]
            if row == cur_row:
                found = True
                break
        if not found:
            self.cheatlist_toggle_lock(cur_row)
            return True
        # the current row is part of the selection
        for path in pathlist:
            row = path[0]
            self.cheatlist_toggle_lock(row)
        return True

    def cheatlist_toggle_lock_flag_cb(self, cell, path, new_text, data=None):
        self.cheatlist_editing = False
        # currently only one lock flag is supported
        return True

    def cheatlist_edit_description_cb(self, cell, path, new_text, data=None):
        self.cheatlist_editing = False
        pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
        for path in pathlist:
            row = path[0]
            self.cheatlist_liststore[row][1] = new_text
        return True

    def cheatlist_edit_value_cb(self, cell, path, new_text, data=None):
        self.cheatlist_editing = False
        # ignore empty value
        if new_text == '':
            return True
        pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
        for path in pathlist:
            row = path[0]
            if not self.cheatlist_liststore[row][5]: #not valid
                continue
            self.cheatlist_liststore[row][4] = new_text
            if self.cheatlist_liststore[row][0]: # locked
                # data_worker will handle this
                pass
            else:
                (addr, typestr, value) = self.cheatlist_liststore[row][2:5]
                self.write_value(addr, typestr, value)
        return True

    def cheatlist_edit_type_cb(self, cell, path, new_text, data=None):
        self.cheatlist_editing = False
        pathlist = self.cheatlist_tv.get_selection().get_selected_rows()[1]
        for path in pathlist:
            row = path[0]
            (addr, typestr, value) = self.cheatlist_liststore[row][2:5]
            if new_text == typestr:
                continue
            if new_text in {'bytearray', 'string'}:
                self.cheatlist_liststore[row][4] = misc.bytes2value(new_text, self.read_memory(addr, misc.get_type_size(typestr, value)))
            self.cheatlist_liststore[row][3] = new_text
            self.cheatlist_liststore[row][0] = False # unlock
        return True

    # Process list

    def processlist_filter_func(self, model, iter, data=None):
        (user, process) = model.get(iter, 1, 2)
        return process is not None and \
                self.processfilter_input.get_text().lower() in process.lower() and \
                user is not None and \
                self.userfilter_input.get_text().lower() in user.lower()

    def read_cheat_list(self, file):
        obj = json.load(file)
        for row in obj['cheat_list']:
            self.add_to_cheat_list(desc = row[1], typestr = row[3],
                                   addr = row[2], value   = row[4], at_end=True)

    def write_cheat_list(self, file):
        obj = { 'cheat_list' : [] }
        for row in self.cheatlist_liststore:
            obj['cheat_list'].append(list(row))
        json.dump(obj, file)

    def scan_for_addr(self, addr):
        bits = misc.get_pointer_width()
        if bits is None:
            self._ui.show_error('Unknown architecture, you may report to developers')
            return
        self.reset_scan()
        self.scan_data_type = 'int%d' % bits
        self._ui.value_input.set_text('%#x' % addr)
        UIBuilder.combobox_set_active_item(self.scan_data_type_combobox, self.scan_data_type)
        self.do_scan()

    def browse_memory(self, addr=None):
        # select a region contains addr
        try:
            self._maps = misc.read_proc_maps(self._pid)
        except:
            self._ui.show_error('Cannot retrieve memory maps of that process, maybe it has exited (crashed), or you don\'t have enough privileges')
            return
        selected_region = None
        if addr is not None:
            for m in self._maps:
                if m['start_addr'] <= addr and addr < m['end_addr']:
                    selected_region = m
                    break
            if selected_region:
                if selected_region['flags'][0] != 'r': # not readable
                    self._ui.show_error('Address %x is not readable' % addr)
                    return
            else:
                self._ui.show_error('Address %x is not valid' % addr)
                return
        else:
            # just select the first readable region
            for m in self._maps:
                if m['flags'][0] == 'r':
                    selected_region = m
                    break
            if selected_region is None:
                self._ui.show_error('Cannot find a readable region')
                return
            addr = selected_region['start_addr']

        # read region if possible
        start_addr = max(addr - HEXEDIT_SPAN, selected_region['start_addr'])
        end_addr = min(addr + HEXEDIT_SPAN, selected_region['end_addr'])
        data = self.read_memory(start_addr, end_addr - start_addr)
        if data is None:
            self._ui.show_error('Cannot read memory')
            return
        self.memoryeditor_hexview.payload = misc.str2bytes(data)
        self.memoryeditor_hexview.base_addr = start_addr
        
        # set editable flag
        self.memoryeditor_hexview.editable = (selected_region['flags'][1] == 'w')

        self.memoryeditor_hexview.show_addr(addr)
        self.memoryeditor_window.show()

    # this callback will be called from other thread
    def progress_watcher(self):
        if self.command_lock.acquire(blocking=False):
            pgss = self.command_send('pgss')[0]['scan_progress']
            self._ui.scan_progbar.set_fraction(pgss)
            self.is_scanning = (pgss <= 1.0)
            self.command_lock.release()
        return self.is_scanning and not self.exiting_flag

    def add_to_cheat_list(self, addr, value, typestr, desc='No Description', at_end=False):
        # determine longest possible type
        types = typestr.split()
        vt = typestr
        for t in types:
            if t in misc.TYPENAMES_S2G:
                vt = misc.TYPENAMES_S2G[t]
                break
        if at_end:
            self.cheatlist_liststore.append([False, desc, addr, vt, str(value), True])
        else:
            self.cheatlist_liststore.prepend([False, desc, addr, vt, str(value), True])

    def select_process(self, pid: str, process_name: str):
        # ask backend for attaching the target process
        # update 'current process'
        # reset flags
        # for debug/log
        try:
            self._pid  = int(pid)
            self._maps = misc.read_proc_maps(pid)
        except:
            self._pid = 0
            self._ui.process_label.set_text('No process selected')
            self._ui.process_label.set_property('tooltip-text', 'Select a process')
            self._ui.show_error('Cannot retrieve memory maps of that process, maybe it has exited (crashed), or you don\'t have enough privileges')
        else:
            self._ui.process_label.set_text('%d - %s' % (pid, process_name))
            self._ui.process_label.set_property('tooltip-text', process_name)

        self.reset_scan(pid)

        # unlock all entries in cheat list
        for i in range(len(self.cheatlist_liststore)):
            self.cheatlist_liststore[i][0] = False

    def command_send(self, cmd: str, cap = 1024):
        "**", self._bg.sendall(cmd.encode())
        buf = self._bg.recv(cap)
        try:
            data = json.loads(buf)
            if len(data) and 'error' in data[0]:
                raise Exception(data[0]['error'])
        except Exception as e:
            if IS_DEBUG:
                print(f" -*-*- {buf.decode()}")
            self._ui.show_error(e.__str__())
        return data

    def reset_scan(self, reset_pid = -1):
        # reset search type and value type
        self.scanresult_liststore.clear()

        self.command_lock.acquire()
        self.command_send(f'reset {reset_pid}')
        self.update_scan_result()
        self.command_lock.release()

        self._ui.scan_progbar.set_fraction(0.0)
        self._ui.scan_options.set_sensitive(True)
        self.is_first_scan = True
        self._ui.value_input.grab_focus()

    def apply_scan_settings (self):
        # scan data type
        assert(self.scan_data_type_combobox.get_active() >= 0)
        datatype = self.scan_data_type_combobox.get_active_text()
        scopeval = int(self.search_scope_scale.get_value()) + 1

        # Tell the scanresult sort function if a numeric cast is needed
        isnumeric = ('int' in datatype or 'float' in datatype or 'number' in datatype)
        self.scanresult_liststore.set_sort_func(1, UIBuilder.treeview_sort_cmp, (1, isnumeric))

        self.command_lock.acquire()
        # search scope
        self.command_send(f'option scan_data_type {datatype}\n option region_scan_level {scopeval}')
        # TODO: ugly, reset to make region_scan_level taking effect
        self.command_send('reset')
        self.command_lock.release()

    # perform scanning through backend
    # set GUI if needed
    def do_scan(self):
        if self._pid == 0:
            self._ui.show_error('Please select a process')
            return
        assert(self.scan_data_type_combobox.get_active() >= 0)
        data_type = self.scan_data_type_combobox.get_active_text()
        cmd = self._ui.value_input.get_text()
   
        try:
            cmd = misc.check_scan_command(data_type, cmd, self.is_first_scan)
        except Exception as e:
            # this is not quite good
            self._ui.show_error(e.args[0])
            return

        # disable the window before perform scanning, such that if result come so fast, we won't mess it up
        self._ui.scan_options.set_sensitive(False)

        # disable set of widgets interfering with the scan
        for wid in self.disablelist:
            wid.set_sensitive(False)
        
        # Replace scan_button with stop_button
        self._ui.scan_button.set_visible(False)
        self._ui.stop_button.set_visible(True)

        self.is_scanning = True
        # set scan options only when first scan, since this will reset backend
        if self.is_first_scan:
            self.apply_scan_settings()
            self.is_first_scan = False
        GLib.source_remove(self._watch_id)
        self._watch_id = GLib.timeout_add(PROGRESS_INTERVAL,
            self.progress_watcher, priority=GLib.PRIORITY_DEFAULT_IDLE)
        self.scan_thread_func(cmd)

    def scan_thread_func(self, cmd: str):
        self.command_lock.acquire()
        self.command_send(f'find {cmd}')
        GLib.source_remove(self._watch_id)
        self._watch_id = GLib.timeout_add(DATA_WORKER_INTERVAL, self.data_worker)
        self._ui.scan_progbar.set_fraction(1.0)

        # enable set of widgets interfering with the scan
        for wid in self.disablelist:
            wid.set_sensitive(True)

        # Replace stop_button with scan_button
        self._ui.stop_button.set_visible(False)
        self._ui.scan_button.set_visible(True)
        self._ui.value_input.grab_focus()

        self.is_scanning = False
        self.update_scan_result()

        self.command_lock.release()

    def update_scan_result(self):

        info = self.command_send(f'info {self._pid}')[0]
        self._ui.main_window.set_title('Found: %d'% info['found'])

        if (info['found'] > SCAN_RESULT_LIST_LIMIT) or info['is_process_dead']:
            self.scanresult_liststore.clear()
            return

        addr = GObject.Value(GObject.TYPE_UINT64)
        off  = GObject.Value(GObject.TYPE_UINT64)
        cnt  = chr(32)

        matches = self.command_send(f'list L{cnt}', 4096)

        self.scanresult_tv.set_model(None)
        # temporarily disable model for scanresult_liststore for the sake of performance
        self.scanresult_liststore.clear()

        while len(matches):
            if IS_DEBUG:
                print(f'+= parse {len(matches)} matches')
            for m in matches:
                t   = m['types']
                rt  = m['region_type']
                mid = m['match_id']
                val = m['value']

                if t == 'unknown':
                    continue
                # `insert_with_valuesv` has the same function of `append`, but it's 7x faster
                # PY3 has problems with int's, so we need a forced guint64 conversion
                # See: https://bugzilla.gnome.org/show_bug.cgi?id=769532
                # Still 5x faster even with the extra baggage
                addr.set_uint64(int(m['addr'], 16))
                off .set_uint64(int(m['off'] , 16))
                self.scanresult_liststore.insert_with_valuesv(-1, [0, 1, 2, 3, 4, 5, 6], [addr, val, t, True, off, rt, mid])
                # self.scanresult_liststore.append([addr, val, t, True, off, rt, mid])
            matches = self.command_send(f'next L{cnt}', 4096)
        self.scanresult_tv.set_model(self.scanresult_liststore)

    # return range(r1, r2) where all rows between r1 and r2 (EXCLUSIVE) are visible
    # return range(0, 0) if no row visible
    def get_visible_rows(self, treeview):
        _range = treeview.get_visible_range()
        try:
            r1 = _range[0][0]
            r2 = _range[1][0] + 1
        except:
            r1 = r2 = 0
        return range(r1, r2)

    # read/write data periodically
    def data_worker(self):
        # non-blocking
        if self._pid and self.command_lock.acquire(blocking=False):
            info = self.command_send(f'info {self._pid}')[0]
            if not info['is_process_dead']:
                self.refresh_tree(info['found'])
            self.command_lock.release()
        return not self.exiting_flag

    def refresh_tree(self, new_cnt:int):
        if self._cnt != new_cnt:
            # Write to memory locked values in cheat list
            for i in self.cheatlist_liststore:
                if i[0] and i[5]: # locked and valid
                    self.write_value(i[2], i[3], i[4]) # addr, typestr, value
            # Update visible (and unlocked) cheat list rows
            rows = self.get_visible_rows(self.cheatlist_tv)
            for i in rows:
                locked, desc, addr, typestr, value, valid = self.cheatlist_liststore[i]
                if valid and not locked:
                    newvalue = self.read_value(addr, typestr, value)
                    if newvalue is None:
                        self.cheatlist_liststore[i] = (False, desc, addr, typestr, '??', False)
                    elif newvalue != value and not self.cheatlist_editing:
                        self.cheatlist_liststore[i] = (locked, desc, addr, typestr, str(newvalue), valid)
            # Update visible scanresult rows
            rows = self.get_visible_rows(self.scanresult_tv)
            for i in rows:
                row = self.scanresult_liststore[i]
                addr, cur_value, scanmem_type, valid = row[:4]
                if valid:
                    new_value = self.read_value(addr, misc.TYPENAMES_S2G[scanmem_type.split(' ', 1)[0]], cur_value)
                    if new_value is not None:
                        row[1] = str(new_value)
                    else:
                        row[1] = '??'
                        row[3] = False
            self._cnt = new_cnt

    def read_value(self, addr, typestr, prev_value):
        return misc.bytes2value(typestr, self.read_memory(addr, misc.get_type_size(typestr, prev_value)))
    
    # addr could be int or str
    def read_memory(self, addr, length):
        if not isinstance(addr,str):
            addr = '%x'%(addr,)

        self.command_lock.acquire()
        data = self.command_send(f'dump {addr} {length}')
        print(data)
        data = data[0]['chunk']
        self.command_lock.release()

        # TODO raise Exception here isn't good
        if len(data) != length:
            # self._ui.show_error('Cannot access target memory')
            data = None
        return data
            
    # addr could be int or str
    def write_value(self, addr, typestr, value):
        if not isinstance(addr,str):
            addr = '%x'%(addr,)

        self.command_lock.acquire()
        self.command_send(f'write {typestr} {addr} {value}')
        self.command_lock.release()

    def exit(self, object, data=None):
        self.exiting_flag = True
        self.command_send('exit')
        Gtk.main_quit()


if __name__ == '__main__':
    # accept connections
    connect,_ = misc.wait_connection(SOCK_PATH)
    try:
        # Init application
        gc_instance = GameConqueror(connect)
        # Start
        Gtk.main()
    finally:
        # close the connection
        connect.close()
        # remove the socket file
        os.unlink(SOCK_PATH)
