from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class CommandPalettePanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        self._new_options = new_options
        
        super().__init__( parent )
        
        self._command_palette_panel = ClientGUICommon.StaticBox( self, 'command palette' )
        
        self._command_palette_num_chars_for_results_threshold = ClientGUICommon.BetterSpinBox( self._command_palette_panel, initial = 1, min = 1, max = 64 )
        
        self._command_palette_show_page_of_pages = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_page_of_pages.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show "page of pages" as selectable page results. This will focus the page, and whatever sub-page it previously focused (including none, if it has no child pages).' ) )
        
        self._command_palette_initially_show_all_pages = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_initially_show_all_pages.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, the command palette will not load any open page results until you start typing. This can help with performance with larger sessions.' ) )
        
        self._command_palette_limit_page_results = ClientGUICommon.NoneableSpinCtrl( self._command_palette_panel, default_int = 10, min = 1 )
        self._command_palette_limit_page_results.setToolTip( ClientGUIFunctions.WrapToolTip( 'The maximum number of page results to show before requiring more typing to filter them down.' ) )
        
        self._command_palette_initially_show_history = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_initially_show_history.setToolTip( ClientGUIFunctions.WrapToolTip( 'By default, the command palette shows all your pages when opened. If you enable this, it will also show your page navigation history, which is often more useful for quick switching.' ) )
        
        self._command_palette_limit_history_results = ClientGUICommon.NoneableSpinCtrl( self._command_palette_panel, default_int = 10, min = 1 )
        self._command_palette_limit_history_results.setToolTip( ClientGUIFunctions.WrapToolTip( 'The maximum number of page history results to show before requiring more typing to filter them down.' ) )
        
        self._command_palette_initially_show_favourite_searches = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_initially_show_favourite_searches.setToolTip( ClientGUIFunctions.WrapToolTip( 'If checked, your favourite searches will also show as results when the command palette before typing anything.' ) )
        self._command_palette_fav_searches_open_new_page = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_fav_searches_open_new_page.setToolTip( ClientGUIFunctions.WrapToolTip( 'If unchecked, triggering a favourite search from the palette will overwrite the current page\'s search.' ) )
        
        self._command_palette_limit_favourite_searches_results = ClientGUICommon.NoneableSpinCtrl( self._command_palette_panel, default_int = 10, min = 1 )
        self._command_palette_limit_favourite_searches_results.setToolTip( ClientGUIFunctions.WrapToolTip( 'The maximum number of favourite search results to show before requiring more typing to filter them down.' ) )
        
        self._command_palette_show_main_menu = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_main_menu.setToolTip( ClientGUIFunctions.WrapToolTip(  'Show the main gui window\'s menubar actions. This checkbox overrides its presence in the provider order box.' ) )
        
        self._command_palette_show_media_menu = QW.QCheckBox( self._command_palette_panel )
        self._command_palette_show_media_menu.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show the actions for the thumbnail menu on the current media page. Be careful with this, it basically just shows everything with slightly ugly labels..  This checkbox overrides its presence in the provider order box.' ) )
        
        command_palette_provider_order = ClientGUICommon.StaticBox( self._command_palette_panel, 'search provider order' )
        self._command_palette_provider_order = ClientGUIListBoxes.QueueListBox( command_palette_provider_order, 6, self._GetPrettyProviderName, self._AddMissingSearchProviderDialog )
        self._command_palette_provider_order.AddDatas( self._new_options.GetIntegerList( 'command_palette_provider_order' ) )
        
        #
        
        self._command_palette_num_chars_for_results_threshold.setValue( self._new_options.GetInteger( 'command_palette_num_chars_for_results_threshold' ) )
        self._command_palette_show_page_of_pages.setChecked( self._new_options.GetBoolean( 'command_palette_show_page_of_pages' ) )
        self._command_palette_initially_show_all_pages.setChecked( self._new_options.GetBoolean( 'command_palette_initially_show_all_pages' ) )
        self._command_palette_limit_page_results.SetValue( self._new_options.GetNoneableInteger( 'command_palette_limit_page_results' ) )
        self._command_palette_initially_show_history.setChecked( self._new_options.GetBoolean( 'command_palette_initially_show_history' ) )
        self._command_palette_limit_history_results.SetValue( self._new_options.GetNoneableInteger( 'command_palette_limit_history_results' ) )
        self._command_palette_initially_show_favourite_searches.setChecked( self._new_options.GetBoolean( 'command_palette_initially_show_favourite_searches' ) )
        self._command_palette_fav_searches_open_new_page.setChecked( self._new_options.GetBoolean( 'command_palette_fav_searches_open_new_page' ))
        self._command_palette_limit_favourite_searches_results.SetValue( self._new_options.GetNoneableInteger( 'command_palette_limit_favourite_searches_results' ) )
        
        self._command_palette_show_main_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_main_menu' ) )
        self._command_palette_show_media_menu.setChecked( self._new_options.GetBoolean( 'command_palette_show_media_menu' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Initially show all page results:', self._command_palette_initially_show_all_pages ) )
        rows.append( ( 'Initially show page history results:', self._command_palette_initially_show_history ) )
        rows.append( ( 'Initially show favourite search results:', self._command_palette_initially_show_favourite_searches ) )
        rows.append( ( 'Start searching when this many characters have been typed:', self._command_palette_num_chars_for_results_threshold ) )
        rows.append( ( 'Max page results to show:', self._command_palette_limit_page_results ) )
        rows.append( ( 'Max page history to show:', self._command_palette_limit_history_results ) )
        rows.append( ( 'Max favourite searches to show:', self._command_palette_limit_favourite_searches_results ) )
        rows.append( ( 'Include "page of pages" page results:', self._command_palette_show_page_of_pages ) )
        rows.append( ( 'Open favourite searches in a new page:', self._command_palette_fav_searches_open_new_page ) )
        rows.append( ( 'ADVANCED: Search main menubar:', self._command_palette_show_main_menu ) )
        rows.append( ( 'ADVANCED: Search media menu:', self._command_palette_show_media_menu ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        text = 'By default, you can hit Ctrl+P to bring up a Command Palette. It initially shows your pages for quick navigation, but it can search for more.'
        
        st = ClientGUICommon.BetterStaticText( self._command_palette_panel, text )
        st.setWordWrap( True )
        
        self._command_palette_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._command_palette_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        text = 'You can re-order or remove search providers from the palette here. Any removed providers can be re-added.'
        
        st = ClientGUICommon.BetterStaticText( self._command_palette_panel, text )
        st.setWordWrap( True )
        
        command_palette_provider_order.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        command_palette_provider_order.Add( self._command_palette_provider_order, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._command_palette_panel.Add( command_palette_provider_order, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._command_palette_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def _AddMissingSearchProviderDialog( self ):
        
        present_providers = self._command_palette_provider_order.GetData()
        
        if len( present_providers ) < len ( CC.command_palette_provider_str_lookup ):
            
            try:
                
                choice_tuples = [ ( value, key, value ) for key, value in CC.command_palette_provider_str_lookup.items() if key not in present_providers ]
                
                if not choice_tuples:
                    
                    raise HydrusExceptions.VetoException()
                    
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                add_provider = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Select a provider to add:', choice_tuples )
                
                if add_provider is not None:
                    
                    return( add_provider )
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            except HydrusExceptions.CancelledException:
                
                raise HydrusExceptions.VetoException()
            
        else:
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _GetPrettyProviderName( self, provider: int ) -> str:
        
        if provider is not None:
            
            return CC.command_palette_provider_str_lookup[ provider ]
            
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'command_palette_num_chars_for_results_threshold', self._command_palette_num_chars_for_results_threshold.value() )
        self._new_options.SetBoolean( 'command_palette_show_page_of_pages', self._command_palette_show_page_of_pages.isChecked() )
        self._new_options.SetBoolean( 'command_palette_initially_show_all_pages', self._command_palette_initially_show_all_pages.isChecked() )
        self._new_options.SetNoneableInteger( 'command_palette_limit_page_results', self._command_palette_limit_page_results.GetValue() )
        self._new_options.SetBoolean( 'command_palette_initially_show_history', self._command_palette_initially_show_history.isChecked() )
        self._new_options.SetNoneableInteger( 'command_palette_limit_history_results', self._command_palette_limit_history_results.GetValue() )
        self._new_options.SetBoolean( 'command_palette_initially_show_favourite_searches', self._command_palette_initially_show_favourite_searches.isChecked() )
        self._new_options.SetBoolean( 'command_palette_fav_searches_open_new_page', self._command_palette_fav_searches_open_new_page.isChecked() )
        self._new_options.SetNoneableInteger( 'command_palette_limit_favourite_searches_results', self._command_palette_limit_favourite_searches_results.GetValue() )
        self._new_options.SetBoolean( 'command_palette_show_main_menu', self._command_palette_show_main_menu.isChecked() )
        self._new_options.SetBoolean( 'command_palette_show_media_menu', self._command_palette_show_media_menu.isChecked() )
        self._new_options.SetIntegerList( 'command_palette_provider_order', self._command_palette_provider_order.GetData() )
        
    
