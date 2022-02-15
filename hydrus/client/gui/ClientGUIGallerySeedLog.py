import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientPaths
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImportGallerySeeds

class EditGallerySeedLogPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, controller, read_only, can_generate_more_pages, gallery_seed_log ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._controller = controller
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._gallery_seed_log = gallery_seed_log
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on gallery_seed add/remove
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_GALLERY_SEED_LOG.ID, 30, self._ConvertGallerySeedToListCtrlTuples, delete_key_callback = self._DeleteSelected )
        
        #
        
        self._list_ctrl.AddDatas( self._gallery_seed_log.GetGallerySeeds() )
        
        self._list_ctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._list_ctrl.AddMenuCallable( self._GetListCtrlMenu )
        
        self._controller.sub( self, 'NotifyGallerySeedsUpdated', 'gallery_seed_log_gallery_seeds_updated' )
        
        QP.CallAfter( self._UpdateText )
        
    
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
        pretty_added = ClientData.TimestampToPrettyTimeDelta( added )
        pretty_modified = ClientData.TimestampToPrettyTimeDelta( modified )
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
        
        gallery_seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete the {} selected entries? This is only useful if you have a really really huge list.'.format( HydrusData.ToHumanInt( len( gallery_seeds_to_delete ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.Accepted:
                
                self._gallery_seed_log.RemoveGallerySeeds( gallery_seeds_to_delete )
                
            
        
    
    def _GetListCtrlMenu( self ):
        
        selected_gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected_gallery_seeds ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = QW.QMenu()

        ClientGUIMenus.AppendMenuItem( menu, 'copy urls', 'Copy all the selected urls to clipboard.', self._CopySelectedGalleryURLs )
        ClientGUIMenus.AppendMenuItem( menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
        
        ClientGUIMenus.AppendSeparator( menu )

        ClientGUIMenus.AppendMenuItem( menu, 'open urls', 'Open all the selected urls in your web browser.', self._OpenSelectedGalleryURLs )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if not self._read_only:
            
            ClientGUIMenus.AppendMenuItem( menu, 'try again (just this one page)', 'Schedule this url to occur again.', HydrusData.Call( self._TrySelectedAgain, False ) )
            
            if self._can_generate_more_pages:
                ClientGUIMenus.AppendMenuItem( menu, 'try again (and allow search to continue)', 'Schedule this url to occur again and continue.', HydrusData.Call( self._TrySelectedAgain, True ) )

        ClientGUIMenus.AppendMenuItem( menu, 'skip', 'Skip all the selected urls.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
        
        return menu
        
    
    def _OpenSelectedGalleryURLs( self ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds ) > 0:
            
            if len( gallery_seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return
                    
                
            
            for gallery_seed in gallery_seeds:
                
                ClientPaths.LaunchURLInWebBrowser( gallery_seed.url )
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        for gallery_seed in gallery_seeds:
            
            gallery_seed.SetStatus( status_to_set )
            
        
        self._gallery_seed_log.NotifyGallerySeedsUpdated( gallery_seeds )
        
    
    def _TrySelectedAgain( self, can_generate_more_pages ):
        
        new_gallery_seeds = []
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        for gallery_seed in gallery_seeds:
            
            new_gallery_seeds.append( gallery_seed.GenerateRestartedDuplicate( can_generate_more_pages ) )
            
        
        self._gallery_seed_log.AddGallerySeeds( new_gallery_seeds )
        self._gallery_seed_log.NotifyGallerySeedsUpdated( new_gallery_seeds )
        
    
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
        
        self._text.setText( status )
        
    
    def GetValue( self ):
        
        return self._gallery_seed_log
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seed_log_key, gallery_seeds ):
        
        if gallery_seed_log_key == self._gallery_seed_log.GetGallerySeedLogKey():
            
            self._UpdateText()
            self._UpdateListCtrl( gallery_seeds )
            
        
    
class GallerySeedLogButton( ClientGUICommon.ButtonWithMenuArrow ):
    
    def __init__( self, parent, controller, read_only, can_generate_more_pages, gallery_type_string, gallery_seed_log_get_callable, gallery_seed_log_set_callable = None ):
        
        self._controller = controller
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._gallery_type_string = gallery_type_string
        self._gallery_seed_log_get_callable = gallery_seed_log_get_callable
        self._gallery_seed_log_set_callable = gallery_seed_log_set_callable
        
        action = QW.QAction()
        
        action.setText( '{} log'.format( gallery_type_string ) )
        action.setToolTip( 'open detailed {} log'.format( self._gallery_type_string ) )
        
        action.triggered.connect( self._ShowGallerySeedLogFrame )
        
        ClientGUICommon.ButtonWithMenuArrow.__init__( self, parent, action )
        
    
    def _PopulateMenu( self, menu ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        num_successful = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SUCCESSFUL_AND_NEW )
        num_vetoed = gallery_seed_log.GetGallerySeedCount( CC.STATUS_VETOED )
        num_errors = gallery_seed_log.GetGallerySeedCount( CC.STATUS_ERROR )
        num_skipped = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SKIPPED )
        
        if num_successful > 0:
            
            ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'successful\' gallery log entries from the log'.format( HydrusData.ToHumanInt( num_successful ) ), 'Tell this log to clear out successful records, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_SUCCESSFUL_AND_NEW, ) )
            
        
        if num_errors > 0:
            
            ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'failed\' gallery log entries from the log'.format( HydrusData.ToHumanInt( num_errors ) ), 'Tell this log to clear out errored records, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_ERROR, ) )
            
        
        if num_vetoed > 0:
            
            ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'ignored\' gallery log entries from the log'.format( HydrusData.ToHumanInt( num_vetoed ) ), 'Tell this log to clear out ignored records, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_VETOED, ) )
            
        
        if num_skipped > 0:
            
            ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'skipped\' gallery log entries from the log'.format( HydrusData.ToHumanInt( num_skipped ) ), 'Tell this log to clear out skipped records, reducing the size of the queue.', self._ClearGallerySeeds, ( CC.STATUS_SKIPPED, ) )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( gallery_seed_log ) > 0:
            
            if not self._read_only and gallery_seed_log.CanRestartFailedSearch():
                
                ClientGUIMenus.AppendMenuItem( menu, 'restart and resume failed search', 'Requeue the last failed attempt and resume search from there.', gallery_seed_log.RestartFailedSearch )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            submenu = QW.QMenu( menu )

            ClientGUIMenus.AppendMenuItem( submenu, 'to clipboard', 'Copy all the urls in this list to the clipboard.', self._ExportToClipboard )
            ClientGUIMenus.AppendMenuItem( submenu, 'to png', 'Export all the urls in this list to a png file.', self._ExportToPNG )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'export all urls' )
            
        
        if not self._read_only:
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'from clipboard', 'Import new urls to this list from the clipboard.', self._ImportFromClipboard )
            ClientGUIMenus.AppendMenuItem( submenu, 'from png', 'Import new urls to this list from a png file.', self._ImportFromPNG )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'import new urls' )
            
        
    
    def _ClearGallerySeeds( self, statuses_to_remove ):
        
        st_text = '/'.join( ( CC.status_string_lookup[ status ] for status in statuses_to_remove ) )
        
        message = 'Are you sure you want to delete all the {} {} log entries? This is useful for cleaning up and de-laggifying a very large list, but be careful you aren\'t removing something you would want to revisit.'.format( st_text, self._gallery_type_string )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            gallery_seed_log = self._gallery_seed_log_get_callable()
            
            gallery_seed_log.RemoveGallerySeedsByStatus( statuses_to_remove )
            
        
    
    def _GetExportableURLsString( self ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        gallery_seeds = gallery_seed_log.GetGallerySeeds()
        
        urls = [ gallery_seed.url for gallery_seed in gallery_seeds ]
        
        return os.linesep.join( urls )
        
    
    def _GetURLsFromURLsString( self, urls_string ):
        
        urls = HydrusText.DeserialiseNewlinedTexts( urls_string )
        
        return urls
        
    
    def _ImportFromClipboard( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        urls = self._GetURLsFromURLsString( raw_text )
        
        try:
            
            self._ImportURLs( urls )
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'Could not import!' )
            
            raise
            
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png with the urls', wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                try:
                    
                    payload_string = ClientSerialisable.LoadStringFromPNG( path )
                    
                    urls = self._GetURLsFromURLsString( payload_string )
                    
                    self._ImportURLs( urls )
                    
                except:
                    
                    QW.QMessageBox.critical( self, 'Error', 'Could not import!' )
                    
                    raise
                    
                
            
        
    
    def _ImportURLs( self, urls ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        urls = HydrusData.DedupeList( urls )
        
        filtered_urls = [ url for url in urls if not gallery_seed_log.HasGalleryURL( url ) ]
        
        urls_to_add = urls
        
        if len( filtered_urls ) < len( urls ):
            
            num_urls = len( urls )
            num_removed = num_urls - len( filtered_urls )
            
            message = 'Of the ' + HydrusData.ToHumanInt( num_urls ) + ' URLs you mean to add, ' + HydrusData.ToHumanInt( num_removed ) + ' are already in the search log. Would you like to only add new URLs or add everything (which will force a re-check of the duplicates)?'
            
            ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'only add new urls', no_label = 'add all urls, even duplicates', check_for_cancelled = True )
            
            if was_cancelled:
                
                return
                
            
            if result == QW.QDialog.Accepted:
                
                urls_to_add = filtered_urls
                
            elif result == QW.QDialog.Rejected:
                
                return
                
            
        
        can_generate_more_pages = False
        
        if self._can_generate_more_pages:
            
            message = 'Would you like these urls to only check for new files, or would you like them to also generate subsequent gallery pages, like a regular search would?'
            
            ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'just check what I am adding', no_label = 'start a potential new search for every url added', check_for_cancelled = True )
            
            if was_cancelled:
                
                return
                
            
            can_generate_more_pages = result == QW.QDialog.Rejected
            
        
        gallery_seeds = [ ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = can_generate_more_pages ) for url in urls_to_add ]
        
        gallery_seed_log.AddGallerySeeds( gallery_seeds )
        
    
    def _ExportToPNG( self ):
        
        payload = self._GetExportableURLsString()
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
            
            panel = ClientGUISerialisable.PNGExportPanel( dlg, payload )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ExportToClipboard( self ):
        
        payload = self._GetExportableURLsString()
        
        HG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _RetryErrors( self ):
        
        message = 'Are you sure you want to retry all the files that encountered errors?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            gallery_seed_log = self._gallery_seed_log_get_callable()
            
            gallery_seed_log.RetryFailed()
            
        
    
    def _ShowGallerySeedLogFrame( self ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        tlw = self.window()
        
        title = '{} log'.format( self._gallery_type_string )
        
        if isinstance( tlw, QP.Dialog ):
            
            if self._gallery_seed_log_set_callable is None: # throw up a dialog that edits the gallery_seed log in place
                
                with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._controller, self._read_only, self._can_generate_more_pages, gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.exec()
                    
                
            else: # throw up a dialog that edits the gallery_seed log but can be cancelled
                
                dupe_gallery_seed_log = gallery_seed_log.Duplicate()
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._controller, self._read_only, self._can_generate_more_pages, dupe_gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        self._gallery_seed_log_set_callable( dupe_gallery_seed_log )
                        
                    
                
            
        else: # throw up a frame that edits the gallery_seed log in place
            
            frame_key = 'gallery_import_log'
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditGallerySeedLogPanel( frame, self._controller, self._read_only, self._can_generate_more_pages, gallery_seed_log )
            
            frame.SetPanel( panel )
            
        
    
class GallerySeedLogStatusControl( QW.QFrame ):
    
    def __init__( self, parent, controller, read_only, can_generate_more_pages, gallery_type_string, page_key = None ):
        
        QW.QFrame.__init__( self, parent )
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        self._controller = controller
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._page_key = page_key
        self._gallery_type_string = gallery_type_string
        
        self._gallery_seed_log = None
        
        self._log_summary_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._gallery_seed_log_button = GallerySeedLogButton( self, self._controller, self._read_only, self._can_generate_more_pages, gallery_type_string, self._GetGallerySeedLog )
        
        #
        
        self._Update()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._log_summary_st, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._gallery_seed_log_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def _Update( self ):
        
        if self._gallery_seed_log is None:
            
            self._log_summary_st.clear()
            
            if self._gallery_seed_log_button.isEnabled():
                
                self._gallery_seed_log_button.setEnabled( False )
                
            
        else:
            
            ( import_summary, ( num_done, num_to_do ) ) = self._gallery_seed_log.GetStatus()
            
            self._log_summary_st.setText( import_summary )
            
            if not self._gallery_seed_log_button.isEnabled():
                
                self._gallery_seed_log_button.setEnabled( True )
                
            
        
    
    def SetGallerySeedLog( self, gallery_seed_log ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._gallery_seed_log = gallery_seed_log
        
    
    def TIMERUIUpdate( self ):
        
        if self._controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
