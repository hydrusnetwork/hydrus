import ClientConstants as CC
import ClientGUICommon
import ClientGUIControls
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUITopLevelWindows
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUIShortcuts
import ClientTags
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import HydrusTagArchive
import os
import wx

class EditTagFilterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_filter, prefer_blacklist = False, namespaces = None, message = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._namespaces = namespaces
        
        #
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowHelp )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        self._notebook = wx.Notebook( self )
        
        #
        
        self._advanced_panel = self._InitAdvancedPanel()
        
        self._whitelist_panel = self._InitWhitelistPanel()
        self._blacklist_panel = self._InitBlacklistPanel()
        
        #
        
        if prefer_blacklist:
            
            self._notebook.AddPage( self._blacklist_panel, 'blacklist' )
            self._notebook.AddPage( self._whitelist_panel, 'whitelist' )
            
        else:
            
            self._notebook.AddPage( self._whitelist_panel, 'whitelist' )
            self._notebook.AddPage( self._blacklist_panel, 'blacklist' )
            
        
        self._notebook.AddPage( self._advanced_panel, 'advanced' )
        
        blacklist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == CC.FILTER_BLACKLIST ]
        whitelist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == CC.FILTER_WHITELIST ]
        
        self._advanced_blacklist.AddTags( blacklist_tag_slices )
        self._advanced_whitelist.AddTags( whitelist_tag_slices )
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        selection_tests = []
        
        if prefer_blacklist:
            
            selection_tests.append( ( blacklist_possible, 0 ) )
            selection_tests.append( ( whitelist_possible, 1 ) )
            selection_tests.append( ( True, 2 ) )
            
        else:
            
            selection_tests.append( ( whitelist_possible, 0 ) )
            selection_tests.append( ( blacklist_possible, 1 ) )
            selection_tests.append( ( True, 2 ) )
            
        
        for ( test, index ) in selection_tests:
            
            if test:
                
                self._notebook.SetSelection( index )
                
                break
                
            
        
        #
        
        self._redundant_st = ClientGUICommon.BetterStaticText( self, '' )
        
        self._current_filter_st = ClientGUICommon.BetterStaticText( self, 'currently keeping: ' )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        
        if message is not None:
            
            vbox.Add( ClientGUICommon.BetterStaticText( self, message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._redundant_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._current_filter_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._advanced_panel.Bind( ClientGUIListBoxes.EVT_LIST_BOX, self.EventListBoxChanged )
        self._simple_whitelist_global_checkboxes.Bind( wx.EVT_CHECKLISTBOX, self.EventSimpleWhitelistGlobalCheck )
        self._simple_whitelist_namespace_checkboxes.Bind( wx.EVT_CHECKLISTBOX, self.EventSimpleWhitelistNamespaceCheck )
        self._simple_blacklist_global_checkboxes.Bind( wx.EVT_CHECKLISTBOX, self.EventSimpleBlacklistGlobalCheck )
        self._simple_blacklist_namespace_checkboxes.Bind( wx.EVT_CHECKLISTBOX, self.EventSimpleBlacklistNamespaceCheck )
        
        self._UpdateStatus()
        
    
    def _AdvancedAddBlacklist( self, tag_slice ):
        
        if tag_slice in self._advanced_blacklist.GetClientData():
            
            self._advanced_blacklist.RemoveTags( ( tag_slice, ) )
            
        else:
            
            self._advanced_whitelist.RemoveTags( ( tag_slice, ) )
            
            if self._CurrentlyBlocked( tag_slice ):
                
                self._ShowRedundantError( ClientTags.ConvertTagSliceToString( tag_slice ) + ' is already blocked by a broader rule!' )
                
            else:
                
                self._advanced_blacklist.AddTags( ( tag_slice, ) )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedAddBlacklistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _AdvancedAddWhitelist( self, tag_slice ):
        
        if tag_slice in self._advanced_whitelist.GetClientData():
            
            self._advanced_whitelist.RemoveTags( ( tag_slice, ) )
            
        else:
            
            self._advanced_blacklist.RemoveTags( ( tag_slice, ) )
            
            # if it is still blocked after that, it needs whitelisting explicitly
            
            if self._CurrentlyBlocked( tag_slice ):
                
                self._advanced_whitelist.AddTags( ( tag_slice, ) )
                
            elif tag_slice not in ( '', ':' ):
                
                self._ShowRedundantError( ClientTags.ConvertTagSliceToString( tag_slice ) + ' is already permitted by a broader rule!' )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedAddWhitelistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def _AdvancedBlacklistEverything( self ):
        
        self._advanced_blacklist.SetTags( [] )
        
        self._advanced_whitelist.RemoveTags( ( '', ':' ) )
        
        self._advanced_blacklist.AddTags( ( '', ':' ) )
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteBlacklist( self ):
        
        selected_tag_slices = self._advanced_blacklist.GetSelectedTags()
        
        if len( selected_tag_slices ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._advanced_blacklist.RemoveTags( selected_tag_slices )
                    
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteWhitelist( self ):
        
        selected_tag_slices = self._advanced_whitelist.GetSelectedTags()
        
        if len( selected_tag_slices ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._advanced_whitelist.RemoveTags( selected_tag_slices )
                    
                
            
        
        self._UpdateStatus()
        
    
    def _CurrentlyBlocked( self, tag_slice ):
        
        if tag_slice in ( '', ':' ):
            
            test_slices = { tag_slice }
            
        elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
            
            test_slices = { ':', tag_slice }
            
        elif ':' in tag_slice:
            
            ( ns, st ) = HydrusTags.SplitTag( tag_slice )
            
            test_slices = { ':', ns + ':', tag_slice }
            
        else:
            
            test_slices = { '', tag_slice }
            
        
        blacklist = set( self._advanced_blacklist.GetClientData() )
        
        return not blacklist.isdisjoint( test_slices )
        
    
    def _GetWhiteBlacklistsPossible( self ):
        
        blacklist_tag_slices = self._advanced_blacklist.GetClientData()
        whitelist_tag_slices = self._advanced_whitelist.GetClientData()
        
        blacklist_is_only_simples = set( blacklist_tag_slices ).issubset( { '', ':' } )
        
        nothing_is_whitelisted = len( whitelist_tag_slices ) == 0
        
        whitelist_possible = blacklist_is_only_simples
        blacklist_possible = nothing_is_whitelisted
        
        return ( whitelist_possible, blacklist_possible )
        
    
    def _InitAdvancedPanel( self ):
        
        advanced_panel = wx.Panel( self._notebook )
        
        #
        
        blacklist_panel = ClientGUICommon.StaticBox( advanced_panel, 'exclude these' )
        
        self._advanced_blacklist = ClientGUIListBoxes.ListBoxTagsCensorship( blacklist_panel )
        
        self._advanced_blacklist_input = ClientGUIControls.TextAndPasteCtrl( blacklist_panel, self._AdvancedAddBlacklistMultiple, allow_empty_input = True )
        
        add_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'add', self._AdvancedAddBlacklist )
        delete_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'delete', self._AdvancedDeleteBlacklist )
        blacklist_everything_button = ClientGUICommon.BetterButton( blacklist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        whitelist_panel = ClientGUICommon.StaticBox( advanced_panel, 'except for these' )
        
        self._advanced_whitelist = ClientGUIListBoxes.ListBoxTagsCensorship( whitelist_panel )
        
        self._advanced_whitelist_input = ClientGUIControls.TextAndPasteCtrl( whitelist_panel, self._AdvancedAddWhitelistMultiple, allow_empty_input = True )
        
        self._advanced_add_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'add', self._AdvancedAddWhitelist )
        delete_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'delete', self._AdvancedDeleteWhitelist )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._advanced_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.Add( add_blacklist_button, CC.FLAGS_VCENTER )
        button_hbox.Add( delete_blacklist_button, CC.FLAGS_VCENTER )
        button_hbox.Add( blacklist_everything_button, CC.FLAGS_VCENTER )
        
        blacklist_panel.Add( self._advanced_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        blacklist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._advanced_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.Add( self._advanced_add_whitelist_button, CC.FLAGS_VCENTER )
        button_hbox.Add( delete_whitelist_button, CC.FLAGS_VCENTER )
        
        whitelist_panel.Add( self._advanced_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        whitelist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        advanced_panel.SetSizer( hbox )
        
        return advanced_panel
        
    
    def _InitBlacklistPanel( self ):
        
        blacklist_panel = wx.Panel( self._notebook )
        
        #
        
        self._simple_blacklist_error_st = ClientGUICommon.BetterStaticText( blacklist_panel )
        
        self._simple_blacklist_global_checkboxes = ClientGUICommon.BetterCheckListBox( blacklist_panel )
        
        self._simple_blacklist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_blacklist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_blacklist_namespace_checkboxes = ClientGUICommon.BetterCheckListBox( blacklist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_blacklist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_blacklist = ClientGUIListBoxes.ListBoxTagsCensorship( blacklist_panel, removed_callable = self._SimpleBlacklistRemoved )
        
        self._simple_blacklist_input = ClientGUIControls.TextAndPasteCtrl( blacklist_panel, self._SimpleAddBlacklistMultiple, allow_empty_input = True )
        
        #
        
        left_vbox = wx.BoxSizer( wx.VERTICAL )
        
        left_vbox.Add( self._simple_blacklist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.Add( self._simple_blacklist_namespace_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        right_vbox = wx.BoxSizer( wx.VERTICAL )
        
        right_vbox.Add( self._simple_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        right_vbox.Add( self._simple_blacklist_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        main_hbox.Add( left_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        main_hbox.Add( right_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._simple_blacklist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( main_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        blacklist_panel.SetSizer( vbox )
        
        return blacklist_panel
        
    
    def _InitWhitelistPanel( self ):
        
        whitelist_panel = wx.Panel( self._notebook )
        
        #
        
        self._simple_whitelist_error_st = ClientGUICommon.BetterStaticText( whitelist_panel )
        
        self._simple_whitelist_global_checkboxes = ClientGUICommon.BetterCheckListBox( whitelist_panel )
        
        self._simple_whitelist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_whitelist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_whitelist_namespace_checkboxes = ClientGUICommon.BetterCheckListBox( whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_whitelist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_whitelist = ClientGUIListBoxes.ListBoxTagsCensorship( whitelist_panel, removed_callable = self._SimpleWhitelistRemoved )
        
        self._simple_whitelist_input = ClientGUIControls.TextAndPasteCtrl( whitelist_panel, self._SimpleAddWhitelistMultiple, allow_empty_input = True )
        
        #
        
        left_vbox = wx.BoxSizer( wx.VERTICAL )
        
        left_vbox.Add( self._simple_whitelist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.Add( self._simple_whitelist_namespace_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        right_vbox = wx.BoxSizer( wx.VERTICAL )
        
        right_vbox.Add( self._simple_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        right_vbox.Add( self._simple_whitelist_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        main_hbox.Add( left_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        main_hbox.Add( right_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._simple_whitelist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( main_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        whitelist_panel.SetSizer( vbox )
        
        return whitelist_panel
        
    
    def _ShowHelp( self ):
        
        help = 'Here you can set rules to filter tags for one purpose or another. The default is typically to permit all tags. Check the current filter summary text at the bottom-left of the panel to ensure you have your logic correct.'
        help += os.linesep * 2
        help += 'The different tabs are multiple ways of looking at the filter--sometimes it is more useful to think about a filter as a whitelist (where only the listed contents are kept) or a blacklist (where everything _except_ the listed contents are kept), and there is also an advanced tab that lets you do a more complicated combination of the two.'
        help += os.linesep * 2
        help += 'As well as selecting broader categories of tags with the checkboxes, you can type or paste the individual tags directly--just hit enter to add each one--and double-click an existing entry in a list to remove it.'
        help += os.linesep * 2
        help += 'If you wish to manually type a special tag, use these shorthands:'
        help += os.linesep * 2
        help += '"namespace:" - all instances of that namespace'
        help += os.linesep
        help += '":" - all namespaced tags'
        help += os.linesep
        help += '"" (i.e. an empty string) - all unnamespaced tags'
        
        wx.MessageBox( help )
        
    
    def _ShowRedundantError( self, text ):
        
        self._redundant_st.SetLabelText( text )
        
        HG.client_controller.CallLaterWXSafe( self._redundant_st, 2, self._redundant_st.SetLabelText, '' )
        
    
    def _SimpleAddBlacklistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _SimpleAddWhitelistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetClientData():
                
                self._AdvancedAddBlacklist( tag_slice )
                
            else:
                
                self._AdvancedAddWhitelist( tag_slice )
                
            
        
    
    def _SimpleBlacklistRemoved( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _SimpleBlacklistReset( self ):
        
        pass
        
    
    def _SimpleWhitelistRemoved( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if simple in tag_slices:
                
                tag_slices.discard( simple )
                
                self._AdvancedAddBlacklist( simple )
                
            
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def _SimpleWhitelistReset( self ):
        
        pass
        
    
    def _UpdateStatus( self ):
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        whitelist_tag_slices = self._advanced_whitelist.GetClientData()
        blacklist_tag_slices = self._advanced_blacklist.GetClientData()
        
        if whitelist_possible:
            
            self._simple_whitelist_error_st.SetLabelText( '' )
            
            self._simple_whitelist.Enable()
            self._simple_whitelist_global_checkboxes.Enable()
            self._simple_whitelist_input.Enable()
            
            whitelist_tag_slices = set( whitelist_tag_slices )
            
            if not self._CurrentlyBlocked( '' ):
                
                whitelist_tag_slices.add( '' )
                
            
            if not self._CurrentlyBlocked( ':' ):
                
                whitelist_tag_slices.add( ':' )
                
                self._simple_whitelist_namespace_checkboxes.Disable()
                
            else:
                
                self._simple_whitelist_namespace_checkboxes.Enable()
                
            
            self._simple_whitelist.SetTags( whitelist_tag_slices )
            
            for index in range( self._simple_whitelist_global_checkboxes.GetCount() ):
                
                check = self._simple_whitelist_global_checkboxes.GetClientData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.GetCount() ):
                
                check = self._simple_whitelist_namespace_checkboxes.GetClientData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_whitelist_error_st.SetLabelText( 'The filter is currently more complicated than a simple whitelist, so cannot be shown here.' )
            
            self._simple_whitelist.Disable()
            self._simple_whitelist_global_checkboxes.Disable()
            self._simple_whitelist_namespace_checkboxes.Disable()
            self._simple_whitelist_input.Disable()
            
            self._simple_whitelist.SetTags( '' )
            
            for index in range( self._simple_whitelist_global_checkboxes.GetCount() ):
                
                self._simple_whitelist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.GetCount() ):
                
                self._simple_whitelist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetClientData()
        blacklist_tag_slices = self._advanced_blacklist.GetClientData()
        
        if blacklist_possible:
            
            self._simple_blacklist_error_st.SetLabelText( '' )
            
            self._simple_blacklist.Enable()
            self._simple_blacklist_global_checkboxes.Enable()
            self._simple_blacklist_input.Enable()
            
            if self._CurrentlyBlocked( ':' ):
                
                self._simple_blacklist_namespace_checkboxes.Disable()
                
            else:
                
                self._simple_blacklist_namespace_checkboxes.Enable()
                
            
            self._simple_blacklist.SetTags( blacklist_tag_slices )
            
            for index in range( self._simple_blacklist_global_checkboxes.GetCount() ):
                
                check = self._simple_blacklist_global_checkboxes.GetClientData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.GetCount() ):
                
                check = self._simple_blacklist_namespace_checkboxes.GetClientData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_blacklist_error_st.SetLabelText( 'The filter is currently more complicated than a simple blacklist, so cannot be shown here.' )
            
            self._simple_blacklist.Disable()
            self._simple_blacklist_global_checkboxes.Disable()
            self._simple_blacklist_namespace_checkboxes.Disable()
            self._simple_blacklist_input.Disable()
            
            self._simple_blacklist.SetTags( '' )
            
            for index in range( self._simple_blacklist_global_checkboxes.GetCount() ):
                
                self._simple_blacklist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.GetCount() ):
                
                self._simple_blacklist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetClientData()
        blacklist_tag_slices = self._advanced_blacklist.GetClientData()
        
        if len( blacklist_tag_slices ) == 0:
            
            self._advanced_whitelist_input.Disable()
            self._advanced_add_whitelist_button.Disable()
            
        else:
            
            self._advanced_whitelist_input.Enable()
            self._advanced_add_whitelist_button.Enable()
            
        
        #
        
        tag_filter = self.GetValue()
        
        pretty_tag_filter = tag_filter.ToPermittedString()
        
        self._current_filter_st.SetLabelText( 'currently keeping: ' + pretty_tag_filter )
        
    
    def EventListBoxChanged( self, event ):
        
        self._UpdateStatus()
        
    
    def EventSimpleBlacklistNamespaceCheck( self, event ):
        
        index = event.GetInt()
        
        if index != wx.NOT_FOUND:
            
            tag_slice = self._simple_blacklist_namespace_checkboxes.GetClientData( index )
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def EventSimpleBlacklistGlobalCheck( self, event ):
        
        index = event.GetInt()
        
        if index != wx.NOT_FOUND:
            
            tag_slice = self._simple_blacklist_global_checkboxes.GetClientData( index )
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def EventSimpleWhitelistNamespaceCheck( self, event ):
        
        index = event.GetInt()
        
        if index != wx.NOT_FOUND:
            
            tag_slice = self._simple_whitelist_namespace_checkboxes.GetClientData( index )
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def EventSimpleWhitelistGlobalCheck( self, event ):
        
        index = event.GetInt()
        
        if index != wx.NOT_FOUND:
            
            tag_slice = self._simple_whitelist_global_checkboxes.GetClientData( index )
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetClientData():
                
                self._AdvancedAddBlacklist( tag_slice )
                
            else:
                
                self._AdvancedAddWhitelist( tag_slice )
                
            
        
    
    def GetValue( self ):
        
        tag_filter = ClientTags.TagFilter()
        
        for tag_slice in self._advanced_blacklist.GetClientData():
            
            tag_filter.SetRule( tag_slice, CC.FILTER_BLACKLIST )
            
        
        for tag_slice in self._advanced_whitelist.GetClientData():
            
            tag_filter.SetRule( tag_slice, CC.FILTER_WHITELIST )
            
        
        return tag_filter
        
    
def ExportToHTA( parent, service_key, hashes ):
    
    with wx.FileDialog( parent, style = wx.FD_SAVE, defaultFile = 'archive.db' ) as dlg:
        
        if dlg.ShowModal() == wx.ID_OK:
            
            path = HydrusData.ToUnicode( dlg.GetPath() )
            
        else:
            
            return
            
        
    
    message = 'Would you like to use hydrus\'s normal hash type, or an alternative?'
    message += os.linesep * 2
    message += 'Hydrus uses SHA256 to identify files, but other services use different standards. MD5, SHA1 and SHA512 are available, but only for local files, which may limit your export.'
    message += os.linesep * 2
    message += 'If you do not know what this stuff means, click \'normal\'.'
    
    with ClientGUIDialogs.DialogYesNo( parent, message, title = 'Choose which hash type.', yes_label = 'normal', no_label = 'alternative' ) as dlg:
        
        result = dlg.ShowModal()
        
        if result in ( wx.ID_YES, wx.ID_NO ):
            
            if result == wx.ID_YES:
                
                hash_type = HydrusTagArchive.HASH_TYPE_SHA256
                
            else:
                
                choice_tuples = []
                
                choice_tuples.append( ( 'md5', HydrusTagArchive.HASH_TYPE_MD5 ) )
                choice_tuples.append( ( 'sha1', HydrusTagArchive.HASH_TYPE_SHA1 ) )
                choice_tuples.append( ( 'sha512', HydrusTagArchive.HASH_TYPE_SHA512 ) )
                
                with ClientGUIDialogs.DialogSelectFromList( parent, 'Select the hash type', choice_tuples ) as hash_dlg:
                    
                    if hash_dlg.ShowModal() == wx.ID_OK:
                        
                        hash_type = hash_dlg.GetChoice()
                        
                    else:
                        
                        return
                        
                    
                
            
        
    
    if hash_type is not None:
        
        HG.client_controller.Write( 'export_mappings', path, service_key, hash_type, hashes )
        
    
def ImportFromHTA( parent, hta_path, tag_service_key, hashes ):
    
    hta = HydrusTagArchive.HydrusTagArchive( hta_path )
    
    potential_namespaces = list( hta.GetNamespaces() )
    
    potential_namespaces.sort()
    
    hash_type = hta.GetHashType() # this tests if the hta can produce a hashtype
    
    del hta
    
    service = HG.client_controller.services_manager.GetService( tag_service_key )
    
    service_type = service.GetServiceType()
    
    can_delete = True
    
    if service_type == HC.TAG_REPOSITORY:
        
        if service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
            
            can_delete = False
            
        
    
    if can_delete:
        
        text = 'Would you like to add or delete the archive\'s tags?'
        
        with ClientGUIDialogs.DialogYesNo( parent, text, title = 'Add or delete?', yes_label = 'add', no_label = 'delete' ) as dlg_add:
            
            result = dlg_add.ShowModal()
            
            if result == wx.ID_YES: adding = True
            elif result == wx.ID_NO: adding = False
            else: return
            
        
    else:
        
        text = 'You cannot quickly delete tags from this service, so I will assume you want to add tags.'
        
        wx.MessageBox( text )
        
        adding = True
        
    
    text = 'Choose which namespaces to '
    
    if adding: text += 'add.'
    else: text += 'delete.'
    
    choice_tuples = [ ( HydrusData.ConvertUglyNamespaceToPrettyString( namespace ), namespace, False ) for namespace in potential_namespaces ]
    
    with ClientGUITopLevelWindows.DialogEdit( parent, text ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.ShowModal() == wx.ID_OK:
            
            namespaces = panel.GetValue()
            
            if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                
                text = 'This tag archive can be fully merged into your database, but this may be more than you want.'
                text += os.linesep * 2
                text += 'Would you like to import the tags only for files you actually have, or do you want absolutely everything?'
                
                with ClientGUIDialogs.DialogYesNo( parent, text, title = 'How much do you want?', yes_label = 'just for my local files', no_label = 'everything' ) as dlg_add:
                    
                    result = dlg_add.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                        
                    elif result == wx.ID_NO:
                        
                        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            
            text = 'Are you absolutely sure you want to '
            
            if adding: text += 'add'
            else: text += 'delete'
            
            text += ' the namespaces:'
            text += os.linesep * 2
            text += os.linesep.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) )
            text += os.linesep * 2
            
            file_service = HG.client_controller.services_manager.GetService( file_service_key )
            
            text += 'For '
            
            if hashes is None:
                
                text += 'all'
                
            else:
                
                text += HydrusData.ToHumanInt( len( hashes ) )
                
            
            text += ' files in \'' + file_service.GetName() + '\''
            
            if adding: text += ' to '
            else: text += ' from '
            
            text += '\'' + service.GetName() + '\'?'
            
            with ClientGUIDialogs.DialogYesNo( parent, text ) as dlg_final:
                
                if dlg_final.ShowModal() == wx.ID_YES:
                    
                    HG.client_controller.pub( 'sync_to_tag_archive', hta_path, tag_service_key, file_service_key, adding, namespaces, hashes )
                    
                
            
        
    
class TagFilterButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, message, tag_filter, is_blacklist = False ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'tag filter', self._EditTagFilter )
        
        self._message = message
        self._tag_filter = tag_filter
        self._is_blacklist = is_blacklist
        
        self._UpdateLabel()
        
    
    def _EditTagFilter( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag filter' ) as dlg:
            
            namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            panel = EditTagFilterPanel( dlg, self._tag_filter, prefer_blacklist = self._is_blacklist, namespaces = namespaces, message = self._message )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._tag_filter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        if self._is_blacklist:
            
            tt = self._tag_filter.ToBlacklistString()
            
        else:
            
            tt = self._tag_filter.ToPermittedString()
            
        
        self.SetLabelText( tt[:32] )
        
        self.SetToolTip( tt )
        
    
    def GetValue( self ):
        
        return self._tag_filter
        
    
class TagSummaryGenerator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR
    SERIALISABLE_NAME = 'Tag Summary Generator'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, background_colour = None, text_colour = None, namespace_info = None, separator = None, example_tags = None, show = True ):
        
        if background_colour is None:
            
            background_colour = wx.Colour( 223, 227, 230, 255 )
            
        
        if text_colour is None:
            
            text_colour = wx.Colour( 1, 17, 26, 255 )
            
        
        if namespace_info is None:
            
            namespace_info = []
            
            namespace_info.append( ( 'creator', '', ', ' ) )
            namespace_info.append( ( 'series', '', ', ' ) )
            namespace_info.append( ( 'title', '', ', ' ) )
            
        
        if separator is None:
            
            separator = ' - '
            
        
        if example_tags is None:
            
            example_tags = []
            
        
        self._background_colour = background_colour
        self._text_colour = text_colour
        self._namespace_info = namespace_info
        self._separator = separator
        self._example_tags = list( example_tags )
        self._show = show
        
        self._UpdateNamespaceLookup()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( list( self._background_colour.Get() ), list( self._text_colour.Get() ), self._namespace_info, self._separator, self._example_tags, self._show )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( background_rgba, text_rgba, self._namespace_info, self._separator, self._example_tags, self._show ) = serialisable_info
        
        ( r, g, b, a ) = background_rgba
        
        self._background_colour = wx.Colour( r, g, b, a )
        
        ( r, g, b, a ) = text_rgba
        
        self._text_colour = wx.Colour( r, g, b, a )
        
        self._namespace_info = [ tuple( row ) for row in self._namespace_info ]
        
        self._UpdateNamespaceLookup()
        
    
    def _UpdateNamespaceLookup( self ):
        
        self._interesting_namespaces = { namespace for ( namespace, prefix, separator ) in self._namespace_info }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( namespace_info, separator, example_tags ) = old_serialisable_info
            
            background_rgba = ( 223, 227, 230, 255 )
            text_rgba = ( 1, 17, 26, 255 )
            show = True
            
            new_serialisable_info = ( background_rgba, text_rgba, namespace_info, separator, example_tags, show )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GenerateExampleSummary( self ):
        
        if not self._show:
            
            return 'not showing'
            
        else:
            
            return self.GenerateSummary( self._example_tags )
            
        
    
    def GenerateSummary( self, tags, max_length = None ):
        
        if not self._show:
            
            return ''
            
        
        namespaces_to_subtags = collections.defaultdict( list )
        
        for tag in tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace in self._interesting_namespaces:
                
                namespaces_to_subtags[ namespace ].append( subtag )
                
            
        
        for ( namespace, unsorted_l ) in list( namespaces_to_subtags.items() ):
            
            sorted_l = HydrusTags.SortNumericTags( unsorted_l )
            
            sorted_l = HydrusTags.CollapseMultipleSortedNumericTagsToMinMax( sorted_l )
            
            namespaces_to_subtags[ namespace ] = sorted_l
            
        
        namespace_texts = []
        
        for ( namespace, prefix, separator ) in self._namespace_info:
            
            subtags = namespaces_to_subtags[ namespace ]
            
            if len( subtags ) > 0:
                
                namespace_text = prefix + separator.join( namespaces_to_subtags[ namespace ] )
                
                namespace_texts.append( namespace_text )
                
            
        
        summary = self._separator.join( namespace_texts )
        
        if max_length is not None:
            
            summary = summary[:max_length]
            
        
        return summary
        
    
    def GetBackgroundColour( self ):
        
        return self._background_colour
        
    
    def GetTextColour( self ):
        
        return self._text_colour
        
    
    def ToTuple( self ):
        
        return ( self._background_colour, self._text_colour, self._namespace_info, self._separator, self._example_tags, self._show )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR ] = TagSummaryGenerator
