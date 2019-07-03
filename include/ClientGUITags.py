from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUIACDropdown
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUITopLevelWindows
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsReview
from . import ClientGUIShortcuts
from . import ClientGUITagSuggestions
from . import ClientMedia
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusTagArchive
from . import HydrusText
import itertools
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
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
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
        
        blacklist_tag_slices = [ tag_slice for ( tag_slice, rule ) in list(tag_filter.GetTagSlicesToRules().items()) if rule == CC.FILTER_BLACKLIST ]
        whitelist_tag_slices = [ tag_slice for ( tag_slice, rule ) in list(tag_filter.GetTagSlicesToRules().items()) if rule == CC.FILTER_WHITELIST ]
        
        self._advanced_blacklist.AddTags( blacklist_tag_slices )
        self._advanced_whitelist.AddTags( whitelist_tag_slices )
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        selection_tests = []
        
        if prefer_blacklist:
            
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            selection_tests.append( ( whitelist_possible, self._whitelist_panel ) )
            selection_tests.append( ( True, self._advanced_panel ) )
            
        else:
            
            selection_tests.append( ( whitelist_possible, self._whitelist_panel ) )
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            selection_tests.append( ( True, self._advanced_panel ) )
            
        
        for ( test, page ) in selection_tests:
            
            if test:
                
                self._notebook.SelectPage( page )
                
                break
                
            
        
        #
        
        self._redundant_st = ClientGUICommon.BetterStaticText( self, '', style = wx.ST_ELLIPSIZE_END )
        
        self._current_filter_st = ClientGUICommon.BetterStaticText( self, 'currently keeping: ', style = wx.ST_ELLIPSIZE_END )
        
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
            
            path = dlg.GetPath()
            
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
                
                try:
                    
                    hash_type = ClientGUIDialogsQuick.SelectFromList( parent, 'select the hash type', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
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
                    
                
            
        
    
class ManageTagsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, file_service_key, media, immediate_commit = False, canvas_key = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._file_service_key = file_service_key
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        self._tag_repositories = ClientGUICommon.BetterNotebook( self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES, randomised = False )
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_repositories, self._file_service_key, service.GetServiceKey(), self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            
            select = service_key == default_tag_repository_key
            
            self._tag_repositories.AddPage( page, name, select = select )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Bind( ClientGUIACDropdown.EVT_SELECT_UP, self.EventSelectUp )
        self.Bind( ClientGUIACDropdown.EVT_SELECT_DOWN, self.EventSelectDown )
        
        self.Bind( ClientGUIACDropdown.EVT_SHOW_PREVIOUS, self.EventShowPrevious )
        self.Bind( ClientGUIACDropdown.EVT_SHOW_NEXT, self.EventShowNext )
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media', 'main_gui' ] )
        
        self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
        
        self._SetSearchFocus()
        
    
    def _GetGroupsOfServiceKeysToContentUpdates( self ):
        
        groups_of_service_keys_to_content_updates = []
        
        for page in self._tag_repositories.GetPages():
            
            ( service_key, groups_of_content_updates ) = page.GetGroupsOfContentUpdates()
            
            for content_updates in groups_of_content_updates:
                
                if len( content_updates ) > 0:
                    
                    service_keys_to_content_updates = { service_key : content_updates }
                    
                    groups_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
                    
                
            
        
        return groups_of_service_keys_to_content_updates
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._current_media = ( new_media_singleton.Duplicate(), )
                
                for page in self._tag_repositories.GetPages():
                    
                    page.SetMedia( self._current_media )
                    
                
            
        
    
    def CanCancel( self ):
        
        groups_of_service_keys_to_content_updates = self._GetGroupsOfServiceKeysToContentUpdates()
        
        if len( groups_of_service_keys_to_content_updates ) > 0:
            
            message = 'Are you sure you want to cancel? You have uncommitted changes that will be lost.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return False
                    
                
            
        
        return True
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUIScrolledPanels.ManagePanel.CleanBeforeDestroy( self )
        
        for page in self._tag_repositories.GetPages():
            
            page.CleanBeforeDestroy()
            
        
    
    def CommitChanges( self ):
        
        groups_of_service_keys_to_content_updates = self._GetGroupsOfServiceKeysToContentUpdates()
        
        for service_keys_to_content_updates in groups_of_service_keys_to_content_updates:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventSelectDown( self, event ):
        
        self._tag_repositories.SelectRight()
        
        self._SetSearchFocus()
        
    
    def EventSelectUp( self, event ):
        
        self._tag_repositories.SelectLeft()
        
        self._SetSearchFocus()
        
    
    def EventShowNext( self, event ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def EventShowPrevious( self, event ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def EventServiceChanged( self, event ):
        
        if not self: # actually did get a runtime error here, on some Linux WM dialog shutdown
            
            return
            
        
        if event.GetEventObject() != self._tag_repositories:
            
            return
            
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            wx.CallAfter( page.SetTagBoxFocus )
            
        
        event.Skip()
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'manage_file_tags':
                
                self._OKParent()
                
            elif action == 'focus_media_viewer':
                
                tlps = ClientGUIFunctions.GetTLPParents( self )
                
                from . import ClientGUICanvas
                
                command_processed = False
                
                for tlp in tlps:
                    
                    if isinstance( tlp, ClientGUICanvas.CanvasFrame ):
                        
                        tlp.TakeFocusForUser()
                        
                        command_processed = True
                        
                        break
                        
                    
                
            elif action == 'set_search_focus':
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_key, tag_service_key, media, immediate_commit, canvas_key = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_key = file_service_key
            self._tag_service_key = tag_service_key
            self._immediate_commit = immediate_commit
            self._canvas_key = canvas_key
            
            self._groups_of_content_updates = []
            
            self._i_am_local_tag_service = self._tag_service_key == CC.LOCAL_TAG_SERVICE_KEY
            
            if not self._i_am_local_tag_service:
                
                self._service = HG.client_controller.services_manager.GetService( tag_service_key )
                
            
            self._tags_box_sorter = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'tags' )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsSelectionTagsDialog( self._tags_box_sorter, self.EnterTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            if self._i_am_local_tag_service:
                
                text = 'remove all/selected tags'
                
            else:
                
                text = 'petition all/selected tags'
                
            
            self._remove_tags = ClientGUICommon.BetterButton( self._tags_box_sorter, text, self._RemoveTagsButton )
            
            menu_items = []
            
            call = HydrusData.Call( self._DoSiblingsAndParents, self._tag_service_key )
            
            menu_items.append( ( 'normal', 'Hard-replace all applicable tags with their siblings and add missing parents. (Just this service\'s siblings and parents)', 'Fix siblings and parents.', call ) )
            
            call = HydrusData.Call( self._DoSiblingsAndParents, CC.COMBINED_TAG_SERVICE_KEY )
            
            menu_items.append( ( 'normal', 'Hard-replace all applicable tags with their siblings and add missing parents. (All service siblings and parents)', 'Fix siblings and parents.', call ) )
            
            self._do_siblings_and_parents = ClientGUICommon.MenuBitmapButton( self._tags_box_sorter, CC.GlobalBMPs.family, menu_items )
            self._do_siblings_and_parents.SetToolTip( 'Hard-replace all applicable tags with their siblings and add missing parents.' )
            
            self._copy_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.GlobalBMPs.copy, self._Copy )
            self._copy_button.SetToolTip( 'Copy selected tags to the clipboard. If none are selected, copies all.' )
            
            self._paste_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.GlobalBMPs.paste, self._Paste )
            self._paste_button.SetToolTip( 'Paste newline-separated tags from the clipboard into here.' )
            
            self._show_deleted = False
            
            menu_items = []
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'add_parents_on_manage_tags' )
            
            menu_items.append( ( 'check', 'auto-add entered tags\' parents on add/pend action', 'If checked, adding any tag that has parents will also add those parents.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'replace_siblings_on_manage_tags' )
            
            menu_items.append( ( 'check', 'auto-replace entered siblings on add/pend action', 'If checked, adding any tag that has a sibling will instead add that sibling.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'allow_remove_on_manage_tags_input' )
            
            menu_items.append( ( 'check', 'allow remove/petition result on tag input for already existing tag', 'If checked, inputting a tag that already exists will try to remove it.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'yes_no_on_remove_on_manage_tags' )
            
            menu_items.append( ( 'check', 'confirm remove/petition tags on explicit delete actions', 'If checked, clicking the remove/petition tags button (or hitting the deleted key on the list) will first confirm the action with a yes/no dialog.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerCalls( self._FlipShowDeleted, lambda: self._show_deleted )
            
            menu_items.append( ( 'check', 'show deleted', 'Show deleted tags, if any.', check_manager ) )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                menu_items.append( ( 'separator', 0, 0, 0 ) )
                
                menu_items.append( ( 'normal', 'advanced operation', 'Perform an advanced tag operation on the files used to launch this manage tags panel.', self._AdvancedOperation ) )
                
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ):
                
                menu_items.append( ( 'separator', 0, 0, 0 ) )
                
                menu_items.append( ( 'normal', 'modify users who added the selected tags', 'Modify the users who added the selected tags.', self._ModifyMappers ) )
                
            
            self._cog_button = ClientGUICommon.MenuBitmapButton( self._tags_box_sorter, CC.GlobalBMPs.cog, menu_items )
            
            #
            
            expand_parents = True
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.AddTags, expand_parents, self._file_service_key, self._tag_service_key, null_entry_callable = self.OK )
            
            self._tags_box.ChangeTagService( self._tag_service_key )
            
            self.SetMedia( media )
            
            self._suggested_tags = ClientGUITagSuggestions.SuggestedTagsPanel( self, self._tag_service_key, self._media, self.AddTags, canvas_key = self._canvas_key )
            
            button_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            button_hbox.Add( self._remove_tags, CC.FLAGS_VCENTER )
            button_hbox.Add( self._do_siblings_and_parents, CC.FLAGS_VCENTER )
            button_hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
            button_hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
            button_hbox.Add( self._cog_button, CC.FLAGS_SIZER_CENTER )
            
            self._tags_box_sorter.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
            
            vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
            
            vbox.Add( self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._add_tag_box, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
            
            #
            
            hbox = ClientGUICommon.BetterBoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._suggested_tags, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE )
            hbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'main_gui' ] )
            
            self.SetSizer( hbox )
            
            if self._immediate_commit:
                
                HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
                
            
        
        def _EnterTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            tags = HydrusTags.CleanTags( tags )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
                
                forced_reason = 'admin'
                
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            currents = [ tag_manager.GetCurrent( self._tag_service_key ) for tag_manager in tag_managers ]
            pendings = [ tag_manager.GetPending( self._tag_service_key ) for tag_manager in tag_managers ]
            petitioneds = [ tag_manager.GetPetitioned( self._tag_service_key ) for tag_manager in tag_managers ]
            
            num_files = len( self._media )
            
            # let's figure out what these tags can mean for the media--add, remove, or what?
            
            choices = collections.defaultdict( list )
            
            for tag in tags:
                
                num_current = sum( ( 1 for current in currents if tag in current ) )
                
                if self._i_am_local_tag_service:
                    
                    if not only_remove:
                        
                        if num_current < num_files:
                            
                            num_non_current = num_files - num_current
                            
                            choices[ HC.CONTENT_UPDATE_ADD ].append( ( tag, num_non_current ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > 0:
                            
                            choices[ HC.CONTENT_UPDATE_DELETE ].append( ( tag, num_current ) )
                            
                        
                    
                else:
                    
                    num_pending = sum( ( 1 for pending in pendings if tag in pending ) )
                    num_petitioned = sum( ( 1 for petitioned in petitioneds if tag in petitioned ) )
                    
                    if not only_remove:
                        
                        if num_current + num_pending < num_files:
                            
                            num_pendable = num_files - ( num_current + num_pending )
                            
                            choices[ HC.CONTENT_UPDATE_PEND ].append( ( tag, num_pendable ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > num_petitioned and not only_add:
                            
                            num_petitionable = num_current - num_petitioned
                            
                            choices[ HC.CONTENT_UPDATE_PETITION ].append( ( tag, num_petitionable ) )
                            
                        
                        if num_pending > 0 and not only_add:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PEND ].append( ( tag, num_pending ) )
                            
                        
                    
                    if not only_remove:
                        
                        if num_petitioned > 0:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PETITION ].append( ( tag, num_petitioned ) )
                            
                        
                    
                
            
            if len( choices ) == 0:
                
                return
                
            
            # now we have options, let's ask the user what they want to do
            
            if len( choices ) == 1:
                
                [ ( choice_action, tag_counts ) ] = list(choices.items())
                
                tags = { tag for ( tag, count ) in tag_counts }
                
            else:
                
                bdc_choices = []
                
                preferred_order = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_RESCIND_PETITION ]
                
                choice_text_lookup = {}
                
                choice_text_lookup[ HC.CONTENT_UPDATE_ADD ] = 'add'
                choice_text_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'delete'
                choice_text_lookup[ HC.CONTENT_UPDATE_PEND ] = 'pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'petition'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'rescind pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'rescind petition'
                
                for choice_action in preferred_order:
                    
                    if choice_action not in choices:
                        
                        continue
                        
                    
                    choice_text_prefix = choice_text_lookup[ choice_action ]
                    
                    tag_counts = choices[ choice_action ]
                    
                    tags = { tag for ( tag, count ) in tag_counts }
                    
                    if len( tags ) == 1:
                        
                        [ ( tag, count ) ] = tag_counts
                        
                        text = choice_text_prefix + ' "' + tag + '" for ' + HydrusData.ToHumanInt( count ) + ' files'
                        
                    else:
                        
                        text = choice_text_prefix + ' ' + HydrusData.ToHumanInt( len( tags ) ) + ' tags'
                        
                    
                    data = ( choice_action, tags )
                    
                    if len( tag_counts ) > 25:
                        
                        t_c = tag_counts[:25]
                        
                        t_c_lines = [ tag + ' - ' + HydrusData.ToHumanInt( count ) + ' files' for ( tag, count ) in t_c ]
                        
                        t_c_lines.append( 'and ' + HydrusData.ToHumanInt( len( tag_counts ) - 25 ) + ' others' )
                        
                        tooltip = os.linesep.join( t_c_lines )
                        
                    else:
                        
                        tooltip = os.linesep.join( ( tag + ' - ' + HydrusData.ToHumanInt( count ) + ' files' for ( tag, count ) in tag_counts ) )
                        
                    
                    bdc_choices.append( ( text, data, tooltip ) )
                    
                
                try:
                    
                    ( choice_action, tags ) = ClientGUIDialogsQuick.SelectFromListButtons( self, 'What would you like to do?', bdc_choices )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
            reason = None
            
            if choice_action == HC.CONTENT_UPDATE_PETITION:
                
                if forced_reason is None:
                    
                    # add the easy reason buttons here
                    
                    if len( tags ) == 1:
                        
                        ( tag, ) = tags
                        
                        tag_text = '"' + tag + '"'
                        
                    else:
                        
                        tag_text = 'the ' + HydrusData.ToHumanInt( len( tags ) ) + ' tags'
                        
                    
                    message = 'Enter a reason for ' + tag_text + ' to be removed. A janitor will review your petition.'
                    
                    suggestions = []
                    
                    suggestions.append( 'mangled parse/typo' )
                    suggestions.append( 'not applicable' )
                    suggestions.append( 'should be namespaced' )
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            reason = dlg.GetValue()
                            
                        else:
                            
                            return
                            
                        
                    
                    # if this above sub-dialog occurs, the 'default focus' reverts to the main gui when the manage tags frame closes, wew lad
                    
                    ClientGUIFunctions.GetTLP( self ).GetParent().SetFocus()
                    self.SetFocus()
                    
                else:
                    
                    reason = forced_reason
                    
                
            
            # we have an action and tags, so let's effect the content updates
            
            content_updates_group = []
            
            recent_tags = set()
            
            for tag in tags:
                
                if choice_action == HC.CONTENT_UPDATE_ADD: media_to_affect = [ m for m in self._media if tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) ]
                elif choice_action == HC.CONTENT_UPDATE_DELETE: media_to_affect = [ m for m in self._media if tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) ]
                elif choice_action == HC.CONTENT_UPDATE_PEND: media_to_affect = [ m for m in self._media if tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) and tag not in m.GetTagsManager().GetPending( self._tag_service_key ) ]
                elif choice_action == HC.CONTENT_UPDATE_PETITION: media_to_affect = [ m for m in self._media if tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) and tag not in m.GetTagsManager().GetPetitioned( self._tag_service_key ) ]
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND: media_to_affect = [ m for m in self._media if tag in m.GetTagsManager().GetPending( self._tag_service_key ) ]
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION: media_to_affect = [ m for m in self._media if tag in m.GetTagsManager().GetPetitioned( self._tag_service_key ) ]
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                if len( hashes ) > 0:
                    
                    content_updates = []
                    
                    if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                        
                        if self._new_options.GetBoolean( 'replace_siblings_on_manage_tags' ):
                            
                            siblings_manager = HG.client_controller.tag_siblings_manager
                            
                            tag = siblings_manager.CollapseTag( self._tag_service_key, tag )
                            
                        
                        recent_tags.add( tag )
                        
                        if self._new_options.GetBoolean( 'add_parents_on_manage_tags' ):
                            
                            tag_parents_manager = HG.client_controller.tag_parents_manager
                            
                            parents = tag_parents_manager.GetParents( self._tag_service_key, tag )
                            
                            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( parent, hashes ) ) for parent in parents ) )
                            
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes ), reason = reason ) )
                    
                    if len( content_updates ) > 0:
                        
                        if not self._immediate_commit:
                            
                            for m in media_to_affect:
                                
                                mt = m.GetTagsManager()
                                
                                for content_update in content_updates:
                                    
                                    mt.ProcessContentUpdate( self._tag_service_key, content_update )
                                    
                                
                            
                        
                        content_updates_group.extend( content_updates )
                        
                    
                
            
            if len( recent_tags ) > 0 and HG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' ) is not None:
                
                HG.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            if len( content_updates_group ) > 0:
                
                if self._immediate_commit:
                    
                    service_keys_to_content_updates = { self._tag_service_key : content_updates_group }
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                else:
                    
                    self._groups_of_content_updates.append( content_updates_group )
                    
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def _AdvancedOperation( self ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            self.OK()
            
            # do this because of the OK() call, which doesn't want to happen in the dialog event loop
            def do_it():
                
                with ClientGUITopLevelWindows.DialogNullipotent( HG.client_controller.gui, 'advanced content update' ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsReview.AdvancedContentUpdatePanel( dlg, self._tag_service_key, hashes )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.ShowModal()
                    
                
            
            HG.client_controller.CallLaterWXSafe( HG.client_controller.gui, 0.5, do_it )
            
        
        def _Copy( self ):
            
            tags = list( self._tags_box.GetSelectedTags() )
            
            if len( tags ) == 0:
                
                ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._tag_service_key, collapse_siblings = False )
                
                tags = set( current_tags_to_count.keys() ).union( list(pending_tags_to_count.keys()) )    
                
            
            if len( tags ) > 0:
                
                tags = HydrusTags.SortNumericTags( tags )
                
                text = os.linesep.join( tags )
                
                HG.client_controller.pub( 'clipboard', 'text', text )
                
            
        
        def _DoSiblingsAndParents( self, service_key ):
            
            try:
                
                tag_siblings_manager = HG.client_controller.tag_siblings_manager
                
                tag_parents_manager = HG.client_controller.tag_parents_manager
                
                removee_tags_to_hashes = collections.defaultdict( list )
                addee_tags_to_hashes = collections.defaultdict( list )
                
                for m in self._media:
                    
                    hash = m.GetHash()
                    
                    tags_manager = m.GetTagsManager()
                    
                    tags = tags_manager.GetCurrent( self._tag_service_key ).union( tags_manager.GetPending( self._tag_service_key ) )
                    
                    sibling_correct_tags = tag_siblings_manager.CollapseTags( service_key, tags, service_strict = True )
                    
                    sibling_and_parent_correct_tags = tag_parents_manager.ExpandTags( service_key, sibling_correct_tags, service_strict = True )
                    
                    removee_tags = tags.difference( sibling_and_parent_correct_tags )
                    addee_tags = sibling_and_parent_correct_tags.difference( tags )
                    
                    for tag in removee_tags:
                        
                        removee_tags_to_hashes[ tag ].append( hash )
                        
                    
                    for tag in addee_tags:
                        
                        addee_tags_to_hashes[ tag ].append( hash )
                        
                    
                
                if len( removee_tags_to_hashes ) == 0 and len( addee_tags_to_hashes ) == 0:
                    
                    wx.MessageBox( 'No replacements seem to be needed.' )
                    
                    return
                    
                
                summary_message = 'The following changes will be made:'
                
                if len( removee_tags_to_hashes ) > 0:
                    
                    removee_tags_to_counts = { tag : len( hashes ) for ( tag, hashes ) in removee_tags_to_hashes.items() }
                    
                    removee_tags = list( removee_tags_to_counts.keys() )
                    
                    ClientTags.SortTags( CC.SORT_BY_INCIDENCE_DESC, removee_tags, removee_tags_to_counts )
                    
                    removee_tag_statements = [ '{} ({})'.format( tag, removee_tags_to_counts[ tag ] ) for tag in removee_tags ]
                    
                    if len( removee_tag_statements ) > 10:
                        
                        removee_tag_statements = removee_tag_statements[:10]
                        
                        removee_tag_statements.append( 'and more' )
                        
                    
                    summary_message += os.linesep * 2
                    summary_message += 'REMOVE: ' + ', '.join( removee_tag_statements )
                    
                
                if len( addee_tags_to_hashes ) > 0:
                    
                    addee_tags_to_counts = { tag : len( hashes ) for ( tag, hashes ) in addee_tags_to_hashes.items() }
                    
                    addee_tags = list( addee_tags_to_counts.keys() )
                    
                    ClientTags.SortTags( CC.SORT_BY_INCIDENCE_DESC, addee_tags, addee_tags_to_counts )
                    
                    addee_tag_statements = [ '{} ({})'.format( tag, addee_tags_to_counts[ tag ] ) for tag in addee_tags ]
                    
                    if len( addee_tag_statements ) > 10:
                        
                        addee_tag_statements = addee_tag_statements[:10]
                        
                        addee_tag_statements.append( 'and more' )
                        
                    
                    summary_message += os.linesep * 2
                    summary_message += 'ADD: ' + ', '.join( addee_tag_statements )
                    
                
                with ClientGUIDialogs.DialogYesNo( self, summary_message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
                if self._tag_service_key == CC.LOCAL_TAG_SERVICE_KEY:
                    
                    addee_action = HC.CONTENT_UPDATE_ADD
                    removee_action = HC.CONTENT_UPDATE_DELETE
                    reason = None
                    
                else:
                    
                    addee_action = HC.CONTENT_UPDATE_PEND
                    removee_action = HC.CONTENT_UPDATE_PETITION
                    reason = 'automatic sibling/parent replace from manage tags'
                    
                
                content_updates = []
                
                for ( tag, hashes ) in removee_tags_to_hashes.items():
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, removee_action, ( tag, hashes ), reason = reason ) )
                    
                
                for ( tag, hashes ) in addee_tags_to_hashes.items():
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, addee_action, ( tag, hashes ), reason = reason ) )
                    
                
                if not self._immediate_commit:
                    
                    hashes_to_tag_managers = { m.GetHash() : m.GetTagsManager() for m in self._media }
                    
                    for content_update in content_updates:
                        
                        hashes = content_update.GetHashes()
                        
                        for hash in hashes:
                            
                            if hash in hashes_to_tag_managers:
                                
                                hashes_to_tag_managers[ hash ].ProcessContentUpdate( self._tag_service_key, content_update )
                                
                            
                        
                    
                    self._groups_of_content_updates.append( content_updates )
                    
                else:
                    
                    service_keys_to_content_updates = { self._tag_service_key : content_updates }
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                self._tags_box.SetTagsByMedia( self._media, force_reload = True )
                
            finally:
                
                self._add_tag_box.SetFocus()
                
            
        
        def _FlipShowDeleted( self ):
            
            self._show_deleted = not self._show_deleted
            
            self._tags_box.SetShow( 'deleted', self._show_deleted )
            
        
        def _ModifyMappers( self ):
            
            wx.MessageBox( 'this does not work yet!' )
            
            return
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in self._media ) ) )
            
            for tag in tags:
                
                contents.extend( [ HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in hashes ] )
                
            
            if len( contents ) > 0:
                
                subject_accounts = 'blah' # fetch subjects from the server using the contents
                
                with ClientGUIDialogs.DialogModifyAccounts( self, self._tag_service_key, subject_accounts ) as dlg:
                    
                    dlg.ShowModal()
                    
                
            
        
        def _Paste( self ):
            
            try:
                
                text = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                wx.MessageBox( str( e ) )
                
                return
                
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( text )
                
                tags = HydrusTags.CleanTags( tags )
                
                self.AddTags( tags, only_add = True )
                
            except Exception as e:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        
        def _RemoveTagsButton( self ):
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tag_manager in tag_managers:
                
                removable_tags.update( tag_manager.GetCurrent( self._tag_service_key ) )
                removable_tags.update( tag_manager.GetPending( self._tag_service_key ) )
                
            
            selected_tags = list( self._tags_box.GetSelectedTags() )
            
            if len( selected_tags ) == 0:
                
                tags_to_remove = list( removable_tags )
                
            else:
                
                tags_to_remove = [ tag for tag in selected_tags if tag in removable_tags ]
                
            
            tags_to_remove = HydrusTags.SortNumericTags( tags_to_remove )
            
            self.RemoveTags( tags_to_remove )
            
        
        def AddTags( self, tags, only_add = False ):
            
            if not self._new_options.GetBoolean( 'allow_remove_on_manage_tags_input' ):
                
                only_add = True
                
            
            if len( tags ) > 0:
                
                self.EnterTags( tags, only_add = only_add )
                
            
        
        def CleanBeforeDestroy( self ):
            
            self._add_tag_box.CancelCurrentResultsFetchJob()
            
        
        def EnterTags( self, tags, only_add = False ):
            
            if len( tags ) > 0:
                
                self._EnterTags( tags, only_add = only_add )
                
            
        
        def GetGroupsOfContentUpdates( self ):
            
            return ( self._tag_service_key, self._groups_of_content_updates )
            
        
        def HasChanges( self ):
            
            return len( self._groups_of_content_updates ) > 0
            
        
        def OK( self ):
            
            # nice to have this happen immediately so the 'advanced content update' stuff can occur in a neat event order afterwards
            self.GetEventHandler().ProcessEvent( ClientGUITopLevelWindows.OKEvent( -1 ) )
            
            # old call:
            # wx.QueueEvent( self.GetEventHandler(), ClientGUITopLevelWindows.OKEvent( -1 ) )
            
        
        def ProcessApplicationCommand( self, command ):
            
            command_processed = True
            
            command_type = command.GetCommandType()
            data = command.GetData()
            
            if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
                
                action = data
                
                if action == 'set_search_focus':
                    
                    self.SetTagBoxFocus()
                    
                elif action in ( 'show_and_focus_manage_tags_favourite_tags', 'show_and_focus_manage_tags_related_tags', 'show_and_focus_manage_tags_file_lookup_script_tags', 'show_and_focus_manage_tags_recent_tags' ):
                    
                    self._suggested_tags.TakeFocusForUser( action )
                    
                else:
                    
                    command_processed = False
                    
                
            else:
                
                command_processed = False
                
            
            return command_processed
            
        
        def ProcessContentUpdates( self, service_keys_to_content_updates ):
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                for content_update in content_updates:
                    
                    for m in self._media:
                        
                        if len( m.GetHashes().intersection( content_update.GetHashes() ) ) > 0:
                            
                            m.GetMediaResult().ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def RemoveTags( self, tags ):
            
            if len( tags ) > 0:
                
                if self._new_options.GetBoolean( 'yes_no_on_remove_on_manage_tags' ):
                    
                    if len( tags ) < 10:
                        
                        message = 'Are you sure you want to remove these tags:'
                        message += os.linesep * 2
                        message += os.linesep.join( tags )
                        
                    else:
                        
                        message = 'Are you sure you want to remove these ' + HydrusData.ToHumanInt( len( tags ) ) + ' tags?'
                        
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES:
                            
                            return
                            
                        
                    
                
                self._EnterTags( tags, only_remove = True )
                
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = []
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.SetFocus()
            
        

class ManageTagCensorshipPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, initial_value = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.SetMinSize( ( min_width, -1 ) )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.COMBINED_TAG, HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, service_key, initial_value )
            
            select = name == 'all known tags'
            
            self._tag_services.AddPage( page, name, select = select )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = "Here you can set which tags or classes of tags you do not want to see. Input something like 'series:' to censor an entire namespace, or ':' for all namespaced tags, and the empty string (just hit enter with no text added) for all unnamespaced tags. You will have to refresh your current queries to see any changes."
        
        st = ClientGUICommon.BetterStaticText( self, intro )
        
        st.SetWrapWidth( min_width - 50 )
        
        
        
        vbox.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        info = [ page.GetInfo() for page in self._tag_services.GetPages() if page.HasInfo() ]
        
        HG.client_controller.Write( 'tag_censorship', info )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, initial_value = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            choice_pairs = [ ( 'blacklist', True ), ( 'whitelist', False ) ]
            
            self._blacklist = ClientGUICommon.RadioBox( self, 'type', choice_pairs )
            
            self._tags = ClientGUIListBoxes.ListBoxTagsCensorship( self )
            
            self._tag_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._tag_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownTag )
            
            #
            
            ( blacklist, tags ) = HG.client_controller.Read( 'tag_censorship', service_key )
            
            if blacklist: self._blacklist.SetSelection( 0 )
            else: self._blacklist.SetSelection( 1 )
            
            self._tags.AddTags( tags )
            
            if initial_value is not None:
                
                self._tag_input.SetValue( initial_value )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._blacklist, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._tag_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventKeyDownTag( self, event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                tag = self._tag_input.GetValue()
                
                self._tags.EnterTags( { tag } )
                
                self._tag_input.SetValue( '' )
                
            else:
                
                event.Skip()
                
            
        
        def GetInfo( self ):
            
            blacklist = self._blacklist.GetSelectedClientData()
            
            tags = self._tags.GetClientData()
            
            return ( self._service_key, blacklist, tags )
            
        
        def HasInfo( self ):
            
            ( service_key, blacklist, tags ) = self.GetInfo()
            
            return len( tags ) > 0
            
        
        def SetTagBoxFocus( self ):
            
            self._tag_input.SetFocus()
            
        
    
class ManageTagParents( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_repositories = ClientGUICommon.BetterNotebook( self )
        
        #
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        services = [ service for service in HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) if service.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION ) ]
        
        services.extend( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_repositories, service_key, tags )
            
            select = service_key == default_tag_repository_key
            
            self._tag_repositories.AddPage( page, name, select = select )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        if self._tag_repositories.GetCurrentPage().HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    raise HydrusExceptions.VetoException( 'Cancelled OK due to uncommitted pair.' )
                    
                
            
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus':
                
                self._SetSearchFocus()
                
            else:
                
                event.Skip()
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            if service_key != CC.LOCAL_TAG_SERVICE_KEY:
                
                self._service = HG.client_controller.services_manager.GetService( service_key )
                
            
            self._pairs_to_reasons = {}
            
            self._original_statuses_to_pairs = collections.defaultdict( set )
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._show_all = wx.CheckBox( self )
            
            listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( '', 6 ), ( 'child', 25 ), ( 'parent', -1 ) ]
            
            self._tag_parents = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'tag_parents', 8, 25, columns, self._ConvertPairToListCtrlTuples, delete_key_callback = self._ListCtrlActivated, activation_callback = self._ListCtrlActivated )
            
            listctrl_panel.SetListCtrl( self._tag_parents )
            
            self._tag_parents.Sort( 2 )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'from clipboard', 'Load parents from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, False ) ) )
            menu_items.append( ( 'normal', 'from clipboard (only add pairs--no deletions)', 'Load parents from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_items.append( ( 'normal', 'from .txt file', 'Load parents from a .txt file.', HydrusData.Call( self._ImportFromTXT, False ) ) )
            menu_items.append( ( 'normal', 'from .txt file (only add pairs--no deletions)', 'Load parents from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            listctrl_panel.AddMenuButton( 'import', menu_items )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'to clipboard', 'Save selected parents to your clipboard.', self._ExportToClipboard ) )
            menu_items.append( ( 'normal', 'to .txt file', 'Save selected parents to a .txt file.', self._ExportToTXT ) )
            
            listctrl_panel.AddMenuButton( 'export', menu_items, enabled_only_on_selection = True )
            
            self._children = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, show_sibling_text = False )
            self._parents = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, show_sibling_text = False )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._children, ( 12, 6 ) )
            
            self._children.SetInitialSize( ( -1, preview_height ) )
            self._parents.SetInitialSize( ( -1, preview_height ) )
            
            expand_parents = True
            
            self._child_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterChildren, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._child_input.Disable()
            
            self._parent_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterParents, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._parent_input.Disable()
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
            self._add.Disable()
            
            #
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self, 'initialising\u2026' + os.linesep + '.' )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            tags_box = wx.BoxSizer( wx.HORIZONTAL )
            
            tags_box.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
            tags_box.Add( self._parents, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            input_box = wx.BoxSizer( wx.HORIZONTAL )
            
            input_box.Add( self._child_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            input_box.Add( self._parent_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
            
            vbox.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._count_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._add, CC.FLAGS_LONE_BUTTON )
            vbox.Add( tags_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.Add( input_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
            #
            
            self._tag_parents.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._tag_parents.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            self.Bind( ClientGUIListBoxes.EVT_LIST_BOX, self.EventListBoxChanged )
            self._show_all.Bind( wx.EVT_CHECKBOX, self.EventShowAll )
            
            HG.client_controller.CallToThread( self.THREADInitialise, tags, self._service_key )
            
        
        def _AddPairs( self, pairs, add_only = False ):
            
            pairs = list( pairs )
            
            pairs.sort( key = lambda c_p: HydrusTags.ConvertTagToSortable( c_p[1] ) )
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for pair in pairs:
                
                if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    if not add_only:
                        
                        pending_pairs.append( pair )
                        
                    
                elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    petitioned_pairs.append( pair )
                    
                elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if not add_only:
                        
                        current_pairs.append( pair )
                        
                    
                elif self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            suggestions = []
            
            suggestions.append( 'obvious by definition (a sword is a weapon)' )
            suggestions.append( 'character/series/studio/etc... belonging (character x belongs to series y)' )
            suggestions.append( 'character/person/etc... properties (character x is a female)' )
            
            affected_pairs = []
            
            if len( new_pairs ) > 0:
            
                do_it = True
                
                if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                    
                    if self._service.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_OVERRULE ):
                        
                        reason = 'admin'
                        
                    else:
                        
                        if len( new_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in new_pairs ) )
                            
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                reason = dlg.GetValue()
                                
                            else:
                                
                                do_it = False
                                
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].update( new_pairs )
                    
                    affected_pairs.extend( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                        
                        
                        if len( current_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in current_pairs ) )
                            
                        
                        if len( current_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Already exist.'
                        else: message = 'The pair ' + pair_strings + ' already exists.'
                        
                        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'petition it', no_label = 'do nothing' ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_YES:
                                
                                if self._service.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_OVERRULE ):
                                    
                                    reason = 'admin'
                                    
                                else:
                                    
                                    message = 'Enter a reason for this pair to be removed. A janitor will review your petition.'
                                    
                                    with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK:
                                            
                                            reason = dlg.GetValue()
                                            
                                        else:
                                            
                                            do_it = False
                                            
                                        
                                    
                                
                                if do_it:
                                    
                                    for pair in current_pairs: self._pairs_to_reasons[ pair ] = reason
                                    
                                
                                
                            else:
                                
                                do_it = False
                                
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].update( current_pairs )
                        
                        affected_pairs.extend( current_pairs )
                        
                    
                
                if len( pending_pairs ) > 0:
                
                    if len( pending_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in pending_pairs ) )
                        
                    
                    if len( pending_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                    else: message = 'The pair ' + pair_strings + ' is pending.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].difference_update( pending_pairs )
                            
                            affected_pairs.extend( pending_pairs )
                            
                        
                    
                
                if len( petitioned_pairs ) > 0:
                
                    if len( petitioned_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in petitioned_pairs ) )
                        
                    
                    if len( petitioned_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                    else: message = 'The pair ' + pair_strings + ' is petitioned.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].difference_update( petitioned_pairs )
                            
                            affected_pairs.extend( petitioned_pairs )
                            
                        
                    
                
            
            if len( affected_pairs ) > 0:
                
                def in_current( pair ):
                    
                    for status in ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING, HC.CONTENT_STATUS_PETITIONED ):
                        
                        if pair in self._current_statuses_to_pairs[ status ]:
                            
                            return True
                            
                        
                        return False
                        
                    
                
                affected_pairs = [ ( self._tag_parents.HasData( pair ), in_current( pair ), pair ) for pair in affected_pairs ]
                
                to_add = [ pair for ( exists, current, pair ) in affected_pairs if not exists ]
                to_update = [ pair for ( exists, current, pair ) in affected_pairs if exists and current ]
                to_delete = [ pair for ( exists, current, pair ) in affected_pairs if exists and not current ]
                
                self._tag_parents.AddDatas( to_add )
                self._tag_parents.UpdateDatas( to_update )
                self._tag_parents.DeleteDatas( to_delete )
                
                self._tag_parents.Sort()
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_child, potential_parent ) = potential_pair
            
            if potential_child == potential_parent: return False
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_children = { child for ( child, parent ) in current_pairs }
            
            # test for loops
            
            if potential_parent in current_children:
                
                simple_children_to_parents = ClientCaches.BuildSimpleChildrenToParents( current_pairs )
                
                if ClientCaches.LoopInSimpleChildrenToParents( simple_children_to_parents, potential_child, potential_parent ):
                    
                    wx.MessageBox( 'Adding ' + potential_child + '->' + potential_parent + ' would create a loop!' )
                    
                    return False
                    
                
            
            return True
            
        
        def _ConvertPairToListCtrlTuples( self, pair ):
            
            ( child, parent ) = pair
            
            if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                
                status = HC.CONTENT_STATUS_PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                
                status = HC.CONTENT_STATUS_PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                
                status = HC.CONTENT_STATUS_CURRENT
                
            
            sign = HydrusData.ConvertStatusToPrefix( status )
            
            pretty_status = sign
            
            display_tuple = ( pretty_status, child, parent )
            sort_tuple = ( status, child, parent )
            
            return ( display_tuple, sort_tuple )
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                raise Exception( 'Uneven number of tags found!' )
                
            
            pairs = []
            
            for i in range( len( tags ) // 2 ):
                
                pair = ( tags[ 2 * i ], tags[ ( 2 * i ) + 1 ] )
                
                pairs.append( pair )
                
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            HG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with wx.FileDialog( self, 'Set the export path.', defaultFile = 'parents.txt', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_parents.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = os.linesep.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, add_only = False ):
            
            try:
                
                import_string = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                wx.MessageBox( str( e ) )
                
                return
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ImportFromTXT( self, add_only = False ):
            
            with wx.FileDialog( self, 'Select the file to import.', style = wx.FD_OPEN ) as dlg:
                
                if dlg.ShowModal() != wx.ID_OK:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ListCtrlActivated( self ):
            
            parents_to_children = collections.defaultdict( set )
            
            pairs = self._tag_parents.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._AddPairs( pairs )
                
            
        
        def _SetButtonStatus( self ):
            
            if len( self._children.GetTags() ) == 0 or len( self._parents.GetTags() ) == 0:
                
                self._add.Disable()
                
            else:
                
                self._add.Enable()
                
            
        
        def _UpdateListCtrlData( self ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            pertinent_tags = children.union( parents )
            
            self._tag_parents.DeleteDatas( self._tag_parents.GetData() )
            
            all_pairs = set()
            
            show_all = self._show_all.GetValue()
            
            for ( status, pairs ) in list(self._current_statuses_to_pairs.items()):
                
                if status == HC.CONTENT_STATUS_DELETED:
                    
                    continue
                    
                
                if len( pertinent_tags ) == 0:
                    
                    if status == HC.CONTENT_STATUS_CURRENT and not show_all:
                        
                        continue
                        
                    
                    # show all pending/petitioned
                    
                    all_pairs.update( pairs )
                    
                else:
                    
                    # show all appropriate
                    
                    for pair in pairs:
                        
                        ( a, b ) = pair
                        
                        if a in pertinent_tags or b in pertinent_tags or show_all:
                            
                            all_pairs.add( pair )
                            
                        
                    
                
            
            self._tag_parents.AddDatas( all_pairs )
            
            self._tag_parents.Sort()
            
        
        def EnterChildren( self, tags ):
            
            if len( tags ) > 0:
                
                self._parents.RemoveTags( tags )
                
                self._children.EnterTags( tags )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def EnterParents( self, tags ):
            
            if len( tags ) > 0:
                
                self._children.RemoveTags( tags )
                
                self._parents.EnterTags( tags )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def EventAddButton( self, event ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            pairs = list( itertools.product( children, parents ) )
            
            self._AddPairs( pairs )
            
            self._children.SetTags( [] )
            self._parents.SetTags( [] )
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
            event.Skip()
            
        
        def EventListBoxChanged( self, event ):
            
            self._UpdateListCtrlData()
            
        
        def EventShowAll( self, event ):
            
            self._UpdateListCtrlData()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            content_updates = []
            
            if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) )
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, pair ) )
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_key, content_updates )
            
        
        def HasUncommittedPair( self ):
            
            return len( self._children.GetTags() ) > 0 and len( self._parents.GetTags() ) > 0
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._children.GetTags() ) == 0: self._child_input.SetFocus()
            else: self._parent_input.SetFocus()
            
        
        def THREADInitialise( self, tags, service_key ):
            
            def wx_code( original_statuses_to_pairs, current_statuses_to_pairs ):
                
                if not self:
                    
                    return
                    
                
                self._original_statuses_to_pairs = original_statuses_to_pairs
                self._current_statuses_to_pairs = current_statuses_to_pairs
                
                self._status_st.SetLabelText( 'Files with a tag on the left will also be given the tag on the right.' + os.linesep + 'As an experiment, this panel will only display the \'current\' pairs for those tags entered below.' )
                self._count_st.SetLabelText( 'Starting with ' + HydrusData.ToHumanInt( len( original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ] ) ) + ' pairs.' )
                
                self._child_input.Enable()
                self._parent_input.Enable()
                
                if tags is None:
                    
                    self._UpdateListCtrlData()
                    
                else:
                    
                    self.EnterChildren( tags )
                    
                
            
            original_statuses_to_pairs = HG.client_controller.Read( 'tag_parents', service_key )
            
            current_statuses_to_pairs = collections.defaultdict( set )
            
            current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in list(original_statuses_to_pairs.items()) } )
            
            wx.CallAfter( wx_code, original_statuses_to_pairs, current_statuses_to_pairs )
            
        
    
