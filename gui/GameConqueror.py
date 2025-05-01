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

import scanmem, misc, gi, ctypes
# check toolkit version
gi.require_version('Gtk', '3.0')
# import Gtk libraries
from gi.repository import Gtk, Gdk, GLib

from hexview import HexView

MATCH_CNT = 32

class GcUI(Gtk.Builder):

    def __init__(self):
        super(GcUI, self).__init__()

        self.set_translation_domain(misc.DOMAIN_TRS)
        self.add_from_file(misc.get_ui_xml_path('gtk'))

        self.    main_window = self.get_object('MainWindow')
        self.  mmedit_window = self.get_object('MemoryEditor_Window')
        self.addChAddr_input = self.get_object('AddCheatAddr_Input')
        self.addChDesc_input = self.get_object('AddCheatDesc_Input')
        self.addChType_vsel  = self.get_object('AddCheatType_Select')
        self.addChSize_numin = self.get_object('AddCheatSize_NumInput')
        self.scanScope_range = self.get_object('SearchScope_Range')
        self.scanDataT_vsel  = self.get_object('ScanDataType_Select')
        self.scanMatchT_vsel = self.get_object('ScanMatchType_Select')
        self.signIntVal_chbx = self.get_object('SignedIntType_Checkbox')
        self. process_label  = self.get_object('Process_Label')
        self.procFiltr_input = self.get_object('ProcessFilter_Input')
        self.userFiltr_input = self.get_object('UserFilter_Input')
        self.  scanVal_input = self.get_object('Value_Input')
        self.    scan_button = self.get_object('Scan_Button')
        self.    proc_button = self.get_object('SelectProcess_Button')
        self.   cheat_button = self.get_object('AddCheat_Button')
        self.   reset_button = self.get_object('Reset_Button')
        self.   scan_options = self.get_object('ScanOption_Frame')
        self.   scan_progbar = self.get_object('ScanProgress_ProgressBar')
        self. mmedit_adentry = self.get_object('MemoryEditor_Address_Entry')
        self.  scanRes_tree  = self.get_object('ScanResult_TreeView')
        self.cheatList_tree  = self.get_object('CheatList_TreeView')
        self. procList_tree  = self.get_object('ProcessList_TreeView')

        # make processes tree
        col1_bg = [('foreground-rgba', Gdk.RGBA(1.0,1.0,1.0,0.6)),
                   ('background-rgba', Gdk.RGBA(0.0,0.0,0.0,0.3))]
        # Set scan data type
        data_r  = ([f' {misc.SCAN_VALUE_TYPES[i]} ', f' ﹝{misc.ltr(misc.SCAN_VALUE_TOOLTIP[i])}﹞'] for i in range(9))
        cheat_r = ([f' {scanmem.TYPE_NAMES[i]} '   , f' :  {misc.ltr(misc.CHEAT_LIST_TOOLTIP[i])}'] for i in range(8))
        match_r = ([f'  {misc.SCAN_MATCH_TYPES[i]}', f' ∙ {misc.ltr(misc.SCAN_MATCH_TOOLTIP[i])}'] for i in range(8))
        # add selectable items
        GcUI.combobox_add_active_item(self.scanDataT_vsel , data_r , props=[ [('family', 'monospace')], col1_bg ])
        GcUI.combobox_add_active_item(self.addChType_vsel , cheat_r, props=[ [('family', 'monospace')], col1_bg ])
        GcUI.combobox_add_active_item(self.scanMatchT_vsel, match_r, props=[ [('size-points', 13.0)]  , col1_bg ])
        # add dialog handlers for default buttos
        for dialog in [
            self.get_object('ValueInputHelp_Button'),
            self.get_object('About_Logo') ]: dialog.connect('clicked', self.on_ShowDialog_handler)
        # deferred creation
        self. mmedit_hexview : HexView = None
        # init ScanResult @ columns:      addr, value, type, valid, offset, region, match_id
        self.scanRes_list = Gtk.ListStore(str , str  , str , bool , str   , str   , int)
        self.scanRes_tree.set_model(self.scanRes_list)
        # init ProcessList @ columns:      pid, usr, process
        self.procList_list = Gtk.ListStore(int, str, str)
        self.procList_filter = self.procList_list.filter_new()
        self.procList_filter.set_visible_func(self.on_ProcessFilter_handler)
        self.procList_tree.set_model(Gtk.TreeModelSort(model=self.procList_filter))
        self.procList_tree.set_search_column(2)
        # init CheatsList @ columns:        lock, desc, addr, type, value, valid
        self.cheatList_list = Gtk.ListStore(bool, str , str , str , str  , bool)
        self.cheatList_tree.set_model(self.cheatList_list)
        # init scanresult treeview columns
        # we may need a cell data func here
        GcUI.treeview_append_column(self.scanRes_tree, 'Address', 0, #data_func=GcUI.format16,
                                    attributes=[('text', 0)],
                                    properties=[('family', 'monospace')])

        GcUI.treeview_append_column(self.scanRes_tree, 'Value', 1,
                                    attributes=[('text', 0)],
                                    properties=[('family', 'monospace')])

        GcUI.treeview_append_column(self.scanRes_tree, 'Offset', 4, #data_func=GcUI.format16,
                                    attributes=[('text', 4)],
                                    properties=[('family', 'monospace')])

        GcUI.treeview_append_column(self.scanRes_tree, 'Region Type', 5,
                                    attributes=[('text', 5)],
                                    properties=[('family', 'monospace')])
        # make processes tree
        GcUI.treeview_append_column(self.procList_tree, 'PID'    , 0, attributes=[('text',0)])
        GcUI.treeview_append_column(self.procList_tree, 'User'   , 1, attributes=[('text',1)])
        GcUI.treeview_append_column(self.procList_tree, 'Process', 2, attributes=[('text',2)])
        # Init signals
        self.signIntVal_chbx.connect('toggled', self.on_SignToggle_handler)
        self.addChType_vsel .connect('changed', self.on_CheatType_handler)
        self.procFiltr_input.connect('changed', self.on_TextInput_handler)
        self.userFiltr_input.connect('changed', self.on_TextInput_handler)
        self.    main_window.connect('key-press-event', self.on_WinKey_handler)
        self.  mmedit_window.connect('key-press-event', self.on_WinKey_handler)


    ############################
    # Handlers
    def on_TextInput_handler(self, input, data=None):
        is_usrFi = input is self.userFiltr_input
        is_prcFi = input is self.procFiltr_input
        if is_usrFi or is_prcFi:
            self.procList_filter.refilter()
            self.procList_tree.set_cursor(0)

    def on_ProcessFilter_handler(self, model, iter, data=None):
        user, proc = model.get(iter, 1, 2)
        pFiltxt = self.procFiltr_input.get_text()
        uFiltxt = self.userFiltr_input.get_text()
        return proc and pFiltxt.lower() in proc.lower() and\
               user and uFiltxt.lower() in user.lower()

    def on_CheatType_handler(self, sbox: Gtk.ComboBox, data=None):
        size = scanmem.TYPE_SIZES[ sbox.get_active() ]
        self.addChSize_numin.set_value(size)
        self.addChSize_numin.set_sensitive(size == 0)

    def on_SignToggle_handler(self, chx: Gtk.CheckButton, data=None):
        sign  = chx.get_active() 
        store = self.scanDataT_vsel.get_model()
        iter  = store.get_iter_first()
        idx   = 0
        while idx <= misc.SCAN_VALUE_TYPES.index('Int64') and iter:
            val = misc.SCAN_VALUE_TYPES[idx]
            store.set_value(iter, 0, (f' U{val.lower()}' if not sign else f' {val}'))
            iter = store.iter_next(iter); idx += 1

    def on_ShowDialog_handler(self, btn: Gtk.Button, on_OK_handler=lambda:False):
        btn_id : str = Gtk.Buildable.get_name(btn)
        idx_ri : int = btn_id.index('_')
        dialog = self.get_object(f'{btn_id[0:idx_ri]}_Dialog')
        while dialog.run() == Gtk.ResponseType.OK and on_OK_handler():
            continue
        dialog.hide()

    def on_WinKey_handler(self, win, event, data=None):
        key  = Gdk.keyval_name(event.keyval)
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK

        is_mmedit = win is self.mmedit_window
        is_main   = win is self.  main_window

        cheats_tv  = self.cheatList_tree
        scanres_tv = self.scanRes_tree
        scanval_in = self.scanVal_input

        if (key == 'x' and ctrl) or key == 'Escape':
            if is_mmedit: win.hide()
        elif key == 'j' and ctrl:
            if is_main:
                if cheats_tv.is_focus() or scanval_in.is_focus():
                    "focus", scanres_tv.grab_focus()
                    curpos = scanres_tv.get_cursor()[0]
                    if curpos is not None:
                        scanres_tv.set_cursor(0)
                elif scanres_tv.is_focus():
                    "focus", cheats_tv.grab_focus()
                    curpos = cheats_tv.get_cursor()[0]
                    if curpos is not None:
                        valcol = cheats_tv.get_column(5)
                        "*****", cheats_tv.set_cursor(curpos, valcol)
                else: scanval_in.grab_focus()

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
                               data_func = None,
                               render    : type=Gtk.CellRendererText(),
                               attributes: list=None,
                               properties: list=None,
                               signals   : list=None):
        # create renderer of given type
        column = Gtk.TreeViewColumn(misc.ltr(title))
        column.set_resizable(resizable)
        column.pack_start(render, True)
        treeview.append_column(column)
        if sort_id != -1:
            column.set_sort_column_id(sort_id)
        if data_func:
            column.set_cell_data_func(render, data_func, sort_id)
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
    def treeview_remove_entries(treeview):
        lstore, plist = treeview.get_selection().get_selected_rows()
        for path in reversed(plist):
            lstore.remove(lstore.get_iter(path))

    @staticmethod
    # target is optional data to callback
    def new_popup_menu(target, itemprops: list[ tuple[str] ]):
        menu = Gtk.Menu()
        for label,handler in itemprops:
            item = Gtk.MenuItem(label=misc.ltr(label))
            menu.append(item)
            item.connect('activate', handler, target)
        menu.show_all()
        return menu

    @staticmethod
    # set active item of the `combobox` such that the value at `col` is `name`
    def combobox_add_active_item(cmbox: Gtk.ComboBox,
                                 rows: tuple[list],
                                 props: list = None,
                                 templ_cols = [str, str]):
        # create the new model and set the columns type
        model_type = Gtk.ListStore()
        model_type.set_column_types(templ_cols)
        # adds the user text rows
        for row in rows:
            model_type.append(row)
        # apply model for combo-box
        cmbox.set_model(model_type)
        # create renderer for each column with individual style
        for i in range(len(templ_cols)):
            cell = Gtk.CellRendererText()
            if props and i < len(props) and props[i]:
                for key,val in props[i]:
                    cell.set_property(key, val)
            cmbox.pack_start(cell, True)
            cmbox.add_attribute(cell, "text", i)

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


