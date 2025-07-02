import collections
import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUITextInput

class EditTagFilterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    TEST_RESULT_DEFAULT = 'Enter a tag here to test if it passes the current filter:'
    TEST_RESULT_BLACKLIST_DEFAULT = 'Enter a tag here to test if it passes the blacklist (siblings tested, unnamespaced rules match namespaced tags):'
    
    def __init__( self, parent, tag_filter, only_show_blacklist = False, namespaces = None, message = None, read_only = False ):
        
        super().__init__( parent )
        
        self._only_show_blacklist = only_show_blacklist
        self._namespaces = namespaces
        self._read_only = read_only
        
        self._wildcard_replacements = {}
        
        self._wildcard_replacements[ '*' ] = ''
        self._wildcard_replacements[ '*:' ] = ':'
        self._wildcard_replacements[ '*:*' ] = ':'
        
        #
        
        self._favourites_panel = ClientGUICommon.StaticBox( self, 'favourites' )
        
        self._import_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'import', self._ImportFavourite )
        self._export_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'export', self._ExportFavourite )
        self._load_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'load', self._LoadFavourite )
        self._save_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'save', self._SaveFavourite )
        self._delete_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'delete', self._DeleteFavourite )
        
        #
        
        self._filter_panel = ClientGUICommon.StaticBox( self, 'filter' )
        
        self._show_all_panels_button = ClientGUICommon.BetterButton( self._filter_panel, 'show other panels', self._ShowAllPanels )
        self._show_all_panels_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'This shows the whitelist and advanced panels, in case you want to craft a clever blacklist with \'except\' rules.' ) )
        
        show_the_button = self._only_show_blacklist and CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        self._show_all_panels_button.setVisible( show_the_button )
        
        #
        
        self._notebook = ClientGUICommon.BetterNotebook( self._filter_panel )
        
        #
        
        self._advanced_panel = self._InitAdvancedPanel()
        
        self._whitelist_panel = self._InitWhitelistPanel()
        self._blacklist_panel = self._InitBlacklistPanel()
        
        #
        
        if self._only_show_blacklist:
            
            self._whitelist_panel.setVisible( False )
            self._notebook.addTab( self._blacklist_panel, 'blacklist' )
            self._advanced_panel.setVisible( False )
            
        else:
            
            self._notebook.addTab( self._whitelist_panel, 'whitelist' )
            self._notebook.addTab( self._blacklist_panel, 'blacklist' )
            self._notebook.addTab( self._advanced_panel, 'advanced' )
            
        
        #
        
        self._redundant_st = ClientGUICommon.BetterStaticText( self._filter_panel, '', ellipsize_end = True )
        self._redundant_st.setVisible( False )
        
        self._current_filter_st = ClientGUICommon.BetterStaticText( self._filter_panel, 'current filter: ', ellipsize_end = True )
        
        #
        
        self._test_panel = ClientGUICommon.StaticBox( self, 'testing', can_expand = True, start_expanded = True )
        
        self._test_result_st = ClientGUICommon.BetterStaticText( self._test_panel, self.TEST_RESULT_DEFAULT )
        self._test_result_st.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignRight )
        
        self._test_result_st.setWordWrap( True )
        
        self._test_input = QW.QPlainTextEdit( self._test_panel )
        
        #
        
        vbox = QP.VBoxLayout()
        
        if not self._read_only:
            
            help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
            
            help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
            
            QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
            
        
        if message is not None:
            
            message_panel = ClientGUICommon.StaticBox( self, 'explanation', can_expand = True, start_expanded = True )
            
            st = ClientGUICommon.BetterStaticText( message_panel, message )
            
            st.setWordWrap( True )
            
            message_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, message_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        if self._read_only:
            
            self._import_favourite.hide()
            self._load_favourite.hide()
            
        
        QP.AddToLayout( hbox, self._import_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._export_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._load_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._save_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._delete_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._favourites_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        QP.AddToLayout( vbox, self._favourites_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._filter_panel.Add( self._show_all_panels_button, CC.FLAGS_ON_RIGHT )
        
        label = 'Click the "(un)namespaced" checkboxes to allow/disallow those tags.\nType "namespace:" to manually input a namespace that is not in the list.'
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._filter_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._filter_panel.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._filter_panel.Add( self._redundant_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filter_panel.Add( self._current_filter_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._filter_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        test_text_vbox = QP.VBoxLayout()
        
        if self._only_show_blacklist:
            
            message = 'This is a fixed blacklist. It will apply rules against all test tag siblings and apply unnamespaced rules to namespaced test tags.'
            
            st = ClientGUICommon.BetterStaticText( self._test_input, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( test_text_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( test_text_vbox, self._test_result_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, test_text_vbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._test_input, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._test_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._test_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._advanced_blacklist.listBoxChanged.connect( self._UpdateStatus )
        self._advanced_whitelist.listBoxChanged.connect( self._UpdateStatus )
        self._simple_whitelist_global_checkboxes.clicked.connect( self.EventSimpleWhitelistGlobalCheck )
        self._simple_whitelist_namespace_checkboxes.clicked.connect( self.EventSimpleWhitelistNamespaceCheck )
        self._simple_blacklist_global_checkboxes.clicked.connect( self.EventSimpleBlacklistGlobalCheck )
        self._simple_blacklist_namespace_checkboxes.clicked.connect( self.EventSimpleBlacklistNamespaceCheck )
        
        self._test_input.textChanged.connect( self._UpdateTest )
        
        self.SetValue( tag_filter )
        
    
    def _AdvancedAddBlacklistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        self._AdvancedEnterBlacklistMultiple( tag_slices, only_add = True )
        
    
    def _AdvancedAddWhitelistMultiple( self, tag_slices ):
        
        self._AdvancedEnterWhitelistMultiple( tag_slices, only_add = True )
        
    
    def _AdvancedBlacklistEverything( self ):
        
        self._advanced_blacklist.SetTagSlices( [] )
        
        self._advanced_whitelist.RemoveTagSlices( ( '', ':' ) )
        
        self._advanced_blacklist.AddTagSlices( ( '', ':' ) )
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteBlacklistButton( self ):
        
        selected_tag_slices = self._advanced_blacklist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._advanced_blacklist.RemoveTagSlices( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteWhitelistButton( self ):
        
        selected_tag_slices = self._advanced_whitelist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._advanced_whitelist.RemoveTagSlices( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedEnterBlacklistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        tag_slices = [ self._CleanTagSliceInput( tag_slice ) for tag_slice in tag_slices ]
        
        tag_slices = HydrusData.DedupeList( tag_slices )
        
        current_blacklist = set( self._advanced_blacklist.GetTagSlices() )
        
        to_remove = set( tag_slices ).intersection( current_blacklist )
        
        to_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in to_remove ]
        
        if len( to_remove ) > 0 and not only_add:
            
            self._advanced_blacklist.RemoveTagSlices( to_remove )
            
        
        if len( to_add ) > 0 and not only_remove:
            
            self._advanced_whitelist.RemoveTagSlices( to_add )
            
            already_blocked = [ tag_slice for tag_slice in to_add if self._CurrentlyBlocked( tag_slice ) ]
            
            if len( already_blocked ) > 0:
                
                if len( already_blocked ) == 1:
                    
                    message = f'{HydrusTags.ConvertTagSliceToPrettyString( already_blocked[0] )} is already blocked by a broader rule!'
                    
                else:
                    
                    separator = '\n' if len( already_blocked ) < 5 else ', '
                    
                    message = 'The tags\n\n' + separator.join( [ HydrusTags.ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in already_blocked ] ) + '\n\nare already blocked by a broader rule!'
                    
                
                self._ShowRedundantError( message )
                
            
            self._advanced_blacklist.AddTagSlices( to_add )
            
        
        self._UpdateStatus()
        
    
    def _AdvancedEnterWhitelistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        tag_slices = [ self._CleanTagSliceInput( tag_slice ) for tag_slice in tag_slices ]
        
        current_whitelist = set( self._advanced_whitelist.GetTagSlices() )
        
        to_remove = set( tag_slices ).intersection( current_whitelist )
        
        if len( to_remove ) > 0 and not only_add:
            
            self._advanced_whitelist.RemoveTagSlices( to_remove )
            
        
        to_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in to_remove ]
        
        if len( to_add ) > 0 and not only_remove:
            
            self._advanced_blacklist.RemoveTagSlices( to_add )
            
            already_permitted = [ tag_slice for tag_slice in to_add if tag_slice not in ( '', ':' ) and not self._CurrentlyBlocked( tag_slice ) ]
            
            if len( already_permitted ) > 0:
                
                if len( already_permitted ) == 1:
                    
                    message = f'{HydrusTags.ConvertTagSliceToPrettyString( to_add[0] )} is already permitted by a broader rule!'
                    
                else:
                    
                    separator = '\n' if len( already_permitted ) < 5 else ', '
                    
                    message = 'The tags\n\n' + separator.join( [ HydrusTags.ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in already_permitted ] ) + '\n\nare already permitted by a broader rule!'
                    
                
                self._ShowRedundantError( message )
                
            
            tag_slices_to_actually_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in ( '', ':' ) ]
            
            # we don't say 'except for' for (un)namespaced
            self._advanced_whitelist.AddTagSlices( tag_slices_to_actually_add )
            
        
        self._UpdateStatus()
        
    
    def _CleanTagSliceInput( self, tag_slice ):
        
        tag_slice = tag_slice.lower().strip()
        
        while '**' in tag_slice:
            
            tag_slice = tag_slice.replace( '**', '*' )
            
        
        if tag_slice in self._wildcard_replacements:
            
            tag_slice = self._wildcard_replacements[ tag_slice ]
            
        
        if ':' in tag_slice:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag_slice )
            
            if subtag == '*':
                
                tag_slice = '{}:'.format( namespace )
                
            
        
        return tag_slice
        
    
    def _CurrentlyBlocked( self, tag_slice ):
        
        if tag_slice in ( '', ':' ):
            
            test_slices = { tag_slice }
            
        elif HydrusTags.IsNamespaceTagSlice( tag_slice ):
            
            test_slices = { ':', tag_slice }
            
        elif ':' in tag_slice:
            
            ( ns, st ) = HydrusTags.SplitTag( tag_slice )
            
            test_slices = { ':', ns + ':', tag_slice }
            
        else:
            
            test_slices = { '', tag_slice }
            
        
        blacklist = set( self._advanced_blacklist.GetTagSlices() )
        
        return not blacklist.isdisjoint( test_slices )
        
    
    def _DeleteFavourite( self ):
        
        def do_it( name ):
            
            names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
            
            if name in names_to_tag_filters:
                
                message = 'Delete "{}"?'.format( name )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
                del names_to_tag_filters[ name ]
                
                CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
            
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'delete {}'.format( name ), do_it, name )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ExportFavourite( self ):
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'this tag filter', 'export this tag filter', CG.client_controller.pub, 'clipboard', 'text', self.GetValue().DumpToString() )
        
        if len( names_to_tag_filters ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'export {}'.format( name ), CG.client_controller.pub, 'clipboard', 'text', tag_filter.DumpToString() )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _GetWhiteBlacklistsPossible( self ):
        
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        
        blacklist_is_only_simples = set( blacklist_tag_slices ).issubset( { '', ':' } )
        
        nothing_is_whitelisted = len( whitelist_tag_slices ) == 0
        
        whitelist_possible = blacklist_is_only_simples
        blacklist_possible = nothing_is_whitelisted
        
        return ( whitelist_possible, blacklist_possible )
        
    
    def _ImportFavourite( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Tag Filter object', e )
            
            return
            
        
        if not isinstance( obj, HydrusTags.TagFilter ):
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'That object was not a Tag Filter! It seemed to be a "{type(obj)}".' )
            
            return
            
        
        tag_filter = obj
        
        tag_filter.CleanRules()
        
        try:
            
            message = 'Enter a name for the favourite.'
            
            name = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        if name in names_to_tag_filters:
            
            message = '"{}" already exists! Overwrite?'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        names_to_tag_filters[ name ] = tag_filter
        
        CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
        
        self.SetValue( tag_filter )
        
    
    def _InitAdvancedPanel( self ):
        
        advanced_panel = QW.QWidget( self._notebook )
        
        #
        
        self._advanced_blacklist_panel = ClientGUICommon.StaticBox( advanced_panel, 'exclude these' )
        
        self._advanced_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( self._advanced_blacklist_panel, read_only = self._read_only )
        
        self._advanced_blacklist_input = ClientGUITextInput.TextAndPasteCtrl( self._advanced_blacklist_panel, self._AdvancedAddBlacklistMultiple, allow_empty_input = True )
        
        delete_blacklist_button = ClientGUICommon.BetterButton( self._advanced_blacklist_panel, 'delete', self._AdvancedDeleteBlacklistButton )
        blacklist_everything_button = ClientGUICommon.BetterButton( self._advanced_blacklist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        self._advanced_whitelist_panel = ClientGUICommon.StaticBox( advanced_panel, 'except for these' )
        
        self._advanced_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( self._advanced_whitelist_panel, read_only = self._read_only )
        
        self._advanced_whitelist_input = ClientGUITextInput.TextAndPasteCtrl( self._advanced_whitelist_panel, self._AdvancedAddWhitelistMultiple, allow_empty_input = True )
        
        delete_whitelist_button = ClientGUICommon.BetterButton( self._advanced_whitelist_panel, 'delete', self._AdvancedDeleteWhitelistButton )
        
        #
        
        if self._read_only:
            
            self._advanced_blacklist_input.hide()
            delete_blacklist_button.hide()
            blacklist_everything_button.hide()
            
            self._advanced_whitelist_input.hide()
            delete_whitelist_button.hide()
            
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, blacklist_everything_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._advanced_blacklist_panel.Add( self._advanced_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._advanced_blacklist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._advanced_whitelist_panel.Add( self._advanced_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._advanced_whitelist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._advanced_blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._advanced_whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        advanced_panel.setLayout( hbox )
        
        return advanced_panel
        
    
    def _InitBlacklistPanel( self ):
        
        blacklist_overpanel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_blacklist_error_st = ClientGUICommon.BetterStaticText( blacklist_overpanel )
        self._simple_blacklist_error_st.setVisible( False )
        
        #
        
        self._simple_blacklist_panel = ClientGUICommon.StaticBox( blacklist_overpanel, 'exclude these' )
        
        self._simple_blacklist_global_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        self._simple_blacklist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_blacklist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_blacklist_global_checkboxes.SetHeightBasedOnContents()
        
        self._simple_blacklist_namespace_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_blacklist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( self._simple_whitelist_panel, read_only = self._read_only )
        
        self._simple_blacklist_input = ClientGUITextInput.TextAndPasteCtrl( self._simple_whitelist_panel, self._SimpleAddBlacklistMultiple, allow_empty_input = True )
        
        delete_blacklist_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'remove', self._SimpleDeleteBlacklistButton )
        blacklist_everything_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        if self._read_only:
            
            self._simple_blacklist_global_checkboxes.setEnabled( False )
            self._simple_blacklist_namespace_checkboxes.setEnabled( False )
            
            self._simple_blacklist_input.hide()
            
            delete_blacklist_button.hide()
            blacklist_everything_button.hide()
            
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_blacklist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._simple_blacklist_namespace_checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._simple_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, blacklist_everything_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._simple_blacklist_panel.Add( main_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_blacklist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        blacklist_overpanel.setLayout( vbox )
        
        self._simple_blacklist.tagsRemoved.connect( self._SimpleBlacklistRemoved )
        
        return blacklist_overpanel
        
    
    def _InitWhitelistPanel( self ):
        
        whitelist_overpanel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_whitelist_error_st = ClientGUICommon.BetterStaticText( whitelist_overpanel )
        self._simple_whitelist_error_st.setVisible( False )
        
        #
        
        self._simple_whitelist_panel = ClientGUICommon.StaticBox( whitelist_overpanel, 'allow these' )
        
        self._simple_whitelist_global_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        self._simple_whitelist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_whitelist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_whitelist_global_checkboxes.SetHeightBasedOnContents()
        
        self._simple_whitelist_namespace_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_whitelist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        #
        
        self._simple_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( self._simple_whitelist_panel, read_only = self._read_only )
        
        self._simple_whitelist_input = ClientGUITextInput.TextAndPasteCtrl( self._simple_whitelist_panel, self._SimpleAddWhitelistMultiple, allow_empty_input = True )
        
        delete_whitelist_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'remove', self._SimpleDeleteWhitelistButton )
        
        #
        
        if self._read_only:
            
            self._simple_whitelist_global_checkboxes.setEnabled( False )
            self._simple_whitelist_namespace_checkboxes.setEnabled( False )
            
            self._simple_whitelist_input.hide()
            delete_whitelist_button.hide()
            
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_whitelist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._simple_whitelist_namespace_checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._simple_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._simple_whitelist_panel.Add( main_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_whitelist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        whitelist_overpanel.setLayout( vbox )
        
        self._simple_whitelist.tagsRemoved.connect( self._SimpleWhitelistRemoved )
        
        return whitelist_overpanel
        
    
    def _LoadFavourite( self ):
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'load {}'.format( name ), self.SetValue, tag_filter )
                
            
        
        tag_repositories = CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        if len( tag_repositories ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for service in sorted( tag_repositories, key = lambda s: s.GetName() ):
                
                tag_filter = service.GetTagFilter()
                
                ClientGUIMenus.AppendMenuItem( menu, f'tag filter for "{service.GetName()}"', 'load the serverside tag filter for this service', self.SetValue, tag_filter )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SaveFavourite( self ):
        
        try:
            
            message = 'Enter a name for the favourite.'
            
            name = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        tag_filter = self.GetValue()
        
        if name in names_to_tag_filters:
            
            message = '"{}" already exists! Overwrite?'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        names_to_tag_filters[ name ] = tag_filter
        
        CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
        
    
    def _ShowAllPanels( self ):
        
        self._whitelist_panel.setVisible( True )
        self._advanced_panel.setVisible( True )
        
        self._notebook.addTab( self._whitelist_panel, 'whitelist' )
        self._notebook.addTab( self._advanced_panel, 'advanced' )
        
        self._show_all_panels_button.setVisible( False )
        
    
    def _ShowHelp( self ):
        
        help = 'Here you can set rules to filter tags for one purpose or another. The default is typically to permit all tags. Check the current filter summary text at the bottom-left of the panel to ensure you have your logic correct.'
        help += '\n' * 2
        help += 'The whitelist/blacklist/advanced tabs are different ways of looking at the same filter, so you can choose which works best for you. Sometimes it is more useful to think about a filter as a whitelist (where only the listed contents are kept) or a blacklist (where everything _except_ the listed contents are kept), while the advanced tab lets you do a more complicated combination of the two.'
        help += '\n' * 2
        help += 'As well as selecting entire namespaces with the checkboxes, you can type or paste the individual tags directly--just hit enter to add each one. Double-click an existing entry in a list to remove it.'
        
        ClientGUIDialogsMessage.ShowInformation( self, help )
        
    
    def _ShowRedundantError( self, text ):
        
        self._redundant_st.setVisible( True )
        
        self._redundant_st.setText( text )
        
        CG.client_controller.CallLaterQtSafe( self._redundant_st, 2, 'clear redundant error', self._redundant_st.setVisible, False )
        
    
    def _SimpleAddBlacklistMultiple( self, tag_slices ):
        
        self._AdvancedAddBlacklistMultiple( tag_slices )
        
    
    def _SimpleAddWhitelistMultiple( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if False and simple in tag_slices and simple in self._simple_whitelist.GetTagSlices():
                
                tag_slices.discard( simple )
                
                self._AdvancedEnterBlacklistMultiple( ( simple, ) )
                
            
        
        self._AdvancedAddWhitelistMultiple( tag_slices )
        
    
    def _SimpleBlacklistRemoved( self, tag_slices ):
        
        self._AdvancedEnterBlacklistMultiple( tag_slices )
        
    
    def _SimpleBlacklistReset( self ):
        
        pass
        
    
    def _SimpleDeleteBlacklistButton( self ):
        
        selected_tag_slices = self._simple_blacklist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._simple_blacklist.RemoveTagSlices( selected_tag_slices )
                
                self._simple_blacklist.tagsRemoved.emit( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _SimpleDeleteWhitelistButton( self ):
        
        selected_tag_slices = self._simple_whitelist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._simple_whitelist.RemoveTagSlices( selected_tag_slices )
                
                self._simple_whitelist.tagsRemoved.emit( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _SimpleWhitelistRemoved( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if simple in tag_slices:
                
                tag_slices.discard( simple )
                
                self._AdvancedEnterBlacklistMultiple( ( simple, ) )
                
            
        
        self._AdvancedEnterWhitelistMultiple( tag_slices )
        
    
    def _SimpleWhitelistReset( self ):
        
        pass
        
    
    def _UpdateStatus( self ):
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        
        self._whitelist_panel.setEnabled( whitelist_possible )
        
        self._simple_whitelist_error_st.setVisible( not whitelist_possible )
        
        if whitelist_possible:
            
            whitelist_tag_slices = set( whitelist_tag_slices )
            
            if not self._CurrentlyBlocked( '' ):
                
                whitelist_tag_slices.add( '' )
                
            
            if not self._CurrentlyBlocked( ':' ):
                
                whitelist_tag_slices.add( ':' )
                
                self._simple_whitelist_namespace_checkboxes.setEnabled( False )
                
            else:
                
                self._simple_whitelist_namespace_checkboxes.setEnabled( True )
                
            
            self._simple_whitelist.SetTagSlices( whitelist_tag_slices )
            
            for index in range( self._simple_whitelist_global_checkboxes.count() ):
                
                check = self._simple_whitelist_global_checkboxes.GetData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                check = self._simple_whitelist_namespace_checkboxes.GetData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_whitelist_error_st.setText( 'The filter is currently more complicated than a simple whitelist, so it cannot be shown here.' )
            
            self._simple_whitelist.SetTagSlices( '' )
            
            for index in range( self._simple_whitelist_global_checkboxes.count() ):
                
                self._simple_whitelist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                self._simple_whitelist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        self._blacklist_panel.setEnabled( blacklist_possible )
        
        self._simple_blacklist_error_st.setVisible( not blacklist_possible )
        
        if blacklist_possible:
            
            if self._CurrentlyBlocked( ':' ):
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( False )
                
            else:
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( True )
                
            
            self._simple_blacklist.SetTagSlices( blacklist_tag_slices )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                check = self._simple_blacklist_global_checkboxes.GetData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                check = self._simple_blacklist_namespace_checkboxes.GetData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_blacklist_error_st.setText( 'The filter is currently more complicated than a simple blacklist, so it cannot be shown here.' )
            
            self._simple_blacklist.SetTagSlices( '' )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                self._simple_blacklist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                self._simple_blacklist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        self._advanced_whitelist_input.setEnabled( len( blacklist_tag_slices ) > 0 )
        
        #
        
        tag_filter = self.GetValue()
        
        if self._only_show_blacklist:
            
            pretty_tag_filter = tag_filter.ToBlacklistString()
            
        else:
            
            pretty_tag_filter = 'current filter: {}'.format( tag_filter.ToPermittedString() )
            
        
        self._current_filter_st.setText( pretty_tag_filter )
        
        self._UpdateTest()
        
    
    def _UpdateTest( self ):
        
        test_input = self._test_input.toPlainText()
        
        if test_input == '':
            
            if self._only_show_blacklist:
                
                test_result_text = self.TEST_RESULT_BLACKLIST_DEFAULT
                
            else:
                
                test_result_text = self.TEST_RESULT_DEFAULT
                
            
            self._test_result_st.setObjectName( '' )
            
            self._test_result_st.setText( test_result_text )
            self._test_result_st.style().polish( self._test_result_st )
            
        else:
            
            test_tags = HydrusText.DeserialiseNewlinedTexts( test_input )
            
            test_tags = HydrusTags.CleanTags( test_tags )
            
            tag_filter = self.GetValue()
            
            self._test_result_st.setObjectName( '' )
            
            self._test_result_st.clear()
            self._test_result_st.style().polish( self._test_result_st )
            
            if self._only_show_blacklist:
                
                def work_callable():
                    
                    results = []
                    
                    tags_to_siblings = CG.client_controller.Read( 'tag_siblings_lookup', CC.COMBINED_TAG_SERVICE_KEY, test_tags )
                    
                    for test_tag_and_siblings in tags_to_siblings.values():
                        
                        results.append( False not in ( tag_filter.TagOK( t, apply_unnamespaced_rules_to_namespaced_tags = True ) for t in test_tag_and_siblings ) )
                        
                    
                    return results
                    
                
            else:
                
                def work_callable():
                    
                    results = [ tag_filter.TagOK( test_tag ) for test_tag in test_tags ]
                    
                    return results
                    
                
            
            def publish_callable( results ):
                
                all_good = False not in results
                all_bad = True not in results
                
                if len( results ) == 1:
                    
                    if all_good:
                        
                        test_result_text = 'tag passes!'
                        
                        self._test_result_st.setObjectName( 'HydrusValid' )
                        
                    else:
                        
                        test_result_text = 'tag blocked!'
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    
                else:
                    
                    if all_good:
                        
                        test_result_text = 'all pass!'
                        
                        self._test_result_st.setObjectName( 'HydrusValid' )
                        
                    elif all_bad:
                        
                        test_result_text = 'all blocked!'
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    else:
                        
                        c = collections.Counter()
                        
                        c.update( results )
                        
                        test_result_text = '{} pass, {} blocked!'.format( HydrusNumbers.ToHumanInt( c[ True ] ), HydrusNumbers.ToHumanInt( c[ False ] ) )
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    
                
                self._test_result_st.setText( test_result_text )
                self._test_result_st.style().polish( self._test_result_st )
                
            
            async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_job.start()
            
        
    
    def EventSimpleBlacklistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_blacklist_namespace_checkboxes.GetData( index )
            
            self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleBlacklistGlobalCheck( self, index ):
        
        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_blacklist_global_checkboxes.GetData( index )
            
            self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleWhitelistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_whitelist_namespace_checkboxes.GetData( index )
            
            self._AdvancedEnterWhitelistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleWhitelistGlobalCheck( self, index ):
        
        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_whitelist_global_checkboxes.GetData( index )
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetTagSlices():
                
                self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
                
            else:
                
                self._AdvancedEnterWhitelistMultiple( ( tag_slice, ) )
                
            
        
    
    def GetValue( self ):
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRules( self._advanced_blacklist.GetTagSlices(), HC.FILTER_BLACKLIST )
        tag_filter.SetRules( self._advanced_whitelist.GetTagSlices(), HC.FILTER_WHITELIST )
        
        return tag_filter
        
    
    def SetValue( self, tag_filter: HydrusTags.TagFilter ):
        
        blacklist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == HC.FILTER_BLACKLIST ]
        whitelist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == HC.FILTER_WHITELIST ]
        
        self._advanced_blacklist.SetTagSlices( blacklist_tag_slices )
        self._advanced_whitelist.SetTagSlices( whitelist_tag_slices )
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        selection_tests = []
        
        if self._only_show_blacklist:
            
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            
        else:
            
            selection_tests.append( ( whitelist_possible, self._whitelist_panel ) )
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            selection_tests.append( ( True, self._advanced_panel ) )
            
        
        for ( test, page ) in selection_tests:
            
            if test:
                
                self._notebook.SelectPage( page )
                
                break
                
            
        
        self._UpdateStatus()
        
    

class TagFilterButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, message, tag_filter, only_show_blacklist = False, label_prefix = None ):
        
        super().__init__( parent, 'tag filter', self._EditTagFilter )
        
        self._message = message
        self._tag_filter = tag_filter
        self._only_show_blacklist = only_show_blacklist
        self._label_prefix = label_prefix
        
        self._UpdateLabel()
        
    
    def _EditTagFilter( self ):
        
        if self._only_show_blacklist:
            
            title = 'edit blacklist'
            
        else:
            
            title = 'edit tag filter'
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            panel = EditTagFilterPanel( dlg, self._tag_filter, only_show_blacklist = self._only_show_blacklist, namespaces = namespaces, message = self._message )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_filter = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        if self._only_show_blacklist:
            
            tt = self._tag_filter.ToBlacklistString()
            
        else:
            
            tt = self._tag_filter.ToPermittedString()
            
        
        if self._label_prefix is not None:
            
            tt = self._label_prefix + tt
            
        
        button_text = HydrusText.ElideText( tt, 45 )
        
        self.setText( button_text )
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
    
    def GetValue( self ):
        
        return self._tag_filter
        
    
    def SetValue( self, tag_filter ):
        
        self._tag_filter = tag_filter
        
        self._UpdateLabel()
        
    
