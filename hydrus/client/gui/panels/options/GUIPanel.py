from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class GUIPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._main_gui_panel = ClientGUICommon.StaticBox( self, 'main window' )
        
        self._app_display_name = QW.QLineEdit( self._main_gui_panel )
        self._app_display_name.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is placed in every window title, with current version name. Rename if you want to personalise or differentiate.' ) )
        
        self._confirm_client_exit = QW.QCheckBox( self._main_gui_panel )
        
        self._activate_window_on_tag_search_page_activation = QW.QCheckBox( self._main_gui_panel )
        
        tt = 'Middle-clicking one or more tags in a taglist will cause the creation of a new search page for those tags. If you do this from the media viewer or a child manage tags dialog, do you want to switch immediately to the main gui?'
        
        self._activate_window_on_tag_search_page_activation.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
        
        self._always_show_iso_time = QW.QCheckBox( self._misc_panel )
        tt = 'In many places across the program (typically import status lists), the client will state a timestamp as "5 days ago". If you would prefer a standard ISO string, like "2018-03-01 12:40:23", check this.'
        self._always_show_iso_time.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._menu_choice_buttons_can_mouse_scroll = QW.QCheckBox( self._misc_panel )
        tt = 'Many buttons that produce menus when clicked are also "scrollable", so if you wheel your mouse over them, the selection will scroll through the underlying menu. If this is annoying for you, turn it off here!'
        self._menu_choice_buttons_can_mouse_scroll.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._use_native_menubar = QW.QCheckBox( self._misc_panel )
        tt = 'macOS and some Linux allows to embed the main GUI menubar into the OS. This can be buggy! Requires restart. Note that, in case this goes wrong, by default Ctrl+Shift+O should open this options dialog--confirm that before you try this!'
        self._use_native_menubar.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._human_bytes_sig_figs = ClientGUICommon.BetterSpinBox( self._misc_panel, min = 1, max = 6 )
        self._human_bytes_sig_figs.setToolTip( ClientGUIFunctions.WrapToolTip( 'When the program presents a bytes size above 1KB, like 21.3KB or 4.11GB, how many total digits do we want in the number? 2 or 3 is best.') )
        
        self._do_macos_debug_dialog_menus = QW.QCheckBox( self._misc_panel )
        self._do_macos_debug_dialog_menus.setToolTip( ClientGUIFunctions.WrapToolTip( 'There is a bug in Big Sur Qt regarding interacting with some menus in dialogs. The menus show but cannot be clicked. This shows the menu items in a debug dialog instead.' ) )
        
        self._use_qt_file_dialogs = QW.QCheckBox( self._misc_panel )
        self._use_qt_file_dialogs.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you get crashes opening file/directory dialogs, try this.' ) )
        
        self._remember_options_window_panel = QW.QCheckBox( self._misc_panel )
        self._remember_options_window_panel.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will cause the options window (this one) to reopen at the last panel you were looking at when it was closed.' ) )
        
        #
        
        frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
        
        self._disable_get_safe_position_test = QW.QCheckBox( self._misc_panel )
        self._disable_get_safe_position_test.setToolTip( ClientGUIFunctions.WrapToolTip( 'If your windows keep getting \'rescued\' despite being in a good location, try this.' ) )
        
        self._save_window_size_and_position_on_close = QW.QCheckBox( self._misc_panel )
        self._save_window_size_and_position_on_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you want to save media viewer size when closing the window in addition to when it gets resized/moved normally, check this box. Can be useful behaviour when using multiple open media viewers.' ) )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FRAME_LOCATIONS.ID, self._GetPrettyFrameLocationInfo, self._GetPrettyFrameLocationInfo )
        
        self._frame_locations_panel = ClientGUIListCtrl.BetterListCtrlPanel( frame_locations_panel )
        
        self._frame_locations = ClientGUIListCtrl.BetterListCtrlTreeView( self._frame_locations_panel, 15, model, activation_callback = self.EditFrameLocations )
        
        self._frame_locations_panel.SetListCtrl( self._frame_locations )
        
        self._frame_locations_panel.AddButton( 'edit', self.EditFrameLocations, enabled_only_on_single_selection = True )
        self._frame_locations_panel.AddSeparator()
        self._frame_locations_panel.AddButton( 'flip remember size', self._FlipRememberSize, enabled_only_on_selection = True )
        self._frame_locations_panel.AddButton( 'flip remember position', self._FlipRememberPosition, enabled_only_on_selection = True )
        self._frame_locations_panel.NewButtonRow()
        self._frame_locations_panel.AddButton( 'reset last size', self._ResetLastSize, enabled_only_on_selection = True )
        self._frame_locations_panel.AddButton( 'reset last position', self._ResetLastPosition, enabled_only_on_selection = True )
        
        #
        
        self._new_options = CG.client_controller.new_options
        
        self._app_display_name.setText( self._new_options.GetString( 'app_display_name' ) )
        
        self._confirm_client_exit.setChecked( HC.options[ 'confirm_client_exit' ] )
        
        self._activate_window_on_tag_search_page_activation.setChecked( self._new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' ) )
        
        self._always_show_iso_time.setChecked( self._new_options.GetBoolean( 'always_show_iso_time' ) )
        
        self._menu_choice_buttons_can_mouse_scroll.setChecked( self._new_options.GetBoolean( 'menu_choice_buttons_can_mouse_scroll' ) )
        
        self._use_native_menubar.setChecked( self._new_options.GetBoolean( 'use_native_menubar' ) )
        
        self._human_bytes_sig_figs.setValue( self._new_options.GetInteger( 'human_bytes_sig_figs' ) )
        
        self._do_macos_debug_dialog_menus.setChecked( self._new_options.GetBoolean( 'do_macos_debug_dialog_menus' ) )
        
        self._use_qt_file_dialogs.setChecked( self._new_options.GetBoolean( 'use_qt_file_dialogs' ) )
        
        self._remember_options_window_panel.setChecked( self._new_options.GetBoolean( 'remember_options_window_panel' ) )
        
        self._disable_get_safe_position_test.setChecked( self._new_options.GetBoolean( 'disable_get_safe_position_test' ) )
        
        self._save_window_size_and_position_on_close.setChecked( self._new_options.GetBoolean( 'save_window_size_and_position_on_close' ) )
        
        for ( name, info ) in self._new_options.GetFrameLocations():
            
            listctrl_data = QP.ListsToTuples( [ name ] + list( info ) )
            
            self._frame_locations.AddData( listctrl_data )
            
        
        self._frame_locations.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'Application display name: ', self._app_display_name ) )
        rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
        rows.append( ( 'Switch to main window when creating new file search page from media viewer: ', self._activate_window_on_tag_search_page_activation ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._main_gui_panel, rows )
        
        self._main_gui_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Prefer ISO time ("2018-03-01 12:40:23") to "5 days ago": ', self._always_show_iso_time ) )
        rows.append( ( 'Mouse wheel can "scroll" through menu buttons: ', self._menu_choice_buttons_can_mouse_scroll ) )
        rows.append( ( 'Use Native MenuBar (if available): ', self._use_native_menubar ) )
        rows.append( ( 'EXPERIMENTAL: Bytes strings >1KB pseudo significant figures: ', self._human_bytes_sig_figs ) )
        rows.append( ( 'BUGFIX: If on macOS, show dialog menus in a debug menu: ', self._do_macos_debug_dialog_menus ) )
        rows.append( ( 'ANTI-CRASH BUGFIX: Use Qt file/directory selection dialogs, rather than OS native: ', self._use_qt_file_dialogs ) )
        rows.append( ( 'Remember last open options panel in this window: ', self._remember_options_window_panel ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
        text += '\n'
        text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
        
        st = ClientGUICommon.BetterStaticText( frame_locations_panel, label = text )
        st.setWordWrap( True )
        
        frame_locations_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'BUGFIX: Disable off-screen window rescue: ', self._disable_get_safe_position_test ) )
        
        rows.append( ( 'Save media viewer window size and position on close: ', self._save_window_size_and_position_on_close ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        frame_locations_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        frame_locations_panel.Add( self._frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._main_gui_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._misc_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _FlipRememberPosition( self ):
        
        existing_datas = self._frame_locations.GetData( only_selected = True )
        
        replacement_tuples = []
        
        for listctrl_list in existing_datas:
            
            ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
            
            remember_position = not remember_position
            
            new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
            replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
            
        
        self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def _FlipRememberSize( self ):
        
        existing_datas = self._frame_locations.GetData( only_selected = True )
        
        replacement_tuples = []
        
        for listctrl_list in existing_datas:
            
            ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
            
            remember_size = not remember_size
            
            new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
            replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
            
        
        self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def _ResetLastPosition( self ):
        
        existing_datas = self._frame_locations.GetData( only_selected = True )
        
        replacement_tuples = []
        
        for listctrl_list in existing_datas:
            
            ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
            
            last_position = None
            
            new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
            replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
            
        
        self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def _ResetLastSize( self ):
        
        existing_datas = self._frame_locations.GetData( only_selected = True )
        
        replacement_tuples = []
        
        for listctrl_list in existing_datas:
            
            ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
            
            last_size = None
            
            new_listctrl_list = ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
            replacement_tuples.append( ( listctrl_list, new_listctrl_list ) )
            
        
        self._frame_locations.ReplaceDatas( replacement_tuples, sort_and_scroll = True )
        
    
    def _GetPrettyFrameLocationInfo( self, listctrl_list ):
        
        pretty_listctrl_list = []
        
        for item in listctrl_list:
            
            pretty_listctrl_list.append( str( item ) )
            
        
        return pretty_listctrl_list
        
    
    def EditFrameLocations( self ):
        
        data = self._frame_locations.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        listctrl_list = data
        
        title = 'set frame location information'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditFrameLocationPanel( dlg, listctrl_list )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_listctrl_list = panel.GetValue()
                
                self._frame_locations.ReplaceData( listctrl_list, new_listctrl_list, sort_and_scroll = True )
                
            
        
    
    def UpdateOptions( self ):
        
        HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.isChecked()
        
        self._new_options.SetBoolean( 'always_show_iso_time', self._always_show_iso_time.isChecked() )
        self._new_options.SetBoolean( 'menu_choice_buttons_can_mouse_scroll', self._menu_choice_buttons_can_mouse_scroll.isChecked() )
        self._new_options.SetBoolean( 'use_native_menubar', self._use_native_menubar.isChecked() )
        
        self._new_options.SetInteger( 'human_bytes_sig_figs', self._human_bytes_sig_figs.value() )
        
        self._new_options.SetBoolean( 'activate_window_on_tag_search_page_activation', self._activate_window_on_tag_search_page_activation.isChecked() )
        
        app_display_name = self._app_display_name.text()
        
        if app_display_name == '':
            
            app_display_name = 'hydrus client'
            
        
        self._new_options.SetString( 'app_display_name', app_display_name )
        
        self._new_options.SetBoolean( 'do_macos_debug_dialog_menus', self._do_macos_debug_dialog_menus.isChecked() )
        self._new_options.SetBoolean( 'use_qt_file_dialogs', self._use_qt_file_dialogs.isChecked() )
        self._new_options.SetBoolean( 'remember_options_window_panel', self._remember_options_window_panel.isChecked() )
        
        self._new_options.SetBoolean( 'disable_get_safe_position_test', self._disable_get_safe_position_test.isChecked() )
        self._new_options.SetBoolean( 'save_window_size_and_position_on_close', self._save_window_size_and_position_on_close.isChecked() )
        
        for listctrl_list in self._frame_locations.GetData():
            
            ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
            
            self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
        
    
