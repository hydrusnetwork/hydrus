import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
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
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTagSorting
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.search import ClientSearchPredicate

def ClearFileSeeds( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache, statuses_to_remove ):
    
    message = 'Are you sure you want to delete all the ' + '/'.join( ( CC.status_string_lookup[ status ] for status in statuses_to_remove ) ) + ' file import items? This is useful for cleaning up and de-laggifying a very large list, but be careful you aren\'t removing something you would want to revisit or what watcher/subscription may be using for future check time calculations.'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        file_seed_cache.RemoveFileSeedsByStatus( statuses_to_remove )
        
    

def GetRetryIgnoredParam( window ):
    
    choice_tuples = [
        ( 'retry all', None, 'retry all' ),
        ( 'retry 403s', '^403', 'retry all 403s' ),
        ( 'retry 404s', '^404', 'retry all 404s' ),
        ( 'retry blacklisted', 'blacklisted!$', 'retry all blacklisted' )
    ]
    
    return ClientGUIDialogsQuick.SelectFromListButtons( window, 'select what to retry', choice_tuples )
    

# TODO: I pulled this stuff out of the button to share it with the panel. TBH anything without Qt may be better as be FSC methods

def GetExportableSourcesString( file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    file_seeds = file_seed_cache.GetFileSeeds()
    
    sources = [ file_seed.file_seed_data for file_seed in file_seeds ]
    
    return '\n'.join( sources )
    
def GetSourcesFromSourcesString( sources_string ):
    
    sources = HydrusText.DeserialiseNewlinedTexts( sources_string )
    
    sources = [ ClientNetworkingFunctions.EnsureURLIsEncoded( source ) for source in sources ]
    
    return sources
    

def ExportFileSeedsToClipboard( file_seeds: collections.abc.Collection[ ClientImportFileSeeds.FileSeed ] ):
    
    file_seeds = HydrusSerialisable.SerialisableList( file_seeds )
    
    payload = file_seeds.DumpToString()
    
    CG.client_controller.pub( 'clipboard', 'text', payload )
    

def ExportToClipboard( file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    payload = GetExportableSourcesString( file_seed_cache )
    
    CG.client_controller.pub( 'clipboard', 'text', payload )
    
def ExportToPNG( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    payload = GetExportableSourcesString( file_seed_cache )
    
    with ClientGUITopLevelWindowsPanels.DialogNullipotent( win, 'export to png' ) as dlg:
        
        panel = ClientGUISerialisable.PNGExportPanel( dlg, payload )
        
        dlg.SetPanel( panel )
        
        dlg.exec()
        
    
def ImportFromClipboard( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    try:
        
        raw_text = CG.client_controller.GetClipboardText()
        
    except HydrusExceptions.DataMissing as e:
        
        ClientGUIDialogsMessage.ShowCritical( win, 'Problem pasting!', str(e) )
        
        return
        
    
    sources = GetSourcesFromSourcesString( raw_text )
    
    try:
        
        ImportSources( file_seed_cache, sources )
        
    except Exception as e:
        
        ClientGUIDialogsQuick.PresentClipboardParseError( win, raw_text, 'Lines of URLs or file paths', e )
        
    

def ImportFromPNG( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    with QP.FileDialog( win, 'select the png with the sources', wildcard = 'PNG (*.png)' ) as dlg:
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            path = dlg.GetPath()
            
            try:
                
                payload_string = ClientSerialisable.LoadStringFromPNG( path )
                
                sources = GetSourcesFromSourcesString( payload_string )
                
                ImportSources( file_seed_cache, sources )
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( win, 'Could not import!', str( e ) )
                
                raise
                
            
        
    

def ImportSources( file_seed_cache, sources ):
    
    if sources[0].startswith( 'http' ):
        
        file_seed_type = ClientImportFileSeeds.FILE_SEED_TYPE_URL
        
    else:
        
        file_seed_type = ClientImportFileSeeds.FILE_SEED_TYPE_HDD
        
    
    file_seeds = [ ClientImportFileSeeds.FileSeed( file_seed_type, source ) for source in sources ]
    
    file_seed_cache.AddFileSeeds( file_seeds )
    

def RenormaliseFileSeedCache( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    message = 'Are you sure you want to renormalise all the URLs in here (and discard any subsequent duplicates)? This typically only makes sense if you have changed the URL Class rules after this list was created (e.g. to remove an ephemeral token parameter) and you now need to collapse the existing list to catch future duplicates better.'
    message += '\n' * 2
    message += 'If you do not know exactly what this does, click no.'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        file_seed_cache.RenormaliseURLs()
        
    

def RetryErrors( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    message = 'Are you sure you want to retry all the files that encountered errors?'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        file_seed_cache.RetryFailed()
        
    

def RetryIgnored( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    try:
        
        ignored_regex = GetRetryIgnoredParam( win )
        
    except HydrusExceptions.CancelledException:
        
        return
        
    
    file_seed_cache.RetryIgnored( ignored_regex = ignored_regex )
    

def ReverseFileSeedCache( win: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
    
    message = 'Reverse this file log? Any outstanding imports will process in the opposite order.'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        file_seed_cache.Reverse()
        
    

def ShowFilesInNewPage( file_seed_cache: ClientImportFileSeeds.FileSeedCache, show = 'all' ):
    
    if show == 'all':
        
        hashes = file_seed_cache.GetHashes()
        
    elif show == 'new':
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        
        hashes = file_seed_cache.GetPresentedHashes( presentation_import_options )
        
    
    if len( hashes ) > 0:
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes )
        
    

def PopulateFileSeedCacheMenu( win: QW.QWidget, menu: QW.QMenu, file_seed_cache: ClientImportFileSeeds.FileSeedCache, selected_file_seeds: list[ ClientImportFileSeeds.FileSeed ] ):
    
    num_already_in = file_seed_cache.GetFileSeedCount( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT )
    num_successful = file_seed_cache.GetFileSeedCount( CC.STATUS_SUCCESSFUL_AND_NEW ) + num_already_in
    num_vetoed = file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED )
    num_deleted = file_seed_cache.GetFileSeedCount( CC.STATUS_DELETED )
    num_errors = file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR )
    num_skipped = file_seed_cache.GetFileSeedCount( CC.STATUS_SKIPPED )
    num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
    
    if num_errors > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'retry ' + HydrusNumbers.ToHumanInt( num_errors ) + ' failures', 'Tell this log to reattempt all its error failures.', RetryErrors, win, file_seed_cache )
        
    
    if num_vetoed > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'retry ' + HydrusNumbers.ToHumanInt( num_vetoed ) + ' ignored', 'Tell this log to reattempt all its ignored/vetoed results.', RetryIgnored, win, file_seed_cache )
        
    
    ClientGUIMenus.AppendSeparator( menu )
    
    if num_successful > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'successful\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_successful ) ), 'Tell this log to clear out successful files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, CC.STATUS_SUCCESSFUL_AND_CHILD_FILES ) )
        
    
    if num_already_in > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'already in db\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_already_in ) ), 'Tell this log to clear out successful but non-new files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, ) )
        
    
    if num_deleted > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'previously deleted\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_deleted ) ), 'Tell this log to clear out deleted files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_DELETED, ) )
        
    
    if num_errors > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'failed\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_errors ) ), 'Tell this log to clear out errored files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_ERROR, ) )
        
    
    if num_vetoed > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'ignored\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_vetoed ) ), 'Tell this log to clear out ignored files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_VETOED, ) )
        
    
    if num_skipped > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'skipped\' file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_skipped ) ), 'Tell this log to clear out skipped files, reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_SKIPPED, ) )
        
    
    if num_unknown > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete {} \'unknown\' (i.e. unstarted) file import items from the queue'.format( HydrusNumbers.ToHumanInt( num_unknown ) ), 'Tell this log to clear out any items that have not yet been started (or have been restarted and not yet worked on), reducing the size of the queue.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_UNKNOWN, ) )
        
    
    if len( file_seed_cache ) > 0:
        
        ClientGUIMenus.AppendSeparator( menu )
        
        num_non_unknown = len( file_seed_cache ) - num_unknown
        
        if num_unknown > 0 and num_non_unknown > 0:
            
            ClientGUIMenus.AppendMenuItem( menu, f'delete everything except \'unknown\' (i.e. unstarted) ({HydrusNumbers.ToHumanInt( num_non_unknown )} items) from the queue', 'Tell this log to clear out everything, resetting the queue to empty.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_ERROR, CC.STATUS_VETOED, CC.STATUS_SKIPPED, CC.STATUS_SUCCESSFUL_AND_CHILD_FILES ) )
            
        
        ClientGUIMenus.AppendMenuItem( menu, f'delete everything ({HydrusNumbers.ToHumanInt( len( file_seed_cache ) )} items) from the queue', 'Tell this log to clear out everything, resetting the queue to empty.', ClearFileSeeds, win, file_seed_cache, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_ERROR, CC.STATUS_VETOED, CC.STATUS_SKIPPED, CC.STATUS_SUCCESSFUL_AND_CHILD_FILES ) )
        
    
    if num_unknown > 0:
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'set {} \'unknown\' (i.e. unstarted) file import items to \'skipped\''.format( HydrusNumbers.ToHumanInt( num_unknown ) ), 'Tell this log to skip any outstanding items in the queue.', file_seed_cache.SetStatusToStatus, CC.STATUS_UNKNOWN, CC.STATUS_SKIPPED )
        
    
    ClientGUIMenus.AppendSeparator( menu )
    
    if num_successful > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'show new files in a new page', 'Gather the new files in this import list and show them in a new page.', ShowFilesInNewPage, file_seed_cache, show = 'new' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all files in a new page', 'Gather the files in this import list and show them in a new page.', ShowFilesInNewPage, file_seed_cache )
        
    
    ClientGUIMenus.AppendSeparator( menu )
    
    if len( file_seed_cache ) > 0:
        
        ClientGUIMenus.AppendMenuItem( menu, 'reverse import order', 'Reverse the import list so outstanding imports process in the opposite order.', ReverseFileSeedCache, win, file_seed_cache )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'to clipboard', 'Copy all the sources in this list to the clipboard.', ExportToClipboard, file_seed_cache )
        ClientGUIMenus.AppendMenuItem( submenu, 'to png', 'Export all the sources in this list to a png file.', ExportToPNG, win, file_seed_cache )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'export all sources' )
        
    
    submenu = ClientGUIMenus.GenerateMenu( menu )
    
    ClientGUIMenus.AppendMenuItem( submenu, 'from clipboard', 'Import new urls or paths to this list from the clipboard.', ImportFromClipboard, win, file_seed_cache )
    ClientGUIMenus.AppendMenuItem( submenu, 'from png', 'Import new urls or paths to this list from a png file.', ImportFromPNG, win, file_seed_cache )
    
    ClientGUIMenus.AppendMenu( menu, submenu, 'ADVANCED: import new sources' )
    
    if len( selected_file_seeds ) > 0 or file_seed_cache.IsURLFileSeeds():
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        if len( selected_file_seeds ) > 0:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'export selected import objects to clipboard', 'Advanced JSON inspection.', ExportFileSeedsToClipboard, selected_file_seeds )
            
        
        if file_seed_cache.IsURLFileSeeds():
            
            ClientGUIMenus.AppendMenuItem( submenu, 're-normalise all URLs', 'Normalise all the import objects\' URLs and discard duplicates.', RenormaliseFileSeedCache, win, file_seed_cache )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'advanced' )
        
    

class EditFileSeedCachePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
        
        super().__init__( parent )
        
        self._file_seed_cache = file_seed_cache
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on file_seed add/remove
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FILE_SEED_CACHE.ID, self._ConvertFileSeedToDisplayTuple, self._ConvertFileSeedToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self, 30, model, activation_callback = self._ShowSelectionInNewPage, delete_key_callback = self._DeleteSelected )
        
        #
        
        self._list_ctrl.AddDatas( self._file_seed_cache.GetFileSeeds() )
        
        self._list_ctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._list_ctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        self._list_ctrl.SetCopyRowsCallable( self._GetCopyableRows )
        
        CG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
        CG.client_controller.CallAfter( self, self._UpdateText )
        
    
    def _ConvertFileSeedToDisplayTuple( self, file_seed: ClientImportFileSeeds.FileSeed ):
        
        try:
            
            file_seed_index = self._file_seed_cache.GetFileSeedIndex( file_seed )
            
            pretty_file_seed_index = HydrusNumbers.ToHumanInt( file_seed_index )
            
        except:
            
            pretty_file_seed_index = '--'
            
        
        file_seed_data = file_seed.file_seed_data_for_comparison
        status = file_seed.status
        added = file_seed.created
        modified = file_seed.modified
        source_time = file_seed.source_time
        note = file_seed.note
        
        if file_seed.file_seed_type == ClientImportFileSeeds.FILE_SEED_TYPE_URL:
            
            pretty_file_seed_data = ClientNetworkingFunctions.ConvertURLToHumanString( file_seed_data )
            
        else:
            
            pretty_file_seed_data = file_seed_data
            
        
        pretty_status = CC.status_string_lookup[ status ] if status != CC.STATUS_UNKNOWN else ''
        pretty_added = HydrusTime.TimestampToPrettyTimeDelta( added )
        pretty_modified = HydrusTime.TimestampToPrettyTimeDelta( modified )
        
        if source_time is None:
            
            pretty_source_time = 'unknown'
            
        else:
            
            pretty_source_time = HydrusTime.TimestampToPrettyTimeDelta( source_time )
            
        
        pretty_note = HydrusText.GetFirstLine( note )
        
        return ( pretty_file_seed_index, pretty_file_seed_data, pretty_status, pretty_added, pretty_modified, pretty_source_time, pretty_note )
        
    
    def _ConvertFileSeedToSortTuple( self, file_seed: ClientImportFileSeeds.FileSeed ):
        
        try:
            
            file_seed_index = self._file_seed_cache.GetFileSeedIndex( file_seed )
            
        except:
            
            file_seed_index = -1
            
        
        file_seed_data = file_seed.file_seed_data_for_comparison
        status = file_seed.status
        added = file_seed.created
        modified = file_seed.modified
        source_time = file_seed.source_time
        note = file_seed.note
        
        if file_seed.file_seed_type == ClientImportFileSeeds.FILE_SEED_TYPE_URL:
            
            pretty_file_seed_data = ClientNetworkingFunctions.ConvertURLToHumanString( file_seed_data )
            
        else:
            
            pretty_file_seed_data = file_seed_data
            
        
        sort_source_time = ClientGUIListCtrl.SafeNoneInt( source_time )
        
        return ( file_seed_index, pretty_file_seed_data, status, added, modified, sort_source_time, note )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for file_seed in self._list_ctrl.GetData( only_selected = True ):
            
            note = file_seed.note
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = '\n' * 2
            
            text = separator.join( notes )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedFileSeedData( self ):
        
        texts = self._GetCopyableRows()
        
        if len( texts ) > 0:
            
            CG.client_controller.pub( 'clipboard', 'text', '\n'.join( texts ) )
            
        
    
    def _DeleteSelected( self ):
        
        file_seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( file_seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete the {} selected entries?'.format( HydrusNumbers.ToHumanInt( len( file_seeds_to_delete ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._file_seed_cache.RemoveFileSeeds( file_seeds_to_delete )
                
            
        
    
    def _GetCopyableRows( self ):
        
        texts = [ file_seed.file_seed_data for file_seed in self._list_ctrl.GetData( only_selected = True ) ]
        
        return texts
        
    
    def _GetListCtrlMenu( self ):
        
        selected_file_seeds = self._list_ctrl.GetData( only_selected = True )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( selected_file_seeds ) == 0:
            
            PopulateFileSeedCacheMenu( self, menu, self._file_seed_cache, selected_file_seeds )
            
            return menu
            
        
        we_are_looking_at_urls = self._file_seed_cache.IsURLFileSeeds()
        
        ClientGUIMenus.AppendSeparator( menu )
        
        can_show_files_in_new_page = True in ( file_seed.HasHash() for file_seed in selected_file_seeds )
        
        if can_show_files_in_new_page:
            
            ClientGUIMenus.AppendMenuItem( menu, 'open selected files in a new page', 'Show all the known selected files in a new thumbnail page. This is complicated, so cannot always be guaranteed, even if the import says \'success\'.', self._ShowSelectionInNewPage )
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        label = 'copy urls' if we_are_looking_at_urls else 'copy paths'
        
        ClientGUIMenus.AppendMenuItem( menu, label, 'Copy all the selected sources to clipboard.', self._CopySelectedFileSeedData )
        ClientGUIMenus.AppendMenuItem( menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if we_are_looking_at_urls:
            
            open_sources_text = 'open URLs'
            
        else:
            
            open_sources_text = 'open files\' locations'
            
        
        ClientGUIMenus.AppendMenuItem( menu, open_sources_text, 'Open all the selected sources in your file explorer or web browser.', self._OpenSelectedFileSeedData )
        
        if we_are_looking_at_urls:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
            
            file_seed_datas = [ file_seed.file_seed_data for file_seed in selected_file_seeds ]
            urls = [ file_seed_data for file_seed_data in file_seed_datas if isinstance( file_seed_data, str ) and file_seed_data.startswith( 'http' ) ]
            
            url_preds = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'exact_match', url, f'has url {url}' ) ) for url in urls ]
            
            predicates = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = url_preds ) ]
            
            page_name = 'url search'
            activate_window = False
            
            c = HydrusData.Call( CG.client_controller.pub, 'new_page_query', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
            
            ClientGUIMenus.AppendMenuItem( menu, 'search for URLs', 'Open a new page with the files that share any of these selected URLs.', c )
            
        
        if len( selected_file_seeds ) == 1:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ( selected_file_seed, ) = selected_file_seeds
            
            hash_types_to_hashes = selected_file_seed.GetHashTypesToHashes()
            
            if len( hash_types_to_hashes ) == 0:
                
                ClientGUIMenus.AppendMenuLabel( menu, 'no hashes yet' )
                
            else:
                
                hash_submenu = ClientGUIMenus.GenerateMenu( menu )
                
                for hash_type in ( 'sha256', 'md5', 'sha1', 'sha512' ):
                    
                    if hash_type in hash_types_to_hashes:
                        
                        h = hash_types_to_hashes[ hash_type ]
                        
                        ClientGUIMenus.AppendMenuLabel( hash_submenu, '{}:{}'.format( hash_type, h.hex() ) )
                        
                    
                
                ClientGUIMenus.AppendMenu( menu, hash_submenu, 'hashes' )
                
            
            #
            
            if selected_file_seed.IsURLFileImport():
                
                request_url = selected_file_seed.file_seed_data
                normalised_url = selected_file_seed.file_seed_data_for_comparison
                pretty_url = ClientNetworkingFunctions.ConvertURLToHumanString( normalised_url )
                referral_url = selected_file_seed.GetReferralURL()
                primary_urls = sorted( selected_file_seed.GetPrimaryURLs() )
                source_urls = sorted( selected_file_seed.GetSourceURLs() )
                
                url_submenu = ClientGUIMenus.GenerateMenu( menu )
                
                if normalised_url != pretty_url:
                    
                    ClientGUIMenus.AppendMenuLabel( url_submenu, f'normalised url: {normalised_url}', copy_text = normalised_url )
                    
                
                if request_url != normalised_url:
                    
                    ClientGUIMenus.AppendMenuLabel( url_submenu, f'request url: {request_url}', copy_text = request_url )
                    
                
                url_to_fetch = CG.client_controller.network_engine.domain_manager.GetURLToFetch( request_url )
                
                if url_to_fetch != request_url:
                    
                    ClientGUIMenus.AppendMenuLabel( url_submenu, f'(API/Redirect) actual url that will be fetched: {url_to_fetch}', copy_text = url_to_fetch )
                    
                
                if referral_url is not None:
                    
                    ClientGUIMenus.AppendMenuLabel( url_submenu, f'referral url: {referral_url}', copy_text = referral_url )
                    
                
                referral_url_to_use = CG.client_controller.network_engine.domain_manager.GetReferralURL( url_to_fetch, referral_url )
                
                if referral_url_to_use != referral_url:
                    
                    ClientGUIMenus.AppendMenuLabel( url_submenu, f'(URL Class transformation) actual expected referral url: {referral_url_to_use}', copy_text = referral_url_to_use )
                    
                
                if len( primary_urls ) > 0:
                    
                    ClientGUIMenus.AppendSeparator( url_submenu )
                    
                    for url in primary_urls:
                        
                        ClientGUIMenus.AppendMenuLabel( url_submenu, f'primary url: {url}', copy_text = url )
                        
                    
                
                if len( source_urls ) > 0:
                    
                    ClientGUIMenus.AppendSeparator( url_submenu )
                    
                    for url in source_urls:
                        
                        ClientGUIMenus.AppendMenuLabel( url_submenu, f'source url: {url}', copy_text = url )
                        
                    
                
                if url_submenu.isEmpty():
                    
                    ClientGUIMenus.DestroyMenu( url_submenu )
                    
                    ClientGUIMenus.AppendMenuLabel( menu, 'no additional urls' )
                    
                else:
                    
                    ClientGUIMenus.AppendMenu( menu, url_submenu, 'additional urls' )
                    
                
                #
                
                headers = selected_file_seed.GetHTTPHeaders()
                
                if len( headers ) == 0:
                    
                    ClientGUIMenus.AppendMenuLabel( menu, 'no additional headers' )
                    
                else:
                    
                    header_submenu = ClientGUIMenus.GenerateMenu( menu )
                    
                    for ( key, value ) in headers.items():
                        
                        ClientGUIMenus.AppendMenuLabel( header_submenu, key + ': ' + value )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, header_submenu, 'additional headers' )
                    
                
                #
                
                tags = list( selected_file_seed.GetExternalTags() )
                
                tag_sort = ClientTagSorting.TagSort( sort_type = ClientTagSorting.SORT_BY_HUMAN_TAG, sort_order = CC.SORT_ASC )
                
                ClientTagSorting.SortTags( tag_sort, tags )
                
                if len( tags ) == 0:
                    
                    ClientGUIMenus.AppendMenuLabel( menu, 'no parsed tags' )
                    
                else:
                    
                    tag_submenu = ClientGUIMenus.GenerateMenu( menu )
                    
                    for tag in tags:
                        
                        ClientGUIMenus.AppendMenuLabel( tag_submenu, tag )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, tag_submenu, 'parsed tags' )
                    
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'try again', 'Reset the progress of all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_UNKNOWN ) )
        
        ClientGUIMenus.AppendMenuItem( menu, 'skip', 'Skip all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
        
        ClientGUIMenus.AppendMenuItem( menu, 'delete from list', 'Remove all the selected imports.', HydrusData.Call( self._DeleteSelected ) )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        PopulateFileSeedCacheMenu( self, submenu, self._file_seed_cache, selected_file_seeds )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'whole log' )
        
        return menu
        
    
    def _OpenSelectedFileSeedData( self ):
        
        file_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( file_seeds ) > 0:
            
            if len( file_seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            if file_seeds[0].file_seed_data.startswith( 'http' ):
                
                for file_seed in file_seeds:
                    
                    ClientPaths.LaunchURLInWebBrowser( file_seed.file_seed_data )
                    
                
            else:
                
                try:
                    
                    ClientPaths.OpenFileLocations( [ file_seed.file_seed_data for file_seed in file_seeds ] )
                    
                    
                except Exception as e:
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Problem opening files!', str(e) )
                    
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        file_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if status_to_set == CC.STATUS_UNKNOWN:
            
            deleted_and_clearable_file_seeds = [ file_seed for file_seed in file_seeds if file_seed.IsDeleted() and file_seed.HasHash() ]
            
            if len( deleted_and_clearable_file_seeds ) > 0:
                
                message = 'One or more of these files did not import due to being previously deleted. They will likely fail again unless you erase those deletion records. Would you like to do this now?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    deletee_hashes = { file_seed.GetHash() for file_seed in deleted_and_clearable_file_seeds }
                    
                    ClientGUIMediaSimpleActions.UndeleteFiles( deletee_hashes )
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, deletee_hashes )
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                    
                    CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                
            
        
        for file_seed in file_seeds:
            
            file_seed.SetStatus( status_to_set )
            
        
        self._file_seed_cache.NotifyFileSeedsUpdated( file_seeds )
        
    
    def _ShowSelectionInNewPage( self ):
        
        hashes = []
        
        for file_seed in self._list_ctrl.GetData( only_selected = True ):
            
            if file_seed.HasHash():
                
                hashes.append( file_seed.GetHash() )
                
            
        
        if len( hashes ) > 0:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
            
            ClientGUIMediaSimpleActions.ShowFilesInNewPage( hashes, location_context )
            
        
    
    def _UpdateListCtrl( self, file_seeds ):
        
        file_seeds_to_add = []
        file_seeds_to_update = []
        file_seeds_to_delete = []
        
        for file_seed in file_seeds:
            
            if self._file_seed_cache.HasFileSeed( file_seed ):
                
                if self._list_ctrl.HasData( file_seed ):
                    
                    file_seeds_to_update.append( file_seed )
                    
                else:
                    
                    file_seeds_to_add.append( file_seed )
                    
                
            else:
                
                if self._list_ctrl.HasData( file_seed ):
                    
                    file_seeds_to_delete.append( file_seed )
                    
                
            
        
        if len( file_seeds_to_delete ) > 0:
            
            self._list_ctrl.DeleteDatas( file_seeds_to_delete )
            
        
        if len( file_seeds_to_add ) > 0:
            
            self._list_ctrl.AddDatas( file_seeds_to_add )
            
            # if file_seeds are inserted, then all subsequent indices need to be shuffled up, hence just update all here
            
            self._list_ctrl.UpdateDatas()
            
        else:
            
            self._list_ctrl.UpdateDatas( file_seeds_to_update )
            
        
    
    def _UpdateText( self ):
        
        file_seed_cache_status = self._file_seed_cache.GetStatus()
        
        self._text.setText( file_seed_cache_status.GetStatusText() )
        
    
    def GetValue( self ):
        
        return self._file_seed_cache
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            self._UpdateText()
            self._UpdateListCtrl( file_seeds )
            
        
    

