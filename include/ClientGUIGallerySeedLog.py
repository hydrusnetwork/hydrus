import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListCtrl
import ClientGUIMenus
import ClientGUISerialisable
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import ClientImportGallerySeeds
import ClientPaths
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusPaths
import HydrusText
import os
import wx

class EditGallerySeedLogPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, controller, read_only, gallery_seed_log ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._controller = controller
        self._read_only = read_only
        self._gallery_seed_log = gallery_seed_log
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on gallery_seed add/remove
        
        columns = [ ( '#', 3 ), ( 'url', -1 ), ( 'status', 12 ), ( 'added', 23 ), ( 'last modified', 23 ), ( 'note', 20 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self, 'gallery_seed_log', 30, 30, columns, self._ConvertGallerySeedToListCtrlTuples, delete_key_callback = self._DeleteSelected )
        
        #
        
        self._list_ctrl.AddDatas( self._gallery_seed_log.GetGallerySeeds() )
        
        self._list_ctrl.Sort( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._list_ctrl.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self._controller.sub( self, 'NotifyGallerySeedsUpdated', 'gallery_seed_log_gallery_seeds_updated' )
        
        wx.CallAfter( self._UpdateText )
        
    
    def _ConvertGallerySeedToListCtrlTuples( self, gallery_seed ):
        
        try:
            
            gallery_seed_index = self._gallery_seed_log.GetGallerySeedIndex( gallery_seed )
            
        except:
            
            gallery_seed_index = '--'
            
        
        url = gallery_seed.url
        status = gallery_seed.status
        added = gallery_seed.created
        modified = gallery_seed.modified
        note = gallery_seed.note
        
        pretty_gallery_seed_index = HydrusData.ToHumanInt( gallery_seed_index )
        pretty_url = url
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.TimestampToPrettyTimeDelta( added )
        pretty_modified = HydrusData.TimestampToPrettyTimeDelta( modified )
        pretty_note = note.split( os.linesep )[0]
        
        display_tuple = ( pretty_gallery_seed_index, pretty_url, pretty_status, pretty_added, pretty_modified, pretty_note )
        sort_tuple = ( gallery_seed_index, url, status, added, modified, note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedGalleryURLs( self ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( ( gallery_seed.url for gallery_seed in gallery_seeds ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for gallery_seed in self._list_ctrl.GetData( only_selected = True ):
            
            note = gallery_seed.note
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        if self._read_only:
            
            return
            
        
        gallery_seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete all the selected entries?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._gallery_seed_log.RemoveGallerySeeds( gallery_seeds_to_delete )
                    
                
            
        
    
    def _OpenSelectedGalleryURLs( self ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds ) > 0:
            
            if len( gallery_seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
            
            for gallery_seed in gallery_seeds:
                
                ClientPaths.LaunchURLInWebBrowser( gallery_seed.url )
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        for gallery_seed in gallery_seeds:
            
            gallery_seed.SetStatus( status_to_set )
            
        
        self._gallery_seed_log.NotifyGallerySeedsUpdated( gallery_seeds )
        
    
    def _ShowMenuIfNeeded( self ):
        
        selected_gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected_gallery_seeds ) > 0:
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy urls', 'Copy all the selected urls to clipboard.', self._CopySelectedGalleryURLs )
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open urls', 'Open all the selected urls in your web browser.', self._OpenSelectedGalleryURLs )
            
            if not self._read_only:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'try again', 'Reset the progress of all the selected urls.', HydrusData.Call( self._SetSelected, CC.STATUS_UNKNOWN ) )
                ClientGUIMenus.AppendMenuItem( self, menu, 'skip', 'Skip all the selected urls.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete from list', 'Remove all the selected urls.', self._DeleteSelected )
                
            
            HG.client_controller.PopupMenu( self, menu )
            
        
    
    def _UpdateListCtrl( self, gallery_seeds ):
        
        gallery_seeds_to_add = []
        gallery_seeds_to_update = []
        gallery_seeds_to_delete = []
        
        for gallery_seed in gallery_seeds:
            
            if self._gallery_seed_log.HasGallerySeed( gallery_seed ):
                
                if self._list_ctrl.HasData( gallery_seed ):
                    
                    gallery_seeds_to_update.append( gallery_seed )
                    
                else:
                    
                    gallery_seeds_to_add.append( gallery_seed )
                    
                
            else:
                
                if self._list_ctrl.HasData( gallery_seed ):
                    
                    gallery_seeds_to_delete.append( gallery_seed )
                    
                
            
        
        self._list_ctrl.DeleteDatas( gallery_seeds_to_delete )
        
        if len( gallery_seeds_to_add ) > 0:
            
            self._list_ctrl.AddDatas( gallery_seeds_to_add )
            
            # if gallery_seeds are inserted, then all subsequent indices need to be shuffled up, hence just update all here
            
            self._list_ctrl.UpdateDatas()
            
        else:
            
            self._list_ctrl.UpdateDatas( gallery_seeds_to_update )
            
        
    
    def _UpdateText( self ):
        
        ( status, ( total_processed, total ) ) = self._gallery_seed_log.GetStatus()
        
        self._text.SetLabelText( status )
        
        self.Layout()
        
    
    def EventShowMenu( self, event ):
        
        wx.CallAfter( self._ShowMenuIfNeeded )
        
        event.Skip() # let the right click event go through before doing menu, in case selection should happen
        
    
    def GetValue( self ):
        
        return self._gallery_seed_log
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seed_log_key, gallery_seeds ):
        
        if gallery_seed_log_key == self._gallery_seed_log.GetGallerySeedLogKey():
            
            self._UpdateText()
            self._UpdateListCtrl( gallery_seeds )
            
        
    
class GallerySeedLogButton( ClientGUICommon.BetterBitmapButton ):
    
    def __init__( self, parent, controller, read_only, gallery_seed_log_get_callable, gallery_seed_log_set_callable = None ):
        
        ClientGUICommon.BetterBitmapButton.__init__( self, parent, CC.GlobalBMPs.listctrl, self._ShowGallerySeedLogFrame )
        
        self._controller = controller
        self._read_only = read_only
        self._gallery_seed_log_get_callable = gallery_seed_log_get_callable
        self._gallery_seed_log_set_callable = gallery_seed_log_set_callable
        
        self.SetToolTip( 'open detailed gallery log--right-click for quick actions, if applicable' )
        
        if not self._read_only:
            
            self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
            
        
    
    def _ClearGallerySeeds( self, statuses_to_remove ):
        
        message = 'Are you sure you want to delete all the ' + '/'.join( ( CC.status_string_lookup[ status ] for status in statuses_to_remove ) ) + ' gallery log entries? This is useful for cleaning up and de-laggifying a very large list, but be careful you aren\'t removing something you would want to revisit.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                gallery_seed_log = self._gallery_seed_log_get_callable()
                
                gallery_seed_log.RemoveGallerySeedsByStatus( statuses_to_remove )
                
            
        
    
    def _GetExportableURLsString( self ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        gallery_seeds = gallery_seed_log.GetGallerySeeds()
        
        urls = [ gallery_seed.url for gallery_seed in gallery_seeds ]
        
        return os.linesep.join( urls )
        
    
    def _GetURLsFromURLsString( self, urls_string ):
        
        urls_string = HydrusData.ToUnicode( urls_string )
        
        urls = HydrusText.DeserialiseNewlinedTexts( urls_string )
        
        return urls
        
    
    def _ImportFromClipboard( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        urls = self._GetURLsFromURLsString( raw_text )
        
        try:
            
            self._ImportURLs( urls )
            
        except:
            
            wx.MessageBox( 'Could not import!' )
            
            raise
            
        
    
    def _ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png with the urls', wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                payload = ClientSerialisable.LoadFromPng( path )
                
                try:
                    
                    urls = self._GetURLsFromURLsString( payload )
                    
                    self._ImportURLs( urls )
                    
                except:
                    
                    wx.MessageBox( 'Could not import!' )
                    
                    raise
                    
                
            
        
    
    def _ImportURLs( self, urls ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        filtered_urls = [ url for url in urls if not gallery_seed_log.HasGalleryURL( url ) ]
        
        urls_to_add = urls
        
        if len( filtered_urls ) < urls:
            
            num_urls = len( urls )
            num_removed = num_urls - len( filtered_urls )
            
            message = 'Of the ' + HydrusData.ToHumanInt( num_urls ) + ' URLs you mean to add, ' + HydrusData.ToHumanInt( num_removed ) + ' are already in the gallery log. Would you like to only add new URLs or add everything (which will force a re-check of the duplicates)?'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'only add new urls', no_label = 'add all urls, even duplicates' ) as dlg:
                
                result = dlg.ShowModal()
                
                if result == wx.ID_YES:
                    
                    urls_to_add = filtered_urls
                    
                elif result == wx.ID_CANCEL:
                    
                    return
                    
                
            
        
        message = 'Would you like the URLs you are adding to be checked for just files, or would you like them to also follow subsequent gallery pages, like a regular search would?'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'just check what I am adding', no_label = 'start a potential new search for every url added' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_CANCEL:
                
                return
                
            
            can_generate_more_pages = result == wx.ID_NO
            
        
        gallery_seeds = [ ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = can_generate_more_pages ) for url in urls_to_add ]
        
        gallery_seed_log.AddGallerySeeds( gallery_seeds )
        
    
    def _ExportToPng( self ):
        
        payload = self._GetExportableURLsString()
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
            
            panel = ClientGUISerialisable.PngExportPanel( dlg, payload )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ExportToClipboard( self ):
        
        payload = self._GetExportableURLsString()
        
        HG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _RetryErrors( self ):
        
        message = 'Are you sure you want to retry all the files that encountered errors?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                gallery_seed_log = self._gallery_seed_log_get_callable()
                
                gallery_seed_log.RetryFailures()
                
            
        
    
    def _ShowGallerySeedLogFrame( self ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        tlp = ClientGUICommon.GetTLP( self )
        
        if isinstance( tlp, wx.Dialog ):
            
            if self._gallery_seed_log_set_callable is None: # throw up a dialog that edits the gallery_seed log in place
                
                with ClientGUITopLevelWindows.DialogNullipotent( self, 'gallery import log' ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._controller, self._read_only, gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.ShowModal()
                    
                
            else: # throw up a dialog that edits the gallery_seed log but can be cancelled
                
                dupe_gallery_seed_log = gallery_seed_log.Duplicate()
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'gallery import log' ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._controller, self._read_only, dupe_gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        self._gallery_seed_log_set_callable( dupe_gallery_seed_log )
                        
                    
                
            
        else: # throw up a frame that edits the gallery_seed log in place
            
            title = 'gallery import log'
            frame_key = 'gallery_import_log'
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditGallerySeedLogPanel( frame, self._controller, self._read_only, gallery_seed_log )
            
            frame.SetPanel( panel )
            
        
    
    def EventShowMenu( self, event ):
        
        menu = wx.Menu()
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        num_gallery_seeds = len( gallery_seed_log )
        num_successful = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SUCCESSFUL_AND_NEW )
        num_vetoed = gallery_seed_log.GetGallerySeedCount( CC.STATUS_VETOED )
        num_errors = gallery_seed_log.GetGallerySeedCount( CC.STATUS_ERROR )
        num_skipped = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SKIPPED )
        
        if num_errors > 0:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'retry ' + HydrusData.ToHumanInt( num_errors ) + ' error failures', 'Tell this log to reattempt all its error failures.', self._RetryErrors )
            
        
        if num_vetoed > 0:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'retry ' + HydrusData.ToHumanInt( num_errors ) + ' ignored', 'Tell this log to reattempt all its ignored/vetoed results.', self._RetryIgnored )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if num_successful > 0:
            
            num_deletees = num_successful
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ToHumanInt( num_deletees ) + ' successful gallery urls from the queue', 'Tell this log to clear out successful gallery page urls, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_SUCCESSFUL_AND_NEW, ) )
            
        
        if num_vetoed > 0:
            
            num_deletees = num_vetoed
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ToHumanInt( num_deletees ) + ' ignored gallery urls from the queue', 'Tell this log to clear out ignored gallery urls, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_VETOED, ) )
            
        
        if num_errors + num_skipped > 0:
            
            num_deletees = num_errors + num_skipped
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ToHumanInt( num_deletees ) + ' error/skipped gallery urls from the queue', 'Tell this log to clear out errored and skipped gallery urls, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_ERROR, CC.STATUS_SKIPPED ) )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( gallery_seed_log ) > 0:
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'to clipboard', 'Copy all the urls in this list to the clipboard.', self._ExportToClipboard )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'to png', 'Export all the urls in this list to a png file.', self._ExportToPng )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'export all urls' )
            
        
        submenu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, submenu, 'from clipboard', 'Import new urls to this list from the clipboard.', self._ImportFromClipboard )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'from png', 'Import new urls to this list from a png file.', self._ImportFromPng )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'import new urls' )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class GallerySeedLogStatusControl( wx.Panel ):
    
    def __init__( self, parent, controller, read_only, page_key = None ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._controller = controller
        self._read_only = read_only
        self._page_key = page_key
        
        self._gallery_seed_log = None
        
        self._log_summary_st = ClientGUICommon.BetterStaticText( self, style = wx.ST_ELLIPSIZE_END )
        
        self._gallery_seed_log_button = GallerySeedLogButton( self, self._controller, self._read_only, self._GetGallerySeedLog )
        
        #
        
        self._Update()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._log_summary_st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._gallery_seed_log_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        #
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def _Update( self ):
        
        if self._gallery_seed_log is None:
            
            self._log_summary_st.SetLabelText( '' )
            
            if self._gallery_seed_log_button.IsEnabled():
                
                self._gallery_seed_log_button.Disable()
                
            
        else:
            
            ( import_summary, ( num_done, num_to_do ) ) = self._gallery_seed_log.GetStatus()
            
            self._log_summary_st.SetLabelText( import_summary )
            
            if not self._gallery_seed_log_button.IsEnabled():
                
                self._gallery_seed_log_button.Enable()
                
            
        
    
    def SetGallerySeedLog( self, gallery_seed_log ):
        
        if not self:
            
            return
            
        
        self._gallery_seed_log = gallery_seed_log
        
    
    def TIMERUIUpdate( self ):
        
        if self._controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
