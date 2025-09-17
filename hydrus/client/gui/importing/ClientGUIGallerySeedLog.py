import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.networking import ClientNetworkingFunctions

def ClearGallerySeeds( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog, statuses_to_remove, gallery_type_string ):
    
    st_text = '/'.join( ( CC.status_string_lookup[ status ] for status in statuses_to_remove ) )
    
    message = 'Are you sure you want to delete all the {} {} log entries? This is useful for cleaning up and de-laggifying a very large list, but be careful you aren\'t removing something you would want to revisit.'.format( st_text, gallery_type_string )
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        gallery_seed_log.RemoveGallerySeedsByStatus( statuses_to_remove )
        
    
def GetExportableURLsString( gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
    
    gallery_seeds = gallery_seed_log.GetGallerySeeds()
    
    urls = [ gallery_seed.url for gallery_seed in gallery_seeds ]
    
    return '\n'.join( urls )
    
def GetURLsFromURLsString( urls_string ):
    
    urls = HydrusText.DeserialiseNewlinedTexts( urls_string )
    
    return urls
    

def ImportFromClipboard( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog, can_generate_more_pages: bool ):
    
    try:
        
        raw_text = CG.client_controller.GetClipboardText()
        
    except HydrusExceptions.DataMissing as e:
        
        ClientGUIDialogsMessage.ShowCritical( win, 'Problem importing from clipboard!', str(e) )
        
        return
        
    
    urls = GetURLsFromURLsString( raw_text )
    
    try:
        
        ImportURLs( win, gallery_seed_log, urls, can_generate_more_pages )
        
    except Exception as e:
        
        ClientGUIDialogsQuick.PresentClipboardParseError( win, raw_text, 'Lines of URLs', e )
        
    

def ImportFromPNG( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog, can_generate_more_pages: bool ):
    
    with QP.FileDialog( win, 'select the png with the urls', wildcard = 'PNG (*.png)' ) as dlg:
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            path = dlg.GetPath()
            
            try:
                
                payload_string = ClientSerialisable.LoadStringFromPNG( path )
                
                urls = GetURLsFromURLsString( payload_string )
                
                ImportURLs( win, gallery_seed_log, urls, can_generate_more_pages )
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( win, 'Could not import!', str( e ) )
                
                raise
                
            
        
    
def ImportURLs( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog, urls, can_generate_more_pages: bool ):
    
    urls = HydrusLists.DedupeList( urls )
    
    filtered_urls = [ url for url in urls if not gallery_seed_log.HasGalleryURL( url ) ]
    
    urls_to_add = urls
    
    if len( filtered_urls ) < len( urls ):
        
        num_urls = len( urls )
        num_removed = num_urls - len( filtered_urls )
        
        message = 'Of the ' + HydrusNumbers.ToHumanInt( num_urls ) + ' URLs you mean to add, ' + HydrusNumbers.ToHumanInt( num_removed ) + ' are already in the search log. Would you like to only add new URLs or add everything (which will force a re-check of the duplicates)?'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( win, message, yes_label = 'only add new urls', no_label = 'add all urls, even duplicates', check_for_cancelled = True )
        
        if was_cancelled:
            
            return
            
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            urls_to_add = filtered_urls
            
        elif result == QW.QDialog.DialogCode.Rejected:
            
            return
            
        
    
    if can_generate_more_pages:
        
        message = 'Would you like these urls to only check for new files, or would you like them to also generate subsequent gallery pages, like a regular search would?'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( win, message, yes_label = 'just check what I am adding', no_label = 'start a potential new search for every url added', check_for_cancelled = True )
        
        if was_cancelled:
            
            return
            
        
        can_generate_more_pages = result == QW.QDialog.DialogCode.Rejected
        
    
    gallery_seeds = [ ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = can_generate_more_pages ) for url in urls_to_add ]
    
    gallery_seed_log.AddGallerySeeds( gallery_seeds )
    