class FileSeedCacheButton( ClientGUICommon.ButtonWithMenuArrow ):
    
    def __init__( self, parent, file_seed_cache_get_callable, file_seed_cache_set_callable = None ):
        
        self._file_seed_cache_get_callable = file_seed_cache_get_callable
        self._file_seed_cache_set_callable = file_seed_cache_set_callable
        
        action = QW.QAction()
        
        action.setText( 'file log' )
        action.setToolTip( ClientGUIFunctions.WrapToolTip( 'open detailed file log' ) )
        
        action.triggered.connect( self._ShowFileSeedCacheFrame )
        
        super().__init__( parent, action )
        
    
    def _PopulateMenu( self, menu ):
        
        file_seed_cache = self._file_seed_cache_get_callable()
        
        PopulateFileSeedCacheMenu( self, menu, file_seed_cache, [] )
        
    
    def _ShowFileSeedCacheFrame( self ):
        
        file_seed_cache = self._file_seed_cache_get_callable()
        
        tlw = self.window()
        
        title = 'file log'
        
        if isinstance( tlw, QP.Dialog ):
            
            if self._file_seed_cache_set_callable is None: # throw up a dialog that edits the file_seed cache in place
                
                with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title ) as dlg:
                    
                    panel = EditFileSeedCachePanel( dlg, file_seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.exec()
                    
                
            else: # throw up a dialog that edits the file_seed cache but can be cancelled
                
                dupe_file_seed_cache = file_seed_cache.Duplicate()
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = EditFileSeedCachePanel( dlg, dupe_file_seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        self._file_seed_cache_set_callable( dupe_file_seed_cache )
                        
                    
                
            
        else: # throw up a frame that edits the file_seed cache in place
            
            frame_key = 'file_import_status'
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditFileSeedCachePanel( frame, file_seed_cache )
            
            frame.SetPanel( panel )
            
        
    

class FileSeedCacheStatusControl( QW.QFrame ):
    
    def __init__( self, parent, page_key = None ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Raised )
        
        self._page_key = page_key
        
        self._file_seed_cache = None
        
        self._import_summary_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._progress_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._file_seed_cache_button = FileSeedCacheButton( self, self._GetFileSeedCache )
        
        self._progress_gauge = ClientGUICommon.Gauge( self )
        
        #
        
        self._Update()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._progress_st, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._file_seed_cache_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._import_summary_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._progress_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        #
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def _Update( self ):
        
        if self._file_seed_cache is None:
            
            self._import_summary_st.clear()
            self._progress_st.clear()
            self._progress_gauge.SetRange( 1 )
            self._progress_gauge.SetValue( 0 )
            
            if self._file_seed_cache_button.isEnabled():
                
                self._file_seed_cache_button.setEnabled( False )
                
            
        else:
            
            file_seed_cache_status = self._file_seed_cache.GetStatus()
            
            ( num_done, num_to_do ) = file_seed_cache_status.GetValueRange()
            
            self._import_summary_st.setText( file_seed_cache_status.GetStatusText() )
            
            if num_to_do == 0:
                
                self._progress_st.clear()
                
            else:
                
                self._progress_st.setText( HydrusNumbers.ValueRangeToPrettyString(num_done,num_to_do) )
                
            
            self._progress_gauge.SetRange( num_to_do )
            self._progress_gauge.SetValue( num_done )
            
            if not self._file_seed_cache_button.isEnabled():
                
                self._file_seed_cache_button.setEnabled( True )
                
            
        
    
    def SetFileSeedCache( self, file_seed_cache ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._file_seed_cache = file_seed_cache
        
    
    def TIMERUIUpdate( self ):
        
        do_it_anyway = False
        
        if self._file_seed_cache is not None:
            
            file_seed_cache_status = self._file_seed_cache.GetStatus()
            
            ( num_done, num_to_do ) = file_seed_cache_status.GetValueRange()
            
            ( old_num_done, old_num_to_do ) = self._progress_gauge.GetValueRange()
            
            if old_num_done != num_done or old_num_to_do != num_to_do:
                
                if self._page_key is not None:
                    
                    do_it_anyway = True # to update the gauge
                    
                    CG.client_controller.pub( 'refresh_page_name', self._page_key )
                    
                
            
        
        if CG.client_controller.gui.IShouldRegularlyUpdate( self ) or do_it_anyway:
            
            self._Update()
            
        
    