class GameConqueror(scanmem.Scanmem):

    def __init__(self, args: tuple):
        super(GameConqueror, self).__init__(*args)
        ###########################
        # init others (backend, flag...)
        self._exec: str  = ''
        self._mcnt: int  = 0 # found count
        self._nreg: int  = 0 # regions count
        self._wtid: int  = 0
        self._maps: list = None
        self._ui  : GcUI = None

    def Create_MemoryEditor(self):
        # init memory editor
        self._ui.mmedit_hexview = HexView()
        self._ui.mmedit_window.get_child().pack_start(self._ui.mmedit_hexview, True, True, 0)
        self._ui.mmedit_hexview.show_all()
        self._ui.mmedit_hexview.connect('char-changed', self.MemoryEditor_Byte_Changed_handler)

    def create_window(self):
        ##################################
        # init GUI
        gcui = self._ui = GcUI()

        # apply setting
        gcui.scanMatchT_vsel.set_active(self.match_type)
        gcui.scanDataT_vsel .set_active(self.scan_type)
        gcui.scanScope_range.set_value (self.scan_scope)
        gcui.signIntVal_chbx.set_active(True)
        gcui.addChType_vsel .set_active(scanmem.TYPE_NAMES.index('i32'))
        # ---
        model_cheatCombo_type = Gtk.ListStore(str)
        # CheatList active flag
        self.cheatlist_editing = False
        # Lock
        GcUI.treeview_append_column(gcui.cheatList_tree, 'Lock', 0, render = Gtk.CellRendererToggle(),
                                    attributes = [('active',0)],
                                    properties = [('activatable' , True ),
                                                  ('radio'       , False),
                                                  ('inconsistent', False)],
                                    signals    = [('toggled', self.cheatlist_toggle_lock_cb)])
        # Description
        GcUI.treeview_append_column(gcui.cheatList_tree, 'Description', 1,
                                    attributes = [('text',1)],
                                    properties = [('editable', True)],
                                    signals    = [('edited'          , self.cheatlist_edit_description_cb),
                                                  ('editing-started' , self.cheatlist_edit_start),
                                                  ('editing-canceled', self.cheatlist_edit_cancel)])
        # Address
        GcUI.treeview_append_column(gcui.cheatList_tree, 'Address', 2, #data_func=GcUI.format16,
                                    attributes = [('text',2)],
                                    properties = [('family', 'monospace')])
        # Type
        GcUI.treeview_append_column(gcui.cheatList_tree, 'Type', 3, render = Gtk.CellRendererCombo(),
                                    attributes = [('text',3)],
                                    properties = [('editable'   , True ),
                                                  ('has-entry'  , False),
                                                  ('model'      , model_cheatCombo_type),
                                                  ('text-column', 0)],
                                    signals    = [('edited'           , self.cheatlist_edit_type_cb),
                                                  ('editing-started'  , self.cheatlist_edit_start),
                                                  ('editing-canceled' , self.cheatlist_edit_cancel)])
        # Value 
        GcUI.treeview_append_column(gcui.cheatList_tree, 'Value', 4,
                                    attributes = [('text',4)],
                                    properties = [('editable', True),
                                                  ('family', 'monospace')],
                                    signals    = [('edited'          , self.cheatlist_edit_value_cb),
                                                  ('editing-started' , self.cheatlist_edit_start),
                                                  ('editing-canceled', self.cheatlist_edit_cancel)])
        # set list/input keyboard signals
        gcui.scanVal_input .connect('key-press-event', self.on_KeyPress_handler)
        gcui.cheatList_tree.connect('key-press-event', self.on_KeyPress_handler)
        gcui.scanRes_tree  .connect('key-press-event', self.on_KeyPress_handler)
        # get list of things to be disabled during scan
        gcui. proc_button.connect('clicked', self.on_ProcessList_Open)
        gcui. scan_button.connect('clicked', self.on_ScanProgress_Toggle)
        gcui.cheat_button.connect('clicked', self.on_AddCheat_Open)
        # init AddCheat Types
        for entry in scanmem.TYPE_NAMES:
            model_cheatCombo_type.append([entry])
        # other handlers
        gcui.scanScope_range.connect('format-value', self.SearchScope_format_handler)
        # init popup menu for scanresult
        self.scanresult_popup = GcUI.new_popup_menu(gcui.scanRes_tree, [
            ('Add to cheat list'    , self.do_CheatList_Add),
            ('Browse this address'  , self.on_PopupMenu_Browse),
            ('Scan for this address', self.on_PopupMenu_Scan),
            ('Remove this match'    , self.do_ListItems_Remove)
        ])
        # init popup menu for cheatlist
        self.cheatlist_popup = GcUI.new_popup_menu(gcui.cheatList_tree, [
            ('Browse this address', self.on_PopupMenu_Browse),
            ('Copy address'       , self.on_PopupMenu_Copy),
            ('Remove this entry'  , self.do_ListItems_Remove)
        ])
        gcui.connect_signals(self)
        gcui.main_window.connect('destroy', self.exit)
        # initialize other objects
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)


    ###########################
    # GUI callbacks

    # Memory editor

    def MemoryEditor_Button_clicked_cb(self, button, data=None):
        if not self._cpid:
            self._ui.show_error('Please select a process')
            return
        if not self._ui.mmedit_hexview:
            self.Create_MemoryEditor()
        self.browse_memory()
        return True

    def MemoryEditor_Handle_Address_cb(self, widget, data=None):
        txt = self._ui.mmedit_adentry.get_text().strip()
        if txt == '':
            return
        try:
            addr = int(txt, 16)
            self.browse_memory(addr)
        except:
            self._ui.show_error('Invalid address')

    # Manually add cheat

    def confirm_add_cheat(self):
        # load input values
        addr : str = self._ui.addChAddr_input.get_text()
        desc : str = self._ui.addChDesc_input.get_text()
        size : int = self._ui.addChSize_numin.get_value_as_int()
        t    : int = self._ui.addChType_vsel .get_active()
        try:
            if int(addr, 16) <= 0:
                raise
        except:
            self._ui.show_error('Please enter a valid address.')
            return True
        # ---
        type = scanmem.TYPE_NAMES[t]
        val  = '' 
        match type[0]:
            case 'i': val = '0'
            case 'f': val = '0.0'
            case 's': val = ' ' * size
            case 'a': val = '00 ' * size
        # add to list
        self._ui.cheatList_list.append([False, desc, addr, type, val, True])
        return False

    def on_AddCheat_Open(self, btn: Gtk.Button, data=None):
        return self._ui.on_ShowDialog_handler(btn, self.confirm_add_cheat)

    # Main window

    def RemoveAllCheat_Button_clicked_cb(self, button, data=None):
        self._ui.cheatList_list.clear()
        return True

    def LoadCheat_Button_clicked_cb(self, button, data=None):
        self._ui.open_file_dialog('Select CheatList', self.read_cheat_list, False)
        return True

    def SaveCheat_Button_clicked_cb(self, button, data=None):
        self._ui.open_file_dialog('Save CheatList As', self.write_cheat_list, True)
        return True

    def SearchScope_format_handler(self, el: Gtk.Scale, scale: ctypes.c_double, data=None):
        self.search_scope = int(scale)
        return misc.SEARCH_SCOPE_NAMES[self.search_scope]

    def ScanResult_TreeView_popup_menu_cb(self, widget, data=None):
        pathlist = self._ui.scanRes_tree.get_selection().get_selected_rows()[1]
        if len(pathlist):
            self.scanresult_popup.popup(None, None, None, None, 0, 0)
            return True
        return False

    def ScanResult_TreeView_button_press_event_cb(self, widget, event, data=None):
        # add to cheat list
        (model, pathlist) = self._ui.scanRes_tree.get_selection().get_selected_rows()
        if event.button == 1 and event.get_click_count()[1] > 1: # left double click
            for path in pathlist:
                (addr, value, typestr) = model.get(model.get_iter(path), 0, 1, 2)
                self.add_to_cheat_list(addr, value, typestr)
        elif event.button == 3: # right click
            path = self._ui.scanRes_tree.get_path_at_pos(int(event.x),int(event.y))
            if path is not None:
                self.scanresult_popup.popup(None, None, None, None, event.button, event.get_time())
                return path[0] in pathlist
        return False

    def CheatList_TreeView_button_press_event_cb(self, widget, event, data=None):
        if event.button == 3: # right click
            pathlist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
            path = self._ui.cheatList_tree.get_path_at_pos(int(event.x),int(event.y))
            if path is not None:
                self.cheatlist_popup.popup(None, None, None, None, event.button, event.get_time())
                return path[0] in pathlist
        return False

    def CheatList_TreeView_popup_menu_cb(self, widget, data=None):
        pathlist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
        if len(pathlist):
            self.cheatlist_popup.popup(None, None, None, None, 0, 0)
            return True
        return False

    def on_ScanProgress_Toggle(self, btn: Gtk.Button, data=None):
        if btn.get_label() != '⛔':
            self.scan_start()
        else:
            _, emsg = self.stop_scanning()
            if emsg:
                self._ui.show_error(emsg)
        return True

    def Reset_Button_clicked_cb(self, button, data=None):
        self.reset_scan()
        return True

    def on_ProcessList_Open(self, btn: Gtk.Button, data=None):
        proc_list = self._ui.procList_list
        proc_list.clear()
        for plist in misc.get_process_list():
            proc_list.append(plist)
        return self._ui.on_ShowDialog_handler(btn, self.check_selected_process)

    # Process list
    def check_selected_process(self):
        lstr, iter = self._ui.procList_tree.get_selection().get_selected()
        pid , proc = lstr.get(iter, 0, 2) if iter else ('','')
        if not pid:
            self._ui.show_error('Please select a process')
        else:
            if self._wtid:
                GLib.source_remove(self._wtid)
            self.select_process(pid, proc)
        return not pid

    #######################
    # customed callbacks
    # (i.e. not standard event names are used)

    # Memory editor

    def MemoryEditor_Byte_Changed_handler(self, hexview, offset, charval):
        addr = hexview.base_addr + offset
        self.write_value(addr, 'int8', charval)
        # return False such that the byte the default handler will be called, and will be displayed correctly 
        return False

    def MemoryEditor_Refresh_Button_clicked_cb(self, button, data=None):
        addr = int(self._ui.mmedit_hexview.base_addr)
        size = len(self._ui.mmedit_hexview.payload)
        old_addr = self._ui.mmedit_hexview.get_current_addr()
        buf,emsg = self.read_memory(addr, size)
        # ----
        if emsg:
            self._ui.show_error(emsg)
        # ----
        if buf != None:
            self._ui.mmedit_hexview.payload = buf
            self._ui.mmedit_hexview.show_addr(old_addr)
        else:
            self._ui.mmedit_window.hide()

    # Manually add cheat

    def on_next_widget_focus(self, widget, data=None):
        widget.get_toplevel().child_focus(Gtk.DirectionType.TAB_FORWARD)
        return True

    # Main window

    def cheatlist_edit_start(self, a, b, c):
        self.cheatlist_editing = True
    def cheatlist_edit_cancel(self, a):
        self.cheatlist_editing = False

    # # # # #
    # Popup menu item handlers
    # #
    def do_CheatList_Add(self, trigger=None, tree=None):
        lstor, plist = tree.get_selection().get_selected_rows()
        for path in plist:
            addr, val, typestr = lstor.get(lstor.get_iter(path), 0,1,2)
            self._ui.cheatList_list.append([False, " * ", addr, typestr, str(val), True])

    def on_PopupMenu_Copy(self, mitem, ltree):
        lstor, plist = ltree.get_selection().get_selected_rows()
        hexx = '%x'  % lstor.get_value(lstor.get_iter(plist[0]), 0)
        self.clipboard.set_text(hexx, len(hexx))
        return True

    def on_PopupMenu_Scan(self, mitem, ltree):
        lstor, plist = ltree.get_selection().get_selected_rows()
        hexx = '%#x' % lstor.get_value(lstor.get_iter(plist[0]), 0)
        self.reset_scan()
        self.scan_type = 2
        self._ui.scanVal_input.set_text(hexx)
        GcUI.combobox_set_active_item(self.scan_data_type_combobox, self.scan_type)
        self.scan_start()

    def on_MatchType_Select(self, item: Gtk.MenuItem, ltree=None):
        m = item.get_label()
        self.match_type = misc.SCAN_MATCH_TYPES.index(m)
        self._ui.scanMatchT_vsel.set_label(m)

    def on_PopupMenu_Browse(self, mitem, ltree):
        lstor, plist = ltree.get_selection().get_selected_rows()
        "***"; addr  = lstor.get_value(lstor.get_iter(plist[0]), 0)
        self.browse_memory(addr)
        return True

    def do_ListItems_Remove(self, trigger=None, tree=None):
        lstor, plist = tree.get_selection().get_selected_rows()
        is_scanres   = tree is self._ui.scanRes_tree
        list_id = []
        for path in plist:
            itr = lstor.get_iter(path)
            if is_scanres:
                list_id.append(str(lstor.get_value(itr, 6)))
            lstor.remove(itr)
        if is_scanres:
            self.del_selected_matches(list_id)

    def on_KeyPress_handler(self, target, event, data=None):
        key  = Gdk.keyval_name(event.keyval)
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK

        cheats_tv  = self._ui.cheatList_tree
        scanres_tv = self._ui.scanRes_tree
        scanval_in = self._ui.scanVal_input

        if key == 'Delete' or (key in {'d','-'} and ctrl):

            if target is scanres_tv or target is cheats_tv:
                self.do_ListItems_Remove(tree=target)

        elif key == 'Return' or (key in {'m','+'} and ctrl):

            if target is scanres_tv:
                self.do_CheatList_Add(tree=target)
            elif target is scanval_in:
                self.scan_start()

    def cheatlist_toggle_lock(self, row):
        if self._ui.cheatList_list[row][5]: # valid
            locked = self._ui.cheatList_list[row][0]
            locked = not locked
            self._ui.cheatList_list[row][0] = locked
        if locked:
            #TODO: check value(valid number & not overflow), if failed, unlock it and do nothing
            pass
        else:
            #TODO: update its value?
            pass
        return True

    def cheatlist_toggle_lock_cb(self, cellrenderertoggle, row_str, data=None):
        pathlist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
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
        pathlist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
        for path in pathlist:
            row = path[0]
            self._ui.cheatList_list[row][1] = new_text
        return True

    def cheatlist_edit_value_cb(self, cell, path, new_text, data=None):
        self.cheatlist_editing = False
        # ignore empty value
        if new_text == '':
            return True
        pathlist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
        for path in pathlist:
            row = path[0]
            if not self._ui.cheatList_list[row][5]: #not valid
                continue
            self._ui.cheatList_list[row][4] = new_text
            if self._ui.cheatList_list[row][0]: # locked
                # data_worker will handle this
                pass
            else:
                (addr, typestr, value) = self._ui.cheatList_list[row][2:5]
                self.write_value(addr, typestr, value)
        return True

    def cheatlist_edit_type_cb(self, cell, path, new_type, data=None):
        self.cheatlist_editing = False
        plist = self._ui.cheatList_tree.get_selection().get_selected_rows()[1]
        for p in plist:
            row = self._ui.cheatList_list[p[0]]
            addr, cur_type, val = row[2:5]
            if new_type != cur_type:
                row[0] = False # unlock
                row[3] = new_type
                if new_type in {'bytearray', 'string'}:
                    row[4] = self.read_value(addr, cur_type, val, new_type)
        return True

    # Process list

    def processlist_filter_func(self, model, iter, data=None):
        (user, process) = model.get(iter, 1, 2)
        return process is not None and \
                self.processfilter_input.get_text().lower() in process.lower() and \
                user is not None and \
                self.userfilter_input.get_text().lower() in user.lower()

    def read_cheat_list(self, file):
        for ch in self.load_cheat_list(file):
            self._ui.cheatList_list.append([
                False, ch['desc'], ch['addr'], ch['type'], ch['value'], True
            ])

    def write_cheat_list(self, file):
        self.store_cheat_list( file, self._ui.cheatList_list )

    def del_selected_matches(self, sel_ids: list[str] ):
        idx = 0
        while idx < len(sel_ids):
            self.command_send('delete '+','.join(sel_ids[ idx : idx+32 ]))
            idx += 32

    def browse_memory(self, addr=None):
        # select a region contains addr
        try:
            self._maps = misc.read_proc_maps(self._cpid)
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
        start_addr = max(addr - misc.HEXEDIT_SPAN_MAX, selected_region['start_addr'])
        end_addr   = min(addr + misc.HEXEDIT_SPAN_MAX, selected_region['end_addr'])
        # ----
        buf,emsg   = self.read_memory(start_addr, end_addr - start_addr)
        if  emsg:
            self._ui.show_error(emsg)
        # ----
        if buf != None:
            self._ui.mmedit_hexview.payload = buf
            self._ui.mmedit_hexview.show_addr(addr)
            # set editable flag
            self._ui.mmedit_hexview.base_addr = start_addr
            self._ui.mmedit_hexview.editable = (selected_region['flags'][1] == 'w')
            self._ui.mmedit_window.show()

    # this callback will be called from other thread
    def progress_watcher(self):
        if self._is_scanning:
            emsg,pgss,mcnt = self.get_scan_progress()
            if emsg:
                self._ui.show_error(emsg)

            self._mcnt = mcnt
            self._ui.scan_progbar.set_fraction(pgss)

            if pgss >= 1.0:
                self._is_scanning = False
                self.update_scan_result(mcnt)
                #self.reload_list_matches(m_count)
                self.set_ui_deactive(active=True)

        return self._is_scanning and not self._is_exiting

    def add_to_cheat_list(self, addr, value, typestr, desc='No Description', at_end=False):
        # determine longest possible type
        types = typestr.split()
        vt = typestr
        for t in types:
            if t in misc.TYPENAMES_S2G:
                vt = misc.TYPENAMES_S2G[t]
                break
        if at_end:
            self._ui.cheatList_list.append([False, desc, addr, vt, str(value), True])
        else:
            self._ui.cheatList_list.prepend([False, desc, addr, vt, str(value), True])

    def select_process(self, pid: str, process_name: str):
        # ask backend for attaching the target process
        # update 'current process'
        # reset flags
        # for debug/log
        try:
            self._cpid = pid
            self._maps = misc.read_proc_maps(pid)
            self._wtid = GLib.timeout_add(misc.LIVE_CHECKER_MS, self.process_status_checker)
        except:
            self._cpid = ''
            self._ui.process_label.set_text('No process selected')
            self._ui.process_label.set_property('tooltip-text', 'Select a process')
            self._ui.show_error('Cannot retrieve memory maps of that process, maybe it has exited (crashed), or you don\'t have enough privileges')
        else:
            self._ui.process_label.set_text('%d - %s' % (pid, process_name))
            self._ui.process_label.set_property('tooltip-text', process_name)

        self.reset_scan()

        # unlock all entries in cheat list
        for i in range(len(self._ui.cheatList_list)):
            self._ui.cheatList_list[i][0] = False

    def reset_scan(self):
        # reset search type and value type
        self._ui.scanRes_list.clear()

        emsg, rcount, exelnk = self.reset_process()

        self._ui.scan_progbar.set_fraction(0.0)
        self._ui.scan_options.set_sensitive(True)

        if emsg:
            self._ui.show_error(emsg)
        else:
            self._exec = exelnk
            self._nreg = rcount
            self._is_firstRun = True
            self._ui.process_label.set_text(f'{self._cpid} - {exelnk}')
            self._ui.scanVal_input.grab_focus()

    def apply_scan_settings(self, data_type: str, is_number = True):
        # Tell the scanresult sort function if a numeric cast is needed
        self._ui.scanRes_list.set_sort_func(1, GcUI.treeview_sort_cmp, (1, is_number))
        # search scope
        emsg, rcount, exelnk = self.reset_process()
        if not emsg:
            self._exec = exelnk
            self._nreg = rcount
        return emsg

    # perform scanning through backend
    # set GUI if needed
    def scan_start(self):
        if not self._cpid:
            self._ui.show_error('Please select a process')
            return
        # scan data type
        assert(self.scan_data_type_combobox.get_active() >= 0)
        data_type = self.scan_data_type_combobox.get_active_text()
        is_number = ('int' in data_type or 'float' in data_type or 'number' in data_type)
        search_val = self._ui.scanVal_input.get_text()

        try:
            cmd = misc.check_scan_command(data_type, search_val, self._is_firstRun)
        except Exception as e:
            # this is not quite good
            self._ui.show_error(e.args[0])
            return

        # set scan options only when first scan, since this will reset backend
        if self._is_firstRun:
            self.apply_scan_settings(data_type, is_number)

        _, emsg = self.start_scanning(cmd)
        if emsg:
            self._ui.show_error(emsg)
        else:
            self._is_firstRun = False
            self.set_ui_deactive()
            GLib.timeout_add(misc.PROGRESS_WATCH_MS, self.progress_watcher)

    def set_ui_deactive(self, active = False):
        # disable the window before perform scanning, such that if result come so fast, we won't mess it up
        self._ui.scan_options.set_sensitive(active)
        # disable set of widgets interfering with the scan
        for wid in [self._ui.reset_button,  self._ui.cheatList_tree, self._ui.get_object('processGrid'),
                    self._ui.scanVal_input, self._ui.  scanRes_tree, self._ui.get_object('buttonGrid'),
                    self._ui.mmedit_window]:
            wid.set_sensitive(active)
        self._ui.scan_button.set_label('🔎' if active else '⛔')

    def update_scan_result(self, m_count: int = 0):
        self._ui.main_window.set_title(misc.ltr('Found: %d')% m_count)
        self._ui.scanVal_input.grab_focus()

    def reload_list_matches(self):
        matches = self.send_command(f'list L{MATCH_CNT}', 4096)

        self._ui.scanRes_tree.set_model(None)
        # temporarily disable model for scanresult_liststore for the sake of performance
        self._ui.scanRes_list.clear()

        while len(matches):
            if self.is_debug:
                print(f'+= parse {len(matches)} matches')
            for m in matches:
                t   = m['types']
                rt  = m['region_type']
                mid = m['match_id']
                val = m['value']

                if t == 'unknown':
                    continue
                # `insert_with_valuesv` has the same function of `append`, but it's 7x faster
                # Still 5x faster even with the extra baggage
                addr = m['addr']
                off  = m['off']
                self._ui.scanRes_list.insert_with_valuesv(-1, [0, 1, 2, 3, 4, 5, 6], [addr, val, t, True, off, rt, mid])
                # self._ui.scanRes_list.append([addr, val, t, True, off, rt, mid])
            matches = self.send_command(f'next L{MATCH_CNT}', 4096)
        self._ui.scanRes_tree.set_model(self._ui.scanRes_list)

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
    def process_status_checker(self):
        # non-blocking
        if not self._is_scanning and self._cpid:
            if misc. is_process_dead(self._cpid, self.is_debug):
                self._cpid = ''
                self._ui.show_error('Selected process is no longer available')
                self._ui.scanRes_list.clear()
        return not self._is_exiting and self._cpid

    def refresh_tree(self, new_cnt:int):
        if True:
            # Write to memory locked values in cheat list
            for i in self._ui.cheatList_list:
                if i[0] and i[5]: # locked and valid
                    self.write_value(i[2], i[3], i[4]) # addr, typestr, value
            # Update visible (and unlocked) cheat list rows
            rows = self.get_visible_rows(self._ui.cheatList_tree)
            for i in rows:
                lock, desc, addr, typestr, value, valid = self._ui.cheatList_list[i]
                if valid and not lock:
                    new_value = self.read_value(addr, typestr, value, typestr)
                    if new_value is None:
                        self._ui.cheatList_list[i] = (False, desc, addr, typestr, '??', False)
                    elif new_value != value and not self.cheatlist_editing:
                        self._ui.cheatList_list[i] = (lock, desc, addr, typestr, str(new_value), valid)
            # Update visible scanresult rows
            rows = self.get_visible_rows(self._ui.scanRes_tree)
            for i in rows:
                row = self._ui.scanRes_list[i]
                addr, cur_value, cur_type, valid = row[:4]
                if valid:
                    typestr = misc.TYPENAMES_S2G[cur_type.split(' ', 1)[0]]
                    new_value = self.read_value(addr, typestr, cur_value, typestr)
                    if new_value is not None:
                        row[1] = str(new_value)
                    else:
                        row[1] = '??'
                        row[3] = False

    def read_value(self, addr:str, in_type:str, val:int|str, out_type:str):
        size = misc.get_type_size(in_type, val)
        # ----
        buf,emsg = self.read_memory(addr, size)
        if  emsg:
            self._ui.show_error(emsg)
        #----
        return misc.bytes2value(out_type, buf)

    # addr could be int or str
    def write_value(self, addr:str, typestr:str, value:int|str):
        data = self.send_command(f'write {typestr} {addr} {value}')
        if 'error' in data:
            self._ui.show_error(data['error'])

    def exit(self, object, data=None):
        self.exit_cleanup()
        Gtk.main_quit()


if __name__ == '__main__':
    # Parse parameters
    args = misc.parse_env_args()
    # Init application
    gc_instance = GameConqueror( args )
    try:
        # Open socket and wait clients
        gc_instance.socket_server()
        # Init user interface
        gc_instance.create_window()
        # Start
        Gtk.main()
    finally:
        # Close socket
        gc_instance.close_server()