def ExportGallerySeedsToClipboard( gallery_seeds: collections.abc.Collection[ ClientImportGallerySeeds.GallerySeed ] ):
    
    gallery_seeds = HydrusSerialisable.SerialisableList( gallery_seeds )
    
    payload = gallery_seeds.DumpToString()
    
    CG.client_controller.pub( 'clipboard', 'text', payload )
    

def ExportToPNG( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
    
    payload = GetExportableURLsString( gallery_seed_log )
    
    with ClientGUITopLevelWindowsPanels.DialogNullipotent( win, 'export to png' ) as dlg:
        
        panel = ClientGUISerialisable.PNGExportPanel( dlg, payload )
        
        dlg.SetPanel( panel )
        
        dlg.exec()
        
    
def ExportToClipboard( gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
    
    payload = GetExportableURLsString( gallery_seed_log )
    
    CG.client_controller.pub( 'clipboard', 'text', payload )
    
def RetryErrors( win: QW.QWidget, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
    
    message = 'Are you sure you want to retry all the files that encountered errors?'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        gallery_seed_log.RetryFailed()
        
    
def PopulateGallerySeedLogButton( win: QW.QWidget, menu: QW.QMenu, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog, selected_gallery_seeds: list[ ClientImportGallerySeeds.GallerySeed ], read_only: bool, can_generate_more_pages: bool, gallery_type_string: str ):
    
    num_successful = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SUCCESSFUL_AND_NEW )
    num_vetoed = gallery_seed_log.GetGallerySeedCount( CC.STATUS_VETOED )
    num_errors = gallery_seed_log.GetGallerySeedCount( CC.STATUS_ERROR )
    num_skipped = gallery_seed_log.GetGallerySeedCount( CC.STATUS_SKIPPED )
    
    if num_successful > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'successful\' gallery log entries from the log'.format( HydrusNumbers.ToHumanInt( num_successful ) ), 'Tell this log to clear out successful records, reducing the size of the queue.', ClearGallerySeeds, win, gallery_seed_log, ( CC.STATUS_SUCCESSFUL_AND_NEW, ), gallery_type_string )
        
    
    if num_errors > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'failed\' gallery log entries from the log'.format( HydrusNumbers.ToHumanInt( num_errors ) ), 'Tell this log to clear out errored records, reducing the size of the queue.', ClearGallerySeeds, win, gallery_seed_log, ( CC.STATUS_ERROR, ), gallery_type_string )
        
    
    if num_vetoed > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'ignored\' gallery log entries from the log'.format( HydrusNumbers.ToHumanInt( num_vetoed ) ), 'Tell this log to clear out ignored records, reducing the size of the queue.', ClearGallerySeeds, win, gallery_seed_log, ( CC.STATUS_VETOED, ), gallery_type_string )
        
    
    if num_skipped > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'skipped\' gallery log entries from the log'.format( HydrusNumbers.ToHumanInt( num_skipped ) ), 'Tell this log to clear out skipped records, reducing the size of the queue.', ClearGallerySeeds, win, gallery_seed_log, ( CC.STATUS_SKIPPED, ), gallery_type_string )
        
    
    ClientGUIMenus.AppendSeparator( menu )
    
    if len( gallery_seed_log ) > 0:
        
        if not read_only and gallery_seed_log.CanRestartFailedSearch():
            
            ClientGUIMenus.AppendMenuItem( menu, 'restart and resume failed search', 'Requeue the last failed attempt and resume search from there.', gallery_seed_log.RestartFailedSearch )
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        submenu = ClientGUIMenus.GenerateMenu( menu )

        ClientGUIMenus.AppendMenuItem( submenu, 'to clipboard', 'Copy all the urls in this list to the clipboard.', ExportToClipboard, gallery_seed_log )
        ClientGUIMenus.AppendMenuItem( submenu, 'to png', 'Export all the urls in this list to a png file.', ExportToPNG, win, gallery_seed_log )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'export all urls' )
        
    
    if not read_only:
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'from clipboard', 'Import new urls to this list from the clipboard.', ImportFromClipboard, win, gallery_seed_log, can_generate_more_pages )
        ClientGUIMenus.AppendMenuItem( submenu, 'from png', 'Import new urls to this list from a png file.', ImportFromPNG, win, gallery_seed_log, can_generate_more_pages )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'ADVANCED: import new urls' )
        
    
    if len( selected_gallery_seeds ) > 0:
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        if len( selected_gallery_seeds ) > 0:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'export selected page objects to clipboard', 'Advanced JSON inspection.', ExportGallerySeedsToClipboard, selected_gallery_seeds )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'advanced' )
        
    

class EditGallerySeedLogPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, read_only: bool, can_generate_more_pages: bool, gallery_type_string: str, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
        
        super().__init__( parent )
        
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._gallery_type_string = gallery_type_string
        self._gallery_seed_log = gallery_seed_log
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on gallery_seed add/remove
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_GALLERY_SEED_LOG.ID, self._ConvertGallerySeedToDisplayTuple, self._ConvertGallerySeedToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self, 30, model, delete_key_callback = self._DeleteSelected )
        
        #
        
        self._list_ctrl.AddDatas( self._gallery_seed_log.GetGallerySeeds() )
        
        self._list_ctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._list_ctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        self._list_ctrl.SetCopyRowsCallable( self._GetCopyableRows )
        
        CG.client_controller.sub( self, 'NotifyGallerySeedsUpdated', 'gallery_seed_log_gallery_seeds_updated' )
        
        CG.client_controller.CallAfter( self, self._UpdateText )
        
    
    def _ConvertGallerySeedToDisplayTuple( self, gallery_seed ):
        
        try:
            
            gallery_seed_index = self._gallery_seed_log.GetGallerySeedIndex( gallery_seed )
            
            pretty_gallery_seed_index = HydrusNumbers.ToHumanInt( gallery_seed_index )
            
        except:
            
            pretty_gallery_seed_index = '--'
            
        
        url = gallery_seed.url
        status = gallery_seed.status
        added = gallery_seed.created
        modified = gallery_seed.modified
        note = gallery_seed.note
        
        pretty_url = ClientNetworkingFunctions.ConvertURLToHumanString( url )
        pretty_status = CC.status_string_lookup[ status ] if status != CC.STATUS_UNKNOWN else ''
        pretty_added = HydrusTime.TimestampToPrettyTimeDelta( added )
        pretty_modified = HydrusTime.TimestampToPrettyTimeDelta( modified )
        
        pretty_note = HydrusText.GetFirstLine( note )
        
        return ( pretty_gallery_seed_index, pretty_url, pretty_status, pretty_added, pretty_modified, pretty_note )
        
    
    def _ConvertGallerySeedToSortTuple( self, gallery_seed ):
        
        try:
            
            gallery_seed_index = self._gallery_seed_log.GetGallerySeedIndex( gallery_seed )
            
        except:
            
            gallery_seed_index = -1
            
        
        url = gallery_seed.url
        status = gallery_seed.status
        added = gallery_seed.created
        modified = gallery_seed.modified
        note = gallery_seed.note
        
        pretty_url = ClientNetworkingFunctions.ConvertURLToHumanString( url )
        
        return ( gallery_seed_index, pretty_url, status, added, modified, note )
        
    
    def _CopySelectedGalleryURLs( self ):
        
        texts = self._GetCopyableRows()
        
        if len( texts ) > 0:
            
            CG.client_controller.pub( 'clipboard', 'text', '\n'.join( texts ) )
            
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for gallery_seed in self._list_ctrl.GetData( only_selected = True ):
            
            note = gallery_seed.note
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = '\n' * 2
            
            text = separator.join( notes )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        gallery_seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete the {} selected entries? This is only useful if you have a really really huge list.'.format( HydrusNumbers.ToHumanInt( len( gallery_seeds_to_delete ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._gallery_seed_log.RemoveGallerySeeds( gallery_seeds_to_delete )
                
            
        
    
    def _GetCopyableRows( self ):
        
        texts = [ gallery_seed.url for gallery_seed in self._list_ctrl.GetData( only_selected = True ) ]
        
        return texts
        
    
    def _GetListCtrlMenu( self ):
        
        selected_gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( selected_gallery_seeds ) == 0:
            
            PopulateGallerySeedLogButton( self, menu, self._gallery_seed_log, selected_gallery_seeds, self._read_only, self._can_generate_more_pages, self._gallery_type_string )
            
            return menu
            
        
        if len( selected_gallery_seeds ) == 1:
            
            ( selected_gallery_seed, ) = selected_gallery_seeds
            
            ClientGUIMenus.AppendMenuItem( menu, f'copy url', 'Copy the selected url to clipboard.', self._CopySelectedGalleryURLs )
            
            note = selected_gallery_seed.note
            
            if len( note ) > 0: 
                
                ClientGUIMenus.AppendMenuItem( menu, f'copy note', 'Copy the selected note to clipboard.', self._CopySelectedNotes )
                
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, 'copy urls', 'Copy all the selected urls to clipboard.', self._CopySelectedGalleryURLs )
            ClientGUIMenus.AppendMenuItem( menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'open urls', 'Open all the selected urls in your web browser.', self._OpenSelectedGalleryURLs )
        
        if len( selected_gallery_seeds ) == 1:
            
            ( selected_gallery_seed, ) = selected_gallery_seeds
            
            ClientGUIMenus.AppendSeparator( menu )
            
            request_url = selected_gallery_seed.url
            
            referral_url = selected_gallery_seed.GetReferralURL()
            
            url_submenu = ClientGUIMenus.GenerateMenu( menu )
            
            url_to_fetch = CG.client_controller.network_engine.domain_manager.GetURLToFetch( request_url )
            
            if url_to_fetch != request_url:
                
                ClientGUIMenus.AppendMenuLabel( url_submenu, f'(API/Redirect) actual url that will be fetched: {url_to_fetch}', copy_text = url_to_fetch )
                
            
            if referral_url is not None:
                
                ClientGUIMenus.AppendMenuLabel( url_submenu, f'referral url: {referral_url}', copy_text = referral_url )
                
            
            referral_url_to_use = CG.client_controller.network_engine.domain_manager.GetReferralURL( url_to_fetch, referral_url )
            
            if referral_url_to_use != referral_url:
                
                ClientGUIMenus.AppendMenuLabel( url_submenu, f'(URL Class transformation) actual expected referral url: {referral_url_to_use}', copy_text = referral_url_to_use )
                
            
            if url_submenu.isEmpty():
                
                ClientGUIMenus.DestroyMenu( url_submenu )
                
                ClientGUIMenus.AppendMenuLabel( menu, 'no additional urls' )
                
            else:
                
                ClientGUIMenus.AppendMenu( menu, url_submenu, 'additional urls' )
                
            
            headers = selected_gallery_seed.GetHTTPHeaders()
            
            if len( headers ) == 0:
                
                ClientGUIMenus.AppendMenuLabel( menu, 'no additional headers' )
                
            else:
                
                header_submenu = ClientGUIMenus.GenerateMenu( menu )
                
                for ( key, value ) in headers.items():
                    
                    ClientGUIMenus.AppendMenuLabel( header_submenu, key + ': ' + value )
                    
                
                ClientGUIMenus.AppendMenu( menu, header_submenu, 'additional headers' )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if not self._read_only:
            
            ClientGUIMenus.AppendMenuItem( menu, 'try again (just this one page)', 'Schedule this url to occur again.', HydrusData.Call( self._TrySelectedAgain, False ) )
            
            if self._can_generate_more_pages:
                
                ClientGUIMenus.AppendMenuItem( menu, 'try again (and allow search to continue)', 'Schedule this url to occur again and continue.', HydrusData.Call( self._TrySelectedAgain, True ) )
                
            
        
        ClientGUIMenus.AppendMenuItem( menu, 'skip', 'Skip all the selected urls.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        PopulateGallerySeedLogButton( self, submenu, self._gallery_seed_log, selected_gallery_seeds, self._read_only, self._can_generate_more_pages, self._gallery_type_string )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'whole log' )
        
        return menu
        
    
    def _OpenSelectedGalleryURLs( self ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( gallery_seeds ) > 0:
            
            if len( gallery_seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            for gallery_seed in gallery_seeds:
                
                ClientPaths.LaunchURLInWebBrowser( gallery_seed.url )
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        for gallery_seed in gallery_seeds:
            
            gallery_seed.SetStatus( status_to_set )
            
        
        self._gallery_seed_log.NotifyGallerySeedsUpdated( gallery_seeds )
        
    
    def _TrySelectedAgain( self, can_generate_more_pages ):
        
        gallery_seeds = self._list_ctrl.GetData( only_selected = True )
        
        for gallery_seed in gallery_seeds:
            
            restarted_gallery_seed = gallery_seed.GenerateRestartedDuplicate( can_generate_more_pages )
            
            self._gallery_seed_log.AddGallerySeeds( ( restarted_gallery_seed, ), parent_gallery_seed = gallery_seed )
            
        
    
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
    
    def __init__( self, parent, read_only: bool, can_generate_more_pages: bool, gallery_type_string: str, gallery_seed_log_get_callable, gallery_seed_log_set_callable = None ):
        
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._gallery_type_string = gallery_type_string
        self._gallery_seed_log_get_callable = gallery_seed_log_get_callable
        self._gallery_seed_log_set_callable = gallery_seed_log_set_callable
        
        action = QW.QAction()
        
        action.setText( '{} log'.format( gallery_type_string ) )
        action.setToolTip( ClientGUIFunctions.WrapToolTip( 'open detailed {} log'.format( self._gallery_type_string ) ) )
        
        action.triggered.connect( self._ShowGallerySeedLogFrame )
        
        super().__init__( parent, action )
        
    
    def _PopulateMenu( self, menu ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        PopulateGallerySeedLogButton( self, menu, gallery_seed_log, [], self._read_only, self._can_generate_more_pages, self._gallery_type_string )
        
    
    def _ShowGallerySeedLogFrame( self ):
        
        gallery_seed_log = self._gallery_seed_log_get_callable()
        
        tlw = self.window()
        
        title = '{} log'.format( self._gallery_type_string )
        
        if isinstance( tlw, QP.Dialog ):
            
            if self._gallery_seed_log_set_callable is None: # throw up a dialog that edits the gallery_seed log in place
                
                with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._read_only, self._can_generate_more_pages, self._gallery_type_string, gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.exec()
                    
                
            else: # throw up a dialog that edits the gallery_seed log but can be cancelled
                
                dupe_gallery_seed_log = gallery_seed_log.Duplicate()
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = EditGallerySeedLogPanel( dlg, self._read_only, self._can_generate_more_pages, self._gallery_type_string, dupe_gallery_seed_log )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        self._gallery_seed_log_set_callable( dupe_gallery_seed_log )
                        
                    
                
            
        else: # throw up a frame that edits the gallery_seed log in place
            
            frame_key = 'gallery_import_log'
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditGallerySeedLogPanel( frame, self._read_only, self._can_generate_more_pages, self._gallery_type_string, gallery_seed_log )
            
            frame.SetPanel( panel )
            
        
    
class GallerySeedLogStatusControl( QW.QFrame ):
    
    def __init__( self, parent: QW.QWidget, read_only: bool, can_generate_more_pages: bool, gallery_type_string: str, page_key = None ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Raised )
        
        self._read_only = read_only
        self._can_generate_more_pages = can_generate_more_pages
        self._page_key = page_key
        self._gallery_type_string = gallery_type_string
        
        self._gallery_seed_log = None
        
        self._log_summary_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._gallery_seed_log_button = GallerySeedLogButton( self, self._read_only, self._can_generate_more_pages, gallery_type_string, self._GetGallerySeedLog )
        
        #
        
        self._Update()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._log_summary_st, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._gallery_seed_log_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
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
        
        if CG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