class ManageTagSiblings( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_repositories = ClientGUICommon.BetterNotebook( self )
        
        #
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        services = [ service for service in HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) if service.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ) ]
        
        services.extend( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_repositories, service_key, tags )
            
            select = service_key == default_tag_repository_key
            
            self._tag_repositories.AddPage( page, name, select = select )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        if self._tag_repositories.GetCurrentPage().HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    raise HydrusExceptions.VetoException( 'Cancelled OK due to uncommitted pair.' )
                    
                
            
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus':
                
                self._SetSearchFocus()
                
            else:
                
                event.Skip()
                
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            wx.CallAfter( page.SetTagBoxFocus )
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                
                self._service = HG.client_controller.services_manager.GetService( service_key )
                
            
            self._original_statuses_to_pairs = collections.defaultdict( set )
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._pairs_to_reasons = {}
            
            self._current_new = None
            
            self._show_all = wx.CheckBox( self )
            
            listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( '', 6 ), ( 'old', 25 ), ( 'new', 25 ), ( 'note', -1 ) ]
            
            self._tag_siblings = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'tag_siblings', 8, 40, columns, self._ConvertPairToListCtrlTuples, delete_key_callback = self._ListCtrlActivated, activation_callback = self._ListCtrlActivated )
            
            listctrl_panel.SetListCtrl( self._tag_siblings )
            
            self._tag_siblings.Sort( 2 )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'from clipboard', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, False ) ) )
            menu_items.append( ( 'normal', 'from clipboard (only add pairs--no deletions)', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_items.append( ( 'normal', 'from .txt file', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, False ) ) )
            menu_items.append( ( 'normal', 'from .txt file (only add pairs--no deletions)', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            listctrl_panel.AddMenuButton( 'import', menu_items )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'to clipboard', 'Save selected siblings to your clipboard.', self._ExportToClipboard ) )
            menu_items.append( ( 'normal', 'to .txt file', 'Save selected siblings to a .txt file.', self._ExportToTXT ) )
            
            listctrl_panel.AddMenuButton( 'export', menu_items, enabled_only_on_selection = True )
            
            self._old_siblings = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, show_sibling_text = False )
            self._new_sibling = ClientGUICommon.BetterStaticText( self )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._old_siblings, ( 12, 6 ) )
            
            self._old_siblings.SetInitialSize( ( -1, preview_height ) )
            
            expand_parents = False
            
            self._old_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterOlds, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._old_input.Disable()
            
            self._new_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetNew, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            self._new_input.Disable()
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
            self._add.Disable()
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self, 'initialising\u2026' )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            new_sibling_box = wx.BoxSizer( wx.VERTICAL )
            
            new_sibling_box.Add( ( 10, 10 ), CC.FLAGS_EXPAND_BOTH_WAYS )
            new_sibling_box.Add( self._new_sibling, CC.FLAGS_EXPAND_PERPENDICULAR )
            new_sibling_box.Add( ( 10, 10 ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            text_box = wx.BoxSizer( wx.HORIZONTAL )
            
            text_box.Add( self._old_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            text_box.Add( new_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            input_box = wx.BoxSizer( wx.HORIZONTAL )
            
            input_box.Add( self._old_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            input_box.Add( self._new_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
            
            vbox.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._count_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._add, CC.FLAGS_LONE_BUTTON )
            vbox.Add( text_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.Add( input_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
            #
            
            self._tag_siblings.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._tag_siblings.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            self._show_all.Bind( wx.EVT_CHECKBOX, self.EventShowAll )
            self.Bind( ClientGUIListBoxes.EVT_LIST_BOX, self.EventListBoxChanged )
            
            HG.client_controller.CallToThread( self.THREADInitialise, tags, self._service_key )
            
        
        def _AddPairs( self, pairs, add_only = False, remove_only = False, default_reason = None ):
            
            pairs = list( pairs )
            
            pairs.sort( key = lambda c_p1: HydrusTags.ConvertTagToSortable( c_p1[1] ) )
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for pair in pairs:
                
                if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    if not add_only:
                        
                        pending_pairs.append( pair )
                        
                    
                elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    if not remove_only:
                        
                        petitioned_pairs.append( pair )
                        
                    
                elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if not add_only:
                        
                        current_pairs.append( pair )
                        
                    
                elif not remove_only and self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            suggestions = []
            
            suggestions.append( 'merging underscores/typos/phrasing/unnamespaced to a single uncontroversial good tag' )
            suggestions.append( 'rewording/namespacing based on preference' )
            
            if len( new_pairs ) > 0:
                
                do_it = True
                
                if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                    
                    if default_reason is not None:
                        
                        reason = default_reason
                        
                    elif self._service.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_OVERRULE ):
                        
                        reason = 'admin'
                        
                    else:
                        
                        if len( new_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in new_pairs ) )
                            
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                reason = dlg.GetValue()
                                
                            else:
                                
                                do_it = False
                                
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].update( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                        
                        if default_reason is not None:
                            
                            reason = default_reason
                            
                        elif self._service.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_OVERRULE ):
                            
                            reason = 'admin'
                            
                        else:
                            
                            if len( pending_pairs ) > 10:
                                
                                pair_strings = 'The many pairs you entered.'
                                
                            else:
                                
                                pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in pending_pairs ) )
                                
                            
                            message = 'Enter a reason for:'
                            message += os.linesep * 2
                            message += pair_strings
                            message += os.linesep * 2
                            message += 'to be removed. You will see the delete as soon as you upload, but a janitor will review your petition to decide if all users should receive it as well.'
                            
                            with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                                
                                if dlg.ShowModal() == wx.ID_OK:
                                    
                                    reason = dlg.GetValue()
                                    
                                else:
                                    
                                    do_it = False
                                    
                                
                            
                        
                        if do_it:
                            
                            for pair in current_pairs:
                                
                                self._pairs_to_reasons[ pair ] = reason
                                
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].update( current_pairs )
                        
                    
                
                if len( pending_pairs ) > 0:
                    
                    if len( pending_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in pending_pairs ) )
                        
                    
                    if len( pending_pairs ) > 1:
                        
                        message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                        
                    else:
                        
                        message = 'The pair ' + pair_strings + ' is pending.'
                        
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].difference_update( pending_pairs )
                            
                        
                    
                
                if len( petitioned_pairs ) > 0:
                
                    if len( petitioned_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = ', '.join( ( old + '->' + new for ( old, new ) in petitioned_pairs ) )
                        
                    
                    if len( petitioned_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                    else: message = 'The pair ' + pair_strings + ' is petitioned.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].difference_update( petitioned_pairs )
                            
                        
                    
                
            
        
        def _AutoPetitionConflicts( self, pairs ):
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_olds_to_news = dict( current_pairs )
            
            current_olds = { current_old for ( current_old, current_new ) in current_pairs }
            
            pairs_to_auto_petition = set()
            
            for ( old, new ) in pairs:
                
                if old in current_olds:
                    
                    conflicting_new = current_olds_to_news[ old ]
                    
                    if conflicting_new != new:
                        
                        conflicting_pair = ( old, conflicting_new )
                        
                        pairs_to_auto_petition.add( conflicting_pair )
                        
                    
                
            
            if len( pairs_to_auto_petition ) > 0:
                
                pairs_to_auto_petition = list( pairs_to_auto_petition )
                
                self._AddPairs( pairs_to_auto_petition, remove_only = True, default_reason = 'AUTO-PETITION TO REASSIGN TO: ' + new )
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_old, potential_new ) = potential_pair
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_olds = { old for ( old, new ) in current_pairs }
            
            # test for ambiguity
            
            if potential_old in current_olds:
                
                wx.MessageBox( 'There already is a relationship set for the tag ' + potential_old + '.' )
                
                return False
                
            
            # test for loops
            
            if potential_new in current_olds:
                
                seen_tags = set()
                
                d = dict( current_pairs )
                
                next_new = potential_new
                
                while next_new in d:
                    
                    next_new = d[ next_new ]
                    
                    if next_new == potential_old:
                        
                        wx.MessageBox( 'Adding ' + potential_old + '->' + potential_new + ' would create a loop!' )
                        
                        return False
                        
                    
                    if next_new in seen_tags:
                        
                        message = 'The pair you mean to add seems to connect to a sibling loop already in your database! Please undo this loop first. The tags involved in the loop are:'
                        message += os.linesep * 2
                        message += ', '.join( seen_tags )
                        
                        wx.MessageBox( message )
                        
                        return False
                        
                    
                    seen_tags.add( next_new )
                    
                
            
            return True
            
        
        def _ConvertPairToListCtrlTuples( self, pair ):
            
            ( old, new ) = pair
            
            if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                
                status = HC.CONTENT_STATUS_PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                
                status = HC.CONTENT_STATUS_PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                
                status = HC.CONTENT_STATUS_CURRENT
                
            
            sign = HydrusData.ConvertStatusToPrefix( status )
            
            pretty_status = sign
            
            existing_olds = self._old_siblings.GetTags()
            
            note = ''
            
            if old in existing_olds:
                
                if status == HC.CONTENT_STATUS_PENDING:
                    
                    note = 'CONFLICT: Will be rescinded on add.'
                    
                elif status == HC.CONTENT_STATUS_CURRENT:
                    
                    note = 'CONFLICT: Will be petitioned/deleted on add.'
                    
                
            
            display_tuple = ( pretty_status, old, new, note )
            sort_tuple = ( status, old, new, note )
            
            return ( display_tuple, sort_tuple )
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                raise Exception( 'Uneven number of tags found!' )
                
            
            pairs = []
            
            for i in range( len( tags ) // 2 ):
                
                pair = ( tags[ 2 * i ], tags[ ( 2 * i ) + 1 ] )
                
                pairs.append( pair )
                
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            HG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with wx.FileDialog( self, 'Set the export path.', defaultFile = 'siblings.txt', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_siblings.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = os.linesep.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, add_only = False ):
            
            try:
                
                import_string = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                wx.MessageBox( str( e ) )
                
                return
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AutoPetitionConflicts( pairs )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ImportFromTXT( self, add_only = False ):
            
            with wx.FileDialog( self, 'Select the file to import.', style = wx.FD_OPEN ) as dlg:
                
                if dlg.ShowModal() != wx.ID_OK:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AutoPetitionConflicts( pairs )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ListCtrlActivated( self ):
            
            pairs = self._tag_siblings.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._AddPairs( pairs )
                
            
            self._UpdateListCtrlData()
            
        
        def _SetButtonStatus( self ):
            
            if self._current_new is None or len( self._old_siblings.GetTags() ) == 0:
                
                self._add.Disable()
                
            else:
                
                self._add.Enable()
                
            
        
        def _UpdateListCtrlData( self ):
            
            olds = self._old_siblings.GetTags()
            
            pertinent_tags = set( olds )
            
            if self._current_new is not None:
                
                pertinent_tags.add( self._current_new )
                
            
            self._tag_siblings.DeleteDatas( self._tag_siblings.GetData() )
            
            all_pairs = set()
            
            show_all = self._show_all.GetValue()
            
            for ( status, pairs ) in self._current_statuses_to_pairs.items():
                
                if status == HC.CONTENT_STATUS_DELETED:
                    
                    continue
                    
                
                if len( pertinent_tags ) == 0:
                    
                    if status == HC.CONTENT_STATUS_CURRENT and not show_all:
                        
                        continue
                        
                    
                    # show all pending/petitioned
                    
                    all_pairs.update( pairs )
                    
                else:
                    
                    # show all appropriate
                    
                    for pair in pairs:
                        
                        ( a, b ) = pair
                        
                        if a in pertinent_tags or b in pertinent_tags or show_all:
                            
                            all_pairs.add( pair )
                            
                        
                    
                
            
            self._tag_siblings.AddDatas( all_pairs )
            
            self._tag_siblings.Sort()
            
        
        def EnterOlds( self, olds ):
            
            if self._current_new in olds:
                
                self.SetNew( set() )
                
            
            self._old_siblings.EnterTags( olds )
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def EventAddButton( self, event ):
            
            if self._current_new is not None and len( self._old_siblings.GetTags() ) > 0:
                
                olds = self._old_siblings.GetTags()
                
                pairs = [ ( old, self._current_new ) for old in olds ]
                
                self._AutoPetitionConflicts( pairs )
                
                self._AddPairs( pairs )
                
                self._old_siblings.SetTags( set() )
                self.SetNew( set() )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
            event.Skip()
            
        
        def EventListBoxChanged( self, event ):
            
            self._UpdateListCtrlData()
            
        
        def EventShowAll( self, event ):
            
            self._UpdateListCtrlData()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            # actually, we don't do this for siblings, but we do for parents, and let's have them be the same
            
            content_updates = []
            
            if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) )
                    
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, pair ) )
                    
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_key, content_updates )
            
        
        def HasUncommittedPair( self ):
            
            return len( self._old_siblings.GetTags() ) > 0 and self._current_new is not None
            
        
        def SetNew( self, new_tags ):
            
            if len( new_tags ) == 0:
                
                self._new_sibling.SetLabelText( '' )
                
                self._current_new = None
                
            else:
                
                new = list( new_tags )[0]
                
                self._old_siblings.RemoveTags( { new } )
                
                self._new_sibling.SetLabelText( new )
                
                self._current_new = new
                
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._old_siblings.GetTags() ) == 0:
                
                self._old_input.SetFocus()
                
            else:
                
                self._new_input.SetFocus()
                
            
        
        def THREADInitialise( self, tags, service_key ):
            
            def wx_code( original_statuses_to_pairs, current_statuses_to_pairs ):
                
                if not self:
                    
                    return
                    
                
                self._original_statuses_to_pairs = original_statuses_to_pairs
                self._current_statuses_to_pairs = current_statuses_to_pairs
                
                self._status_st.SetLabelText( 'Tags on the left will be replaced by those on the right.' )
                self._count_st.SetLabelText( 'Starting with ' + HydrusData.ToHumanInt( len( original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ] ) ) + ' pairs.' )
                
                self._old_input.Enable()
                self._new_input.Enable()
                
                if tags is None:
                    
                    self._UpdateListCtrlData()
                    
                else:
                    
                    self.EnterOlds( tags )
                    
                
            
            original_statuses_to_pairs = HG.client_controller.Read( 'tag_siblings', service_key )
            
            current_statuses_to_pairs = collections.defaultdict( set )
            
            current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in original_statuses_to_pairs.items() } )
            
            wx.CallAfter( wx_code, original_statuses_to_pairs, current_statuses_to_pairs )
            
        
    
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
        
    
    def SetValue( self, tag_filter ):
        
        self._tag_filter = tag_filter
        
        self._UpdateLabel()
        
    
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
