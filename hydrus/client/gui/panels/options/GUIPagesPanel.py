from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class GUIPagesPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        self._controls_panel = ClientGUICommon.StaticBox( self, 'preview window' )
        
        self._hide_preview = QW.QCheckBox( self._controls_panel )
        
        #
        
        self._opening_and_closing_panel = ClientGUICommon.StaticBox( self, 'opening and closing' )
        
        self._default_new_page_goes = ClientGUICommon.BetterChoice( self._opening_and_closing_panel )
        
        for value in [ CC.NEW_PAGE_GOES_FAR_LEFT, CC.NEW_PAGE_GOES_LEFT_OF_CURRENT, CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT, CC.NEW_PAGE_GOES_FAR_RIGHT ]:
            
            self._default_new_page_goes.addItem( CC.new_page_goes_string_lookup[ value ], value )
            
        
        self._show_all_my_files_on_page_chooser = QW.QCheckBox( self._opening_and_closing_panel )
        self._show_all_my_files_on_page_chooser.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will only show if you have more than one local file domain.' ) )
        self._show_all_my_files_on_page_chooser_at_top = QW.QCheckBox( self._opening_and_closing_panel )
        self._show_all_my_files_on_page_chooser_at_top.setToolTip( ClientGUIFunctions.WrapToolTip( 'Put "combined local file domains" at the top of the page chooser, to better see it if you have many local file domains.' ) )
        
        self._show_local_files_on_page_chooser = QW.QCheckBox( self._opening_and_closing_panel )
        self._show_local_files_on_page_chooser.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you do not know what this is, you do not want it!' ) )
        self._show_local_files_on_page_chooser_at_top = QW.QCheckBox( self._opening_and_closing_panel )
        self._show_local_files_on_page_chooser_at_top.setToolTip( ClientGUIFunctions.WrapToolTip( 'Put "hydrus local file storage" at the top of the page chooser (above "combined local file domains" as well, if it is present).' ) )
        
        self._close_page_focus_goes = ClientGUICommon.BetterChoice( self._opening_and_closing_panel )
        
        for value in [ CC.CLOSED_PAGE_FOCUS_GOES_LEFT, CC.CLOSED_PAGE_FOCUS_GOES_RIGHT ]:
            
            self._close_page_focus_goes.addItem( CC.closed_page_focus_string_lookup[ value ], value )
            
        
        self._confirm_all_page_closes = QW.QCheckBox( self._opening_and_closing_panel )
        self._confirm_all_page_closes.setToolTip( ClientGUIFunctions.WrapToolTip( 'With this, you will always be asked, even on single page closures of simple file pages.' ) )
        self._confirm_non_empty_downloader_page_close = QW.QCheckBox( self._opening_and_closing_panel )
        self._confirm_non_empty_downloader_page_close.setToolTip( ClientGUIFunctions.WrapToolTip( 'Helps to avoid accidental closes of big downloader pages.' ) )
        
        self._force_hide_page_signal_on_new_page = QW.QCheckBox( self._opening_and_closing_panel )
        
        self._force_hide_page_signal_on_new_page.setToolTip( ClientGUIFunctions.WrapToolTip( 'If your video still plays with sound in the preview viewer when you create a new page, please try this.' ) )
        
        #
        
        self._navigation_and_dnd = ClientGUICommon.StaticBox( self, 'navigation and drag-and-drop' )
        
        self._notebook_tab_alignment = ClientGUICommon.BetterChoice( self._navigation_and_dnd )
        
        for value in [ CC.DIRECTION_UP, CC.DIRECTION_LEFT, CC.DIRECTION_RIGHT, CC.DIRECTION_DOWN ]:
            
            self._notebook_tab_alignment.addItem( CC.directions_alignment_string_lookup[ value ], value )
            
        
        self._set_search_focus_on_page_change = QW.QCheckBox( self._navigation_and_dnd )
        self._set_search_focus_on_page_change.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set it so whenever you switch between pages, the keyboard focus immediately moves to the tag autocomplete or search text input.' ) )
        
        self._page_drop_chase_normally = QW.QCheckBox( self._navigation_and_dnd )
        self._page_drop_chase_normally.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drop a page to a new location, should hydrus follow the page selection to the new location?' ) )
        self._page_drop_chase_with_shift = QW.QCheckBox( self._navigation_and_dnd )
        self._page_drop_chase_with_shift.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drop a page to a new location with shift held down, should hydrus follow the page selection to the new location?' ) )
        
        self._page_drag_change_tab_normally = QW.QCheckBox( self._navigation_and_dnd )
        self._page_drag_change_tab_normally.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drag media or a page to a new location, should hydrus navigate and change tabs as you move the mouse around?' ) )
        self._page_drag_change_tab_with_shift = QW.QCheckBox( self._navigation_and_dnd )
        self._page_drag_change_tab_with_shift.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you drag media or a page to a new location with shift held down, should hydrus navigate and change tabs as you move the mouse around?' ) )
        
        self._wheel_scrolls_tab_bar = QW.QCheckBox( self._navigation_and_dnd )
        self._wheel_scrolls_tab_bar.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you scroll your mouse wheel over some tabs, the normal behaviour is to change the tab selection. If you often have overloaded tab bars, you might like to have the mouse wheel actually scroll the tab bar itself.' ) )
        
        self._disable_page_tab_dnd = QW.QCheckBox( self._navigation_and_dnd )
        
        self._disable_page_tab_dnd.setToolTip( ClientGUIFunctions.WrapToolTip( 'Trying to debug some client hangs!' ) )
        
        #
        
        self._page_names_panel = ClientGUICommon.StaticBox( self, 'page tab names' )
        
        self._max_page_name_chars = ClientGUICommon.BetterSpinBox( self._page_names_panel, min=1, max=256 )
        self._elide_page_tab_names = QW.QCheckBox( self._page_names_panel )
        
        self._page_file_count_display = ClientGUICommon.BetterChoice( self._page_names_panel )
        
        for display_type in ( CC.PAGE_FILE_COUNT_DISPLAY_ALL, CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS, CC.PAGE_FILE_COUNT_DISPLAY_NONE, CC.PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO ):
            
            self._page_file_count_display.addItem( CC.page_file_count_display_string_lookup[ display_type ], display_type )
            
        
        self._import_page_progress_display = QW.QCheckBox( self._page_names_panel )
        
        self._rename_page_of_pages_on_pick_new = QW.QCheckBox( self._page_names_panel )
        self._rename_page_of_pages_on_pick_new.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you create a new \'page of pages\' from the new page picker, should it automatically prompt you to give it a name other than \'pages\'?' ) )
        self._rename_page_of_pages_on_send = QW.QCheckBox( self._page_names_panel )
        self._rename_page_of_pages_on_send.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you \'send this page down\' or \'send pages to the right\' to a new page of pages, should it also automatically prompt you to rename it?' ) )
        
        #
        
        self._show_all_my_files_on_page_chooser.setChecked( self._new_options.GetBoolean( 'show_all_my_files_on_page_chooser' ) )
        self._show_all_my_files_on_page_chooser_at_top.setChecked( self._new_options.GetBoolean( 'show_all_my_files_on_page_chooser_at_top' ) )
        self._show_local_files_on_page_chooser.setChecked( self._new_options.GetBoolean( 'show_local_files_on_page_chooser' ) )
        self._show_local_files_on_page_chooser_at_top.setChecked( self._new_options.GetBoolean( 'show_local_files_on_page_chooser_at_top' ) )
        
        self._confirm_all_page_closes.setChecked( self._new_options.GetBoolean( 'confirm_all_page_closes' ) )
        self._confirm_non_empty_downloader_page_close.setChecked( self._new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) )
        
        self._default_new_page_goes.SetValue( self._new_options.GetInteger( 'default_new_page_goes' ) )
        self._close_page_focus_goes.SetValue( self._new_options.GetInteger( 'close_page_focus_goes' ) )
        
        self._notebook_tab_alignment.SetValue( self._new_options.GetInteger( 'notebook_tab_alignment' ) )
        
        self._max_page_name_chars.setValue( self._new_options.GetInteger( 'max_page_name_chars' ) )
        
        self._elide_page_tab_names.setChecked( self._new_options.GetBoolean( 'elide_page_tab_names' ) )
        
        self._page_file_count_display.SetValue( self._new_options.GetInteger( 'page_file_count_display' ) )
        
        self._import_page_progress_display.setChecked( self._new_options.GetBoolean( 'import_page_progress_display' ) )
        
        self._rename_page_of_pages_on_pick_new.setChecked( self._new_options.GetBoolean( 'rename_page_of_pages_on_pick_new' ) )
        self._rename_page_of_pages_on_send.setChecked( self._new_options.GetBoolean( 'rename_page_of_pages_on_send' ) )
        
        self._page_drop_chase_normally.setChecked( self._new_options.GetBoolean( 'page_drop_chase_normally' ) )
        self._page_drop_chase_with_shift.setChecked( self._new_options.GetBoolean( 'page_drop_chase_with_shift' ) )
        self._page_drag_change_tab_normally.setChecked( self._new_options.GetBoolean( 'page_drag_change_tab_normally' ) )
        self._page_drag_change_tab_with_shift.setChecked( self._new_options.GetBoolean( 'page_drag_change_tab_with_shift' ) )
        
        self._wheel_scrolls_tab_bar.setChecked( self._new_options.GetBoolean( 'wheel_scrolls_tab_bar' ) )
        
        self._disable_page_tab_dnd.setChecked( self._new_options.GetBoolean( 'disable_page_tab_dnd' ) )
        
        self._force_hide_page_signal_on_new_page.setChecked( self._new_options.GetBoolean( 'force_hide_page_signal_on_new_page' ) )
        
        self._set_search_focus_on_page_change.setChecked( self._new_options.GetBoolean( 'set_search_focus_on_page_change' ) )
        
        self._hide_preview.setChecked( HC.options[ 'hide_preview' ] )
        
        #
        
        rows = []
        
        rows.append( ( 'Put new page tabs on: ', self._default_new_page_goes ) )
        rows.append( ( 'In new page chooser, show "combined local file domains" if appropriate:', self._show_all_my_files_on_page_chooser ) )
        rows.append( ( '  Put it at the top:', self._show_all_my_files_on_page_chooser_at_top ) )
        rows.append( ( 'In new page chooser, show "hydrus local file storage":', self._show_local_files_on_page_chooser ) )
        rows.append( ( '  Put it at the top:', self._show_local_files_on_page_chooser_at_top ) )
        rows.append( ( 'When closing the current tab, move focus: ', self._close_page_focus_goes ) )
        rows.append( ( 'Confirm when closing any page: ', self._confirm_all_page_closes ) )
        rows.append( ( 'Confirm when closing a non-empty importer page: ', self._confirm_non_empty_downloader_page_close ) )
        rows.append( ( 'BUGFIX: Force \'hide page\' signal when creating a new page: ', self._force_hide_page_signal_on_new_page ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._opening_and_closing_panel, rows )
        
        self._opening_and_closing_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Notebook tab alignment: ', self._notebook_tab_alignment ) )
        rows.append( ( 'When switching to pages, move keyboard focus to any text input field: ', self._set_search_focus_on_page_change ) )
        rows.append( ( 'Selection chases dropped page after drag and drop: ', self._page_drop_chase_normally ) )
        rows.append( ( '  With shift held down?: ', self._page_drop_chase_with_shift ) )
        rows.append( ( 'Navigate tabs during drag and drop: ', self._page_drag_change_tab_normally ) )
        rows.append( ( '  With shift held down?: ', self._page_drag_change_tab_with_shift ) )
        rows.append( ( 'EXPERIMENTAL: Mouse wheel scrolls tab bar, not page selection: ', self._wheel_scrolls_tab_bar ) )
        rows.append( ( 'BUGFIX: Disable all page tab drag and drop: ', self._disable_page_tab_dnd ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._navigation_and_dnd, rows )
        
        self._navigation_and_dnd.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Max characters to display in a page name: ', self._max_page_name_chars ) )
        rows.append( ( 'When there are too many tabs to fit, \'...\' elide their names so they fit: ', self._elide_page_tab_names ) )
        rows.append( ( 'Show page file count after its name: ', self._page_file_count_display ) )
        rows.append( ( 'Show import page x/y progress after its name: ', self._import_page_progress_display ) )
        rows.append( ( 'Automatically prompt to rename new \'page of pages\' after creation: ', self._rename_page_of_pages_on_pick_new ) )
        rows.append( ( '  Also automatically prompt when sending some pages to one: ', self._rename_page_of_pages_on_send ) )
        
        page_names_gridbox = ClientGUICommon.WrapInGrid( self._page_names_panel, rows )
        
        label = 'If you have enough pages in a row, left/right arrows will appear to navigate them back and forth.'
        label += '\n'
        label += 'Due to an unfortunate Qt issue, the tab bar will scroll so the current tab is right-most visible whenever you change page or a page is renamed. This is very annoying to live with.'
        label += '\n'
        label += 'Therefore, do not put import pages in a long row of tabs, as it will reset scroll position on every progress update. Try to avoid long rows in general.'
        label += '\n'
        label += 'Just make some nested \'page of pages\' so they are not all in the same row.'
        
        st = ClientGUICommon.BetterStaticText( self._page_names_panel, label )
        
        st.setToolTip( ClientGUIFunctions.WrapToolTip( 'https://bugreports.qt.io/browse/QTBUG-45381' ) )
        
        st.setWordWrap( True )
        
        self._page_names_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._page_names_panel.Add( page_names_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Hide the bottom-left preview window: ', self._hide_preview ) )
        gridbox = ClientGUICommon.WrapInGrid( self._controls_panel, rows )
        
        self._controls_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._controls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._opening_and_closing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._navigation_and_dnd, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._page_names_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'notebook_tab_alignment', self._notebook_tab_alignment.GetValue() )
        
        self._new_options.SetBoolean( 'show_all_my_files_on_page_chooser', self._show_all_my_files_on_page_chooser.isChecked() )
        self._new_options.SetBoolean( 'show_all_my_files_on_page_chooser_at_top', self._show_all_my_files_on_page_chooser_at_top.isChecked() )
        self._new_options.SetBoolean( 'show_local_files_on_page_chooser', self._show_local_files_on_page_chooser.isChecked() )
        self._new_options.SetBoolean( 'show_local_files_on_page_chooser_at_top', self._show_local_files_on_page_chooser_at_top.isChecked() )
        
        self._new_options.SetBoolean( 'confirm_all_page_closes', self._confirm_all_page_closes.isChecked() )
        self._new_options.SetBoolean( 'confirm_non_empty_downloader_page_close', self._confirm_non_empty_downloader_page_close.isChecked() )
        
        self._new_options.SetInteger( 'default_new_page_goes', self._default_new_page_goes.GetValue() )
        self._new_options.SetInteger( 'close_page_focus_goes', self._close_page_focus_goes.GetValue() )
        
        self._new_options.SetInteger( 'max_page_name_chars', self._max_page_name_chars.value() )
        
        self._new_options.SetBoolean( 'elide_page_tab_names', self._elide_page_tab_names.isChecked() )
        
        self._new_options.SetInteger( 'page_file_count_display', self._page_file_count_display.GetValue() )
        self._new_options.SetBoolean( 'import_page_progress_display', self._import_page_progress_display.isChecked() )
        self._new_options.SetBoolean( 'rename_page_of_pages_on_pick_new', self._rename_page_of_pages_on_pick_new.isChecked() )
        self._new_options.SetBoolean( 'rename_page_of_pages_on_send', self._rename_page_of_pages_on_send.isChecked() )
        
        self._new_options.SetBoolean( 'disable_page_tab_dnd', self._disable_page_tab_dnd.isChecked() )
        self._new_options.SetBoolean( 'force_hide_page_signal_on_new_page', self._force_hide_page_signal_on_new_page.isChecked() )
        
        self._new_options.SetBoolean( 'page_drop_chase_normally', self._page_drop_chase_normally.isChecked() )
        self._new_options.SetBoolean( 'page_drop_chase_with_shift', self._page_drop_chase_with_shift.isChecked() )
        self._new_options.SetBoolean( 'page_drag_change_tab_normally', self._page_drag_change_tab_normally.isChecked() )
        self._new_options.SetBoolean( 'page_drag_change_tab_with_shift', self._page_drag_change_tab_with_shift.isChecked() )
        
        self._new_options.SetBoolean( 'wheel_scrolls_tab_bar', self._wheel_scrolls_tab_bar.isChecked() )
        
        self._new_options.SetBoolean( 'set_search_focus_on_page_change', self._set_search_focus_on_page_change.isChecked() )
        
        HC.options[ 'hide_preview' ] = self._hide_preview.isChecked()
        
    
