import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIFileSeedCache
from hydrus.client.gui.importing import ClientGUIGallerySeedLog
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelLoading
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.parsing import ClientGUIParsingFormulae
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUITextInput
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportGallery
from hydrus.client.importing import ClientImportWatchers
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing import ClientImportSimpleURLs
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.parsing import ClientParsing

def AddPresentationSubmenu( menu: QW.QMenu, importer_name: str, single_selected_presentation_import_options: PresentationImportOptions.PresentationImportOptions | None, callable ):
    
    submenu = ClientGUIMenus.GenerateMenu( menu )
    
    # inbox only
    # detect single_selected_presentation_import_options and deal with it
    
    description = 'Gather these files for the selected importers and show them.'
    
    if single_selected_presentation_import_options is None:
        
        ClientGUIMenus.AppendMenuItem( submenu, 'default presented files', description, callable )
        
    else:
        
        ClientGUIMenus.AppendMenuItem( submenu, 'default presented files ({})'.format( single_selected_presentation_import_options.GetSummary() ), description, callable )
        
    
    sets_of_options = []
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX )
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
    
    sets_of_options.append( presentation_import_options )
    
    for presentation_import_options in sets_of_options:
        
        if single_selected_presentation_import_options is not None and presentation_import_options == single_selected_presentation_import_options:
            
            continue
            
        
        ClientGUIMenus.AppendMenuItem( submenu, presentation_import_options.GetSummary(), description, callable, presentation_import_options = presentation_import_options )
        
    
    ClientGUIMenus.AppendMenu( menu, submenu, 'show files' )
    

class SidebarImporter( ClientGUISidebarCore.Sidebar ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
    
    def _UpdateImportStatus( self ):
        
        raise NotImplementedError()
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        self._UpdateImportStatus()
        
    
    def RefreshQuery( self ):
        
        self._media_sort_widget.BroadcastSort()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateImportStatus()
        
    

class SidebarImporterHDD( SidebarImporter ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'imports', start_expanded = True, can_expand = True )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._page_key )
        
        self._pause_button = ClientGUICommon.IconButton( self._import_queue_panel, CC.global_icons().file_pause, self.Pause )
        self._pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play imports' ) )
        
        self._hdd_import: ClientImportLocal.HDDImport = self._page_manager.GetVariable( 'hdd_import' )
        
        file_import_options = self._hdd_import.GetFileImportOptions()
        
        show_downloader_options = False
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._current_action, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._hdd_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._hdd_import.SetFileImportOptions )
        
    
    def _UpdateImportStatus( self ):
        
        ( current_action, paused ) = self._hdd_import.GetStatus()
        
        if paused:
            
            self._pause_button.SetIconSmart( CC.global_icons().file_play )
            
        else:
            
            self._pause_button.SetIconSmart( CC.global_icons().file_pause )
            
        
        self._current_action.setText( current_action )
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        if self._hdd_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
        num_items = len( self._hdd_import.GetFileSeedCache() )
        
        if not for_session_close and CG.client_controller.new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) and num_items > 0:
            
            raise HydrusExceptions.VetoException( f'This is a local import page holding {HydrusNumbers.ToHumanInt( num_items )} import objects.' )
            
        
    
    def Pause( self ):
        
        self._hdd_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def Start( self ):
        
        self._hdd_import.Start( self._page_key )
        
    

class SidebarImporterMultipleGallery( SidebarImporter ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        self._last_time_imports_changed = 0
        self._next_update_time = 0.0
        
        self._multiple_gallery_import = typing.cast( ClientImportGallery.MultipleGalleryImport, self._page_manager.GetVariable( 'multiple_gallery_import' ) )
        
        self._highlighted_gallery_import = self._multiple_gallery_import.GetHighlightedGalleryImport()
        
        self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._loading_highlight_job_status.Finish()
        
        #
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader', start_expanded = True, can_expand = True )
        
        #
        
        self._gallery_importers_status_st_top = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        self._gallery_importers_status_st_bottom = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        
        self._gallery_importers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._gallery_downloader_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_GALLERY_IMPORTERS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._gallery_importers_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._gallery_importers_listctrl_panel, 4, model, delete_key_callback = self._RemoveGalleryImports, activation_callback = self._HighlightSelectedGalleryImport )
        
        self._gallery_importers_listctrl_panel.SetListCtrl( self._gallery_importers_listctrl )
        
        self._gallery_importers_listctrl_panel.AddIconButton( CC.global_icons().highlight, self._HighlightSelectedGalleryImport, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._gallery_importers_listctrl_panel.AddIconButton( CC.global_icons().clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._gallery_importers_listctrl_panel.AddIconButton( CC.global_icons().file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddIconButton( CC.global_icons().gallery_pause, self._PausePlayGallery, tooltip = 'pause/play search', enabled_only_on_selection = True )
        
        menu_template_items = []
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry ignored', 'Retry the files that were moved over for one reason or another.', self._RetryIgnored )
        menu_template_item.SetVisibleCallable( self._CanRetryIgnored )
        
        menu_template_items.append( menu_template_item )
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry failed', 'Retry the files that failed.', self._RetryFailed )
        menu_template_item.SetVisibleCallable( self._CanRetryFailed )
        
        menu_template_items.append( menu_template_item )
        
        self._gallery_importers_listctrl_panel.AddMenuIconButton( CC.global_icons().retry, 'retry commands', menu_template_items, enabled_check_func = self._CanRetryAnything )
        
        self._gallery_importers_listctrl_panel.AddIconButton( CC.global_icons().trash, self._RemoveGalleryImports, tooltip = 'remove selected', enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl.Sort()
        
        #
        
        self._query_input = ClientGUITextInput.TextAndPasteCtrl( self._gallery_downloader_panel, self._PendQueries )
        
        self._cog_button = ClientGUIMenuButton.CogIconButton( self._gallery_downloader_panel, self._GetCogIconMenuTemplateItems() )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._gallery_downloader_panel, self._multiple_gallery_import.GetGUGKeyAndName(), update_callable = self._SetGUGKeyAndName )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 2000, message = 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.valueChanged.connect( self.EventFileLimit )
        self._file_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'per query, stop searching the gallery once this many files has been reached' ) )
        
        file_import_options = self._multiple_gallery_import.GetFileImportOptions()
        tag_import_options = self._multiple_gallery_import.GetTagImportOptions()
        note_import_options = self._multiple_gallery_import.GetNoteImportOptions()
        file_limit = self._multiple_gallery_import.GetFileLimit()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        self._set_options_to_queries_button = ClientGUICommon.BetterButton( self, 'update selected with current options', self._SetOptionsToGalleryImports )
        self._set_options_to_queries_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Each query has its own file limit and import options (you can review them in the highlight panel below). These are not updated if the main page\'s options are updated. It seems some downloaders in your selection differ with what the page currently has. Clicking here will update the selected queries with whatever the page currently has.' ) )
        self._set_options_to_queries_button.setVisible( False )
        
        #
        
        input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( input_hbox, self._query_input, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( input_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._gallery_downloader_panel.Add( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._set_options_to_queries_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._highlighted_gallery_import_panel = ClientGUIImport.GalleryImportPanel( self, self._page_key, name = 'highlighted query' )
        
        self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._gallery_downloader_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_gallery_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        self._query_input.setPlaceholderText( initial_search_text )
        
        self._file_limit.SetValue( file_limit )
        
        self._UpdateImportStatus()
        
        self._gallery_importers_listctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        
        self._import_options_button.fileImportOptionsChanged.connect( self._multiple_gallery_import.SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._multiple_gallery_import.SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._multiple_gallery_import.SetTagImportOptions )
        
        self._file_limit.valueChanged.connect( self._UpdateImportOptionsSetButton )
        self._import_options_button.importOptionsChanged.connect( self._UpdateImportOptionsSetButton )
        self._highlighted_gallery_import_panel.importOptionsChanged.connect( self._UpdateImportOptionsSetButton )
        self._gallery_importers_listctrl.selectionModel().selectionChanged.connect( self._UpdateImportOptionsSetButton )
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_gallery_import is not None or not self._loading_highlight_job_status.IsDone()
        
    
    def _CanHighlight( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        gallery_import = selected[0]
        
        return not self._ThisIsTheCurrentOrLoadingHighlight( gallery_import )
        
    
    def _CanRetryAnything( self ):
        
        return self._CanRetryIgnored() or self._CanRetryFailed()
        
    
    def _CanRetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _ClearExistingHighlight( self ):
        
        if not self._loading_highlight_job_status.IsDone():
            
            self._loading_highlight_job_status.Cancel()
            
        
        if self._highlighted_gallery_import is not None:
            
            self._highlighted_gallery_import.PublishToPage( False )
            
            self._highlighted_gallery_import = None
            
            self._multiple_gallery_import.ClearHighlightedGalleryImport()
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no highlighted query' )
        
        self._page.SwapMediaResultsPanel( panel )
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToDisplayTuple( self, gallery_import ):
        
        query_text = gallery_import.GetQueryText()
        
        pretty_query_text = query_text
        
        if gallery_import == self._highlighted_gallery_import:
            
            pretty_query_text = f'* {pretty_query_text}'
            
        elif not self._loading_highlight_job_status.IsDone():
            
            downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
            
            if downloader is not None and gallery_import == downloader:
                
                pretty_query_text = f'> {pretty_query_text}'
                
            
        
        source = gallery_import.GetSourceName()
        
        pretty_source = source
        
        files_finished = gallery_import.FilesFinished()
        files_paused = gallery_import.FilesPaused()
        
        if files_finished:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
        elif files_paused:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        gallery_finished = gallery_import.GalleryFinished()
        gallery_paused = gallery_import.GalleryPaused()
        
        if gallery_finished:
            
            pretty_gallery_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
        elif gallery_paused:
            
            pretty_gallery_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_gallery_paused = ''
            
        
        ( status_enum, pretty_status ) = gallery_import.GetSimpleStatus()
        
        file_seed_cache_status = gallery_import.GetFileSeedCache().GetStatus()
        
        pretty_progress = file_seed_cache_status.GetStatusText( simple = True )
        
        added = gallery_import.GetCreationTime()
        
        pretty_added = HydrusTime.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        return ( pretty_query_text, pretty_source, pretty_files_paused, pretty_gallery_paused, pretty_status, pretty_progress, pretty_added )
        
    
    def _ConvertDataToSortTuple( self, gallery_import ):
        
        query_text = gallery_import.GetQueryText()
        
        source = gallery_import.GetSourceName()
        
        pretty_source = source
        
        files_finished = gallery_import.FilesFinished()
        files_paused = gallery_import.FilesPaused()
        
        if files_finished:
            
            sort_files_paused = -1
            
        elif files_paused:
            
            sort_files_paused = 0
            
        else:
            
            sort_files_paused = 1
            
        
        gallery_finished = gallery_import.GalleryFinished()
        gallery_paused = gallery_import.GalleryPaused()
        
        if gallery_finished:
            
            sort_gallery_paused = -1
            
        elif gallery_paused:
            
            sort_gallery_paused = 0
            
        else:
            
            sort_gallery_paused = 1
            
        
        ( status_enum, pretty_status ) = gallery_import.GetSimpleStatus()
        
        sort_status = ClientImporting.downloader_enum_sort_lookup[ status_enum ]
        
        file_seed_cache_status = gallery_import.GetFileSeedCache().GetStatus()
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        progress = ( num_total, num_done )
        
        added = gallery_import.GetCreationTime()
        
        return ( query_text, pretty_source, sort_files_paused, sort_gallery_paused, sort_status, progress, added )
        
    
    def _CopySelectedQueries( self ):
        
        gallery_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_importers ) > 0:
            
            text = '\n'.join( ( gallery_importer.GetQueryText() for gallery_importer in gallery_importers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no highlighted query'
        
    
    def _GetListCtrlMenu( self ):
        
        selected_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected_importers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = ClientGUIMenus.GenerateMenu( self )

        ClientGUIMenus.AppendMenuItem( menu, 'copy queries', 'Copy all the selected downloaders\' queries to clipboard.', self._CopySelectedQueries )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        single_selected_presentation_import_options = None
        
        if len( selected_importers ) == 1:
            
            ( importer, ) = selected_importers
            
            fio = importer.GetFileImportOptions()
            
            single_selected_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( fio, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
        
        AddPresentationSubmenu( menu, 'downloader', single_selected_presentation_import_options, self._ShowSelectedImportersFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( selected_importers ) == 1:
            
            ( importer, ) = selected_importers
            
            file_seed_cache = importer.GetFileSeedCache()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show file log', 'Show the file log windows for the selected query.', self._ShowSelectedImportersFileSeedCaches )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIFileSeedCache.PopulateFileSeedCacheMenu( self, submenu, file_seed_cache, [] )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file log' )
            
            gallery_seed_log = importer.GetGallerySeedLog()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show search log', 'Show the search log windows for the selected query.', self._ShowSelectedImportersGallerySeedLogs )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIGallerySeedLog.PopulateGallerySeedLogButton( self, submenu, gallery_seed_log, [], False, True, 'search' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'search log' )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, 'show file logs', 'Show the file log windows for the selected queries.', self._ShowSelectedImportersFileSeedCaches )
            ClientGUIMenus.AppendMenuItem( menu, 'show search log', 'Show the search log windows for the selected query.', self._ShowSelectedImportersGallerySeedLogs )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove', 'Remove the selected queries.', self._RemoveGalleryImports )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected downloaders\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play search', 'Pause/play all the selected downloaders\' gallery searches.', self._PausePlayGallery )
        
        return menu
        
    
    def _HighlightGalleryImport( self, new_highlight ):
        
        if self._ThisIsTheCurrentOrLoadingHighlight( new_highlight ):
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
            
            name = new_highlight.GetQueryText()
            
            self._loading_highlight_job_status.SetStatusTitle( f'Loading {name}' )
            
            self._loading_highlight_job_status.SetVariable( 'downloader', new_highlight )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._gallery_importers_listctrl.UpdateDatas()
            
            job_status = self._loading_highlight_job_status
            
            panel = ClientGUIMediaResultsPanelLoading.MediaResultsPanelLoading( self._page, self._page_key, self._page_manager )
            
            self._page.SwapMediaResultsPanel( panel )
            
            def work_callable():
                
                all_media_results = []
                
                start_time = HydrusTime.GetNowFloat()
                
                hashes = new_highlight.GetPresentedHashes()
                
                if job_status.IsCancelled():
                    
                    return all_media_results
                    
                
                num_to_do = len( hashes )
                
                BLOCK_SIZE = 256
                
                have_published_job_status = False
                
                for ( i, block_of_hashes ) in enumerate( HydrusLists.SplitIteratorIntoChunks( hashes, BLOCK_SIZE ) ):
                    
                    num_done = i * BLOCK_SIZE
                    
                    job_status.SetStatusText( 'Loading files: {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) ) )
                    job_status.SetGauge( num_done, num_to_do )
                    
                    if not have_published_job_status and HydrusTime.TimeHasPassedFloat( start_time + 2 ):
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        have_published_job_status = True
                        
                    
                    if job_status.IsCancelled():
                        
                        return all_media_results
                        
                    
                    block_of_media_results = CG.client_controller.Read( 'media_results', block_of_hashes, sorted = True )
                    
                    all_media_results.extend( block_of_media_results )
                    
                
                job_status.SetStatusText( 'Done!' )
                job_status.DeleteGauge()
                
                return all_media_results
                
            
            def publish_callable( media_results ):
                
                try:
                    
                    if job_status != self._loading_highlight_job_status or job_status.IsCancelled():
                        
                        return
                        
                    
                    self._highlighted_gallery_import = new_highlight
                    
                    self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
                    
                    self._highlighted_gallery_import.PublishToPage( True )
                    
                    panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
                    
                    panel.SetEmptyPageStatusOverride( 'no files for this query and its publishing settings' )
                    
                    self._page.SwapMediaResultsPanel( panel )
                    
                    self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
                    
                finally:
                    
                    self._gallery_importers_listctrl_panel.UpdateButtons()
                    
                    self._gallery_importers_listctrl.UpdateDatas()
                    
                    job_status.FinishAndDismiss()
                    
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
    def _HighlightSelectedGalleryImport( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightGalleryImport( new_highlight )
            
        
    
    def _PausePlayFiles( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayFiles()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PausePlayGallery( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayGallery()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PendQueries( self, queries ):
        
        results = self._multiple_gallery_import.PendQueries( queries )
        
        if len( results ) > 0 and self._highlighted_gallery_import is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            first_result = results[ 0 ]
            
            self._HighlightGalleryImport( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _RemoveGalleryImports( self ):
        
        removees = list( self._gallery_importers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        
        for gallery_import in removees:
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        message = 'Remove the ' + HydrusNumbers.ToHumanInt( len( removees ) ) + ' selected queries?'
        
        if num_working > 0:
            
            message += '\n' * 2
            message += HydrusNumbers.ToHumanInt( num_working ) + ' are still working.'
            
        
        if self._highlighted_gallery_import is not None and self._highlighted_gallery_import in removees:
            
            message += '\n' * 2
            message += 'The currently highlighted query will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            highlight_was_included = False
            
            for gallery_import in removees:
                
                if self._ThisIsTheCurrentOrLoadingHighlight( gallery_import ):
                    
                    highlight_was_included = True
                    
                
                self._multiple_gallery_import.RemoveGalleryImport( gallery_import.GetGalleryImportKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryFailed()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _RetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryIgnored( ignored_regex = ignored_regex )
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _SetGUGKeyAndName( self, gug_key_and_name ):
        
        current_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        current_input_value = self._query_input.GetValue()
        
        should_initialise_new_text = current_input_value in ( current_initial_search_text, '' )
        
        self._multiple_gallery_import.SetGUGKeyAndName( gug_key_and_name )
        
        if should_initialise_new_text:
            
            new_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
            
            self._query_input.setPlaceholderText( new_initial_search_text )
            
        
        self._query_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
    def _SetOptionsToGalleryImports( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        message = 'Set the page\'s current file limit and import options to all the selected queries?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            file_limit = self._file_limit.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            note_import_options = self._import_options_button.GetNoteImportOptions()
            
            for gallery_import in gallery_imports:
                
                gallery_import.SetFileLimit( file_limit )
                gallery_import.SetFileImportOptions( file_import_options )
                gallery_import.SetTagImportOptions( tag_import_options )
                gallery_import.SetNoteImportOptions( note_import_options )
                
            
            self._UpdateImportOptionsSetButton()
            
        
    
    def _GetCogIconMenuTemplateItems( self ) -> list[ ClientGUIMenuButton.MenuTemplateItem ]:
        
        menu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            self._multiple_gallery_import.FlipStartFileQueuesPaused,
            self._multiple_gallery_import.GetStartFileQueuesPaused
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'start new importers\' files paused', 'Start any new importers in a file import-paused state.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            self._multiple_gallery_import.FlipStartGalleryQueuesPaused,
            self._multiple_gallery_import.GetStartGalleryQueuesPaused
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'start new importers\' search paused', 'Start any new importers in a gallery search-paused state.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            self._multiple_gallery_import.FlipDoNotAllowNewDupes,
            self._multiple_gallery_import.GetDoNotAllowNewDupes
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'do not allow new duplicates', 'This will discard any query/source pair you try to add that is already in the list.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            self._multiple_gallery_import.FlipMergeSimultaneousPendsToOneImporter,
            self._multiple_gallery_import.GetMergeSimultaneousPendsToOneImporter
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck('bundle multiple pasted queries into one importer (advanced)', 'If you are pasting many small queries at once (such as md5 lookups), check this to smooth out the workflow.', check_manager ) )
        
        return menu_template_items
        
    
    def _ShowSelectedImportersFileSeedCaches( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        gallery_import = gallery_imports[0]
        
        file_seed_cache = gallery_import.GetFileSeedCache()
        
        title = 'file log'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIFileSeedCache.EditFileSeedCachePanel( frame, file_seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _ShowSelectedImportersFiles( self, presentation_import_options = None ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for gallery_import in gallery_imports:
            
            gallery_hashes = gallery_import.GetPresentedHashes( presentation_import_options = presentation_import_options )
            
            new_hashes = [ hash for hash in gallery_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
            
            self._page.SwapMediaResultsPanel( panel )
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No presented files for that selection!' )
            
        
    
    def _ShowSelectedImportersGallerySeedLogs( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        gallery_import = gallery_imports[0]
        
        gallery_seed_log = gallery_import.GetGallerySeedLog()
        
        title = 'search log'
        frame_key = 'gallery_import_log'
        
        read_only = False
        can_generate_more_pages = True
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIGallerySeedLog.EditGallerySeedLogPanel( frame, read_only, can_generate_more_pages, 'search', gallery_seed_log )
        
        frame.SetPanel( panel )
        
    
    def _ThisIsTheCurrentOrLoadingHighlight( self, gallery_import ):
        
        if self._highlighted_gallery_import is not None and gallery_import == self._highlighted_gallery_import:
            
            return True
            
        else:
            
            if not self._loading_highlight_job_status.IsDone():
                
                downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
                
                if downloader is not None and downloader == gallery_import:
                    
                    return True
                    
                
            
            return False
            
        
    
    def _UpdateImportOptionsSetButton( self ):
        
        selected_gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        show_it = False
        
        if len( selected_gallery_imports ) > 0:
            
            # ok the serialisable comparison sucks, but we can cut down the repeated work to just one per future run of this method by updating our children with exactly our object
            
            file_limit = self._file_limit.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            note_import_options = self._import_options_button.GetNoteImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            
            file_import_options_string = None
            note_import_options_string = None
            tag_import_options_string = None
            
            for gallery_import in selected_gallery_imports:
                
                if gallery_import.GetFileLimit() != file_limit:
                    
                    show_it = True
                    
                    break
                    
                
                gallery_import_file_import_options = gallery_import.GetFileImportOptions()
                
                if gallery_import_file_import_options != file_import_options:
                    
                    if file_import_options_string is None:
                        
                        file_import_options_string = file_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if gallery_import_file_import_options.DumpToString() == file_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        gallery_import.SetFileImportOptions( file_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
                gallery_import_note_import_options = gallery_import.GetNoteImportOptions()
                
                if gallery_import_note_import_options != note_import_options:
                    
                    if note_import_options_string is None:
                        
                        note_import_options_string = note_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if gallery_import_note_import_options.DumpToString() == note_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        gallery_import.SetNoteImportOptions( note_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
                gallery_import_tag_import_options = gallery_import.GetTagImportOptions()
                
                if gallery_import_tag_import_options != tag_import_options:
                    
                    if tag_import_options_string is None:
                        
                        tag_import_options_string = tag_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if gallery_import_tag_import_options.DumpToString() == tag_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        gallery_import.SetTagImportOptions( tag_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
            
        
        self._set_options_to_queries_button.setVisible( show_it )
        
    
    def _UpdateImportStatus( self ):
        
        # TODO: Surely this can be optimised, especially with our new multi-column list tech
        # perhaps break any sort to a ten second timer or something
        
        if HydrusTime.TimeHasPassedFloat( self._next_update_time ):
            
            num_items = len( self._gallery_importers_listctrl.GetData() )
            
            min_time = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'gallery_page_status_update_time_minimum_ms' ) )
            denominator = CG.client_controller.new_options.GetInteger( 'gallery_page_status_update_time_ratio_denominator' )
            
            try:
                
                update_period = max( min_time, num_items / denominator )
                
            except Exception as e:
                
                update_period = 1.0
                
            
            self._next_update_time = HydrusTime.GetNowFloat() + update_period
            
            #
            
            last_time_imports_changed = self._multiple_gallery_import.GetLastTimeImportsChanged()
            
            num_gallery_imports = self._multiple_gallery_import.GetNumGalleryImports()
            
            #
            
            if num_gallery_imports == 0:
                
                text_top = 'waiting for new queries'
                text_bottom = ''
                
            else:
                
                file_seed_cache_status = self._multiple_gallery_import.GetTotalStatus()
                
                ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
                
                text_top = '{} queries - {}'.format( HydrusNumbers.ToHumanInt( num_gallery_imports ), HydrusNumbers.ValueRangeToPrettyString( num_done, num_total ) )
                text_bottom = file_seed_cache_status.GetStatusText()
                
            
            self._gallery_importers_status_st_top.setText( text_top )
            self._gallery_importers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_imports_changed != last_time_imports_changed:
                
                self._last_time_imports_changed = last_time_imports_changed
                
                gallery_imports = self._multiple_gallery_import.GetGalleryImports()
                
                self._gallery_importers_listctrl.SetData( gallery_imports )
                
                ideal_rows = len( gallery_imports )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._gallery_importers_listctrl.ForceHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._gallery_importers_listctrl.UpdateDatas( check_for_changed_sort_data = True )
                
                if sort_data_has_changed:
                    
                    self._gallery_importers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0.0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        num_working = 0
        num_items = 0
        
        for gallery_import in self._multiple_gallery_import.GetGalleryImports():
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
            num_items += len( gallery_import.GetFileSeedCache() )
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusNumbers.ToHumanInt( num_working ) + ' queries are still importing.' )
            
        
        if not for_session_close and CG.client_controller.new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) and num_items > 0:
            
            raise HydrusExceptions.VetoException( f'This is a gallery downloader page holding {HydrusNumbers.ToHumanInt(num_items)} import objects.' )
            
        
    
    def EventFileLimit( self ):
        
        self._multiple_gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
    
    def PendSubscriptionGapDownloader( self, gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit ):
        
        new_query = self._multiple_gallery_import.PendSubscriptionGapDownloader( gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit )
        
        if new_query is not None and self._highlighted_gallery_import is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            self._HighlightGalleryImport( new_query )
            
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._query_input )
        
    
    def Start( self ):
        
        self._multiple_gallery_import.Start( self._page_key )
        
    

class SidebarImporterMultipleWatcher( SidebarImporter ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        self._last_time_watchers_changed = 0
        self._next_update_time = 0.0
        
        self._multiple_watcher_import = self._page_manager.GetVariable( 'multiple_watcher_import' )
        
        self._highlighted_watcher = self._multiple_watcher_import.GetHighlightedWatcher()
        
        self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._loading_highlight_job_status.Finish()
        
        checker_options = self._multiple_watcher_import.GetCheckerOptions()
        file_import_options = self._multiple_watcher_import.GetFileImportOptions()
        tag_import_options = self._multiple_watcher_import.GetTagImportOptions()
        note_import_options = self._multiple_watcher_import.GetNoteImportOptions()
        
        #
        
        self._watchers_panel = ClientGUICommon.StaticBox( self, 'watchers', start_expanded = True, can_expand = True )
        
        self._watchers_status_st_top = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        self._watchers_status_st_bottom = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        
        self._watchers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._watchers_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_WATCHERS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._watchers_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._watchers_listctrl_panel, 4, model, delete_key_callback = self._RemoveWatchers, activation_callback = self._HighlightSelectedWatcher )
        
        self._watchers_listctrl_panel.SetListCtrl( self._watchers_listctrl )
        
        self._watchers_listctrl_panel.AddIconButton( CC.global_icons().highlight, self._HighlightSelectedWatcher, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._watchers_listctrl_panel.AddIconButton( CC.global_icons().clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._watchers_listctrl_panel.AddIconButton( CC.global_icons().file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddIconButton( CC.global_icons().gallery_pause, self._PausePlayChecking, tooltip = 'pause/play checking', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'check now', self._CheckNow, enabled_only_on_selection = True )
        
        menu_template_items = []
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry ignored', 'Retry the files that were moved over for one reason or another.', self._RetryIgnored )
        menu_template_item.SetVisibleCallable( self._CanRetryIgnored )
        
        menu_template_items.append( menu_template_item )
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry failed', 'Retry the files that failed.', self._RetryFailed )
        menu_template_item.SetVisibleCallable( self._CanRetryFailed )
        
        menu_template_items.append( menu_template_item )
        
        self._watchers_listctrl_panel.AddMenuIconButton( CC.global_icons().retry, 'retry commands', menu_template_items, enabled_check_func = self._CanRetryAnything )
        
        self._watchers_listctrl_panel.AddIconButton( CC.global_icons().trash, self._RemoveWatchers, tooltip = 'remove selected', enabled_only_on_selection = True )
        
        self._watchers_listctrl.Sort()
        
        self._watcher_url_input = ClientGUITextInput.TextAndPasteCtrl( self._watchers_panel, self._AddURLs )
        
        self._watcher_url_input.setPlaceholderText( 'watcher url' )
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._watchers_panel, checker_options )
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        self._set_options_to_watchers_button = ClientGUICommon.BetterButton( self, 'update selected with current options', self._SetOptionsToWatchers )
        self._set_options_to_watchers_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Each watcher has its own checker and import options (you can review them in the highlight panel below). These are not updated if the main page\'s options are updated. It seems some watchers in your selection differ with what the page currently has. Clicking here will update the selected watchers with whatever the page currently has.' ) )
        self._set_options_to_watchers_button.setVisible( False )
        
        # suck up watchers from elsewhere in the program (presents a checkboxlistdialog)
        
        #
        
        self._highlighted_watcher_panel = ClientGUIImport.WatcherReviewPanel( self, self._page_key, name = 'highlighted watcher' )
        
        self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
        
        #
        
        self._watchers_panel.Add( self._watchers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._watchers_panel.Add( self._watcher_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._set_options_to_watchers_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._watchers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._watchers_listctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        
        self._UpdateImportStatus()
        
        CG.client_controller.sub( self, '_ClearExistingHighlightAndPanel', 'clear_multiwatcher_highlights' )
        
        self._import_options_button.fileImportOptionsChanged.connect( self._OptionsUpdated )
        self._import_options_button.noteImportOptionsChanged.connect( self._OptionsUpdated )
        self._import_options_button.tagImportOptionsChanged.connect( self._OptionsUpdated )
        
        self._checker_options.valueChanged.connect( self._OptionsUpdated )
        
        self._import_options_button.importOptionsChanged.connect( self._UpdateImportOptionsSetButton )
        self._checker_options.valueChanged.connect( self._UpdateImportOptionsSetButton )
        self._highlighted_watcher_panel.importOptionsChanged.connect( self._UpdateImportOptionsSetButton )
        self._watchers_listctrl.selectionModel().selectionChanged.connect( self._UpdateImportOptionsSetButton )
        
    
    def _AddURLs( self, urls, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        first_result = None
        
        for url in urls:
            
            result = self._multiple_watcher_import.AddURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
            
            if result is not None and first_result is None:
                
                first_result = result
                
            
        
        if first_result is not None and self._highlighted_watcher is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_watcher' ):
            
            self._HighlightWatcher( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_watcher is not None or not self._loading_highlight_job_status.IsDone()
        
    
    def _CanHighlight( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        watcher = selected[0]
        
        return not self._ThisIsTheCurrentOrLoadingHighlight( watcher )
        
    
    def _CanRetryAnything( self ):
        
        return self._CanRetryIgnored() or self._CanRetryFailed()
        
    
    def _CanRetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _CheckNow( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.CheckNow()
            
        
    
    def _ClearExistingHighlight( self ):
        
        if not self._loading_highlight_job_status.IsDone():
            
            self._loading_highlight_job_status.Cancel()
            
        
        if self._highlighted_watcher is not None:
            
            self._highlighted_watcher.PublishToPage( False )
            
            self._highlighted_watcher = None
            
            self._multiple_watcher_import.ClearHighlightedWatcher()
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._highlighted_watcher_panel.SetWatcher( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no highlighted watcher' )
        
        self._page.SwapMediaResultsPanel( panel )
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToDisplayTuple( self, watcher: ClientImportWatchers.WatcherImport ):
        
        subject = watcher.GetSubject()
        
        pretty_subject = subject
        
        if watcher == self._highlighted_watcher:
            
            pretty_subject = f'* {pretty_subject}'
            
        elif not self._loading_highlight_job_status.IsDone():
            
            downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
            
            if downloader is not None and downloader == watcher:
                
                pretty_subject = f'> {pretty_subject}'
                
            
        
        files_paused = watcher.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        checking_dead = watcher.IsDead()
        checking_paused = watcher.CheckingPaused()
        
        if checking_dead:
            
            pretty_checking_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
        elif checking_paused:
            
            pretty_checking_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_checking_paused = ''
            
        
        file_seed_cache_status = watcher.GetFileSeedCache().GetStatus()
        
        pretty_progress = file_seed_cache_status.GetStatusText( simple = True )
        
        added = watcher.GetCreationTime()
        
        pretty_added = HydrusTime.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        ( status_enum, pretty_watcher_status ) = self._multiple_watcher_import.GetWatcherSimpleStatus( watcher )
        
        return ( pretty_subject, pretty_files_paused, pretty_checking_paused, pretty_watcher_status, pretty_progress, pretty_added )
        
    
    def _ConvertDataToSortTuple( self, watcher: ClientImportWatchers.WatcherImport ):
        
        subject = watcher.GetSubject()
        
        files_paused = watcher.FilesPaused()
        
        checking_dead = watcher.IsDead()
        checking_paused = watcher.CheckingPaused()
        
        if checking_dead:
            
            sort_checking_paused = -1
            
        elif checking_paused:
            
            sort_checking_paused = 0
            
        else:
            
            sort_checking_paused = 1
            
        
        file_seed_cache_status = watcher.GetFileSeedCache().GetStatus()
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        progress = ( num_total, num_done )
        
        added = watcher.GetCreationTime()
        
        ( status_enum, pretty_watcher_status ) = self._multiple_watcher_import.GetWatcherSimpleStatus( watcher )
        
        checking_status = watcher.GetCheckingStatus()
        
        if checking_status == ClientImporting.CHECKER_STATUS_OK:
            
            next_check_time = watcher.GetNextCheckTime()
            
            if next_check_time is None:
                
                next_check_time = 0
                
            
            sort_watcher_status = ( ClientImporting.downloader_enum_sort_lookup[ status_enum ], next_check_time )
            
        else:
            
            # this lets 404 and DEAD sort different
            
            sort_watcher_status = ( ClientImporting.downloader_enum_sort_lookup[ status_enum ], checking_status )
            
        
        return ( subject, files_paused, sort_checking_paused, sort_watcher_status, progress, added )
        
    
    def _CopySelectedSubjects( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = '\n'.join( ( watcher.GetSubject() for watcher in watchers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = '\n'.join( ( watcher.GetURL() for watcher in watchers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no highlighted watcher'
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy urls', 'Copy all the selected watchers\' urls to clipboard.', self._CopySelectedURLs )
        ClientGUIMenus.AppendMenuItem( menu, 'open urls', 'Open all the selected watchers\' urls in your browser.', self._OpenSelectedURLs )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy subjects', 'Copy all the selected watchers\' subjects to clipboard.', self._CopySelectedSubjects )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        single_selected_presentation_import_options = None
        
        if len( selected_watchers ) == 1:
            
            ( watcher, ) = selected_watchers
            
            fio = watcher.GetFileImportOptions()
            
            single_selected_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( fio, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
        
        AddPresentationSubmenu( menu, 'watcher', single_selected_presentation_import_options, self._ShowSelectedImportersFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( selected_watchers ) == 1:
            
            ( watcher, ) = selected_watchers
            
            file_seed_cache = watcher.GetFileSeedCache()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show file log', 'Show the file log windows for the selected watcher.', self._ShowSelectedImportersFileSeedCaches )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIFileSeedCache.PopulateFileSeedCacheMenu( self, submenu, file_seed_cache, [] )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file log' )
            
            gallery_seed_log = watcher.GetGallerySeedLog()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show check log', 'Show the check log windows for the selected watcher.', self._ShowSelectedImportersGallerySeedLogs )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIGallerySeedLog.PopulateGallerySeedLogButton( self, submenu, gallery_seed_log, [], True, False, 'check' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'check log' )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, 'show file logs', 'Show the file log windows for the selected queries.', self._ShowSelectedImportersFileSeedCaches )
            ClientGUIMenus.AppendMenuItem( menu, 'show check log', 'Show the checker log windows for the selected watcher.', self._ShowSelectedImportersGallerySeedLogs )
            
        
        if self._CanRetryFailed() or self._CanRetryIgnored():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._CanRetryFailed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
                
            
            if self._CanRetryIgnored():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry ignored', 'Retry all the ignored downloads.', self._RetryIgnored )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove selected', 'Remove the selected watchers.', self._RemoveWatchers )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected watchers\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play checking', 'Pause/play all the selected watchers\' checking routines.', self._PausePlayChecking )
        
        return menu
        
    
    def _HighlightWatcher( self, new_highlight ):
        
        if self._ThisIsTheCurrentOrLoadingHighlight( new_highlight ):
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
            
            name = new_highlight.GetSubject()
            
            self._loading_highlight_job_status.SetStatusTitle( f'Loading {name}' )
            
            self._loading_highlight_job_status.SetVariable( 'downloader', new_highlight )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._watchers_listctrl.UpdateDatas()
            
            job_status = self._loading_highlight_job_status
            
            panel = ClientGUIMediaResultsPanelLoading.MediaResultsPanelLoading( self._page, self._page_key, self._page_manager )
            
            self._page.SwapMediaResultsPanel( panel )
            
            def work_callable():
                
                start_time = HydrusTime.GetNowFloat()
                
                all_media_results = []
                
                hashes = new_highlight.GetPresentedHashes()
                
                num_to_do = len( hashes )
                
                BLOCK_SIZE = 256
                
                have_published_job_status = False
                
                if job_status.IsCancelled():
                    
                    return all_media_results
                    
                
                for ( i, block_of_hashes ) in enumerate( HydrusLists.SplitIteratorIntoChunks( hashes, BLOCK_SIZE ) ):
                    
                    num_done = i * BLOCK_SIZE
                    
                    job_status.SetStatusText( 'Loading files: {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) ) )
                    job_status.SetGauge( num_done, num_to_do )
                    
                    if not have_published_job_status and HydrusTime.TimeHasPassedFloat( start_time + 2 ):
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        have_published_job_status = True
                        
                    
                    if job_status.IsCancelled():
                        
                        return all_media_results
                        
                    
                    block_of_media_results = CG.client_controller.Read( 'media_results', block_of_hashes, sorted = True )
                    
                    all_media_results.extend( block_of_media_results )
                    
                
                job_status.SetStatusText( 'Done!' )
                job_status.DeleteGauge()
                
                return all_media_results
                
            
            def publish_callable( media_results ):
                
                try:
                    
                    if job_status != self._loading_highlight_job_status or job_status.IsCancelled():
                        
                        return
                        
                    
                    self._highlighted_watcher = new_highlight
                    
                    self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
                    
                    self._highlighted_watcher.PublishToPage( True )
                    
                    panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
                    
                    panel.SetEmptyPageStatusOverride( 'no files for this watcher and its publishing settings' )
                    
                    self._page.SwapMediaResultsPanel( panel )
                    
                    self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
                    
                finally:
                    
                    self._watchers_listctrl_panel.UpdateButtons()
                    
                    self._watchers_listctrl.UpdateDatas()
                    
                    job_status.FinishAndDismiss()
                    
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
    def _HighlightSelectedWatcher( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightWatcher( new_highlight )
            
        
    
    def _OpenSelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            if len( watchers ) > 10:
                
                message = 'You have many watchers selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            for watcher in watchers:
                
                ClientPaths.LaunchURLInWebBrowser( watcher.GetURL() )
                
            
        
    
    def _OptionsUpdated( self, *args, **kwargs ):
        
        self._multiple_watcher_import.SetCheckerOptions( self._checker_options.GetValue() )
        self._multiple_watcher_import.SetFileImportOptions( self._import_options_button.GetFileImportOptions() )
        self._multiple_watcher_import.SetNoteImportOptions( self._import_options_button.GetNoteImportOptions() )
        self._multiple_watcher_import.SetTagImportOptions( self._import_options_button.GetTagImportOptions() )
        
    
    def _PausePlayChecking( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayChecking()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _PausePlayFiles( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayFiles()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _RemoveWatchers( self ):
        
        removees = list( self._watchers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        num_alive = 0
        
        for watcher in removees:
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            if watcher.CurrentlyAlive():
                
                num_alive += 1
                
            
        
        message = 'Remove the ' + HydrusNumbers.ToHumanInt( len( removees ) ) + ' selected watchers?'
        
        if num_working > 0:
            
            message += '\n' * 2
            message += HydrusNumbers.ToHumanInt( num_working ) + ' are still working.'
            
        
        if num_alive > 0:
            
            message += '\n' * 2
            message += HydrusNumbers.ToHumanInt( num_alive ) + ' are not yet DEAD.'
            
        
        if self._highlighted_watcher is not None and self._highlighted_watcher in removees:
            
            message += '\n' * 2
            message += 'The currently highlighted watcher will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            highlight_was_included = False
            
            for watcher in removees:
                
                if self._ThisIsTheCurrentOrLoadingHighlight( watcher ):
                    
                    highlight_was_included = True
                    
                
                self._multiple_watcher_import.RemoveWatcher( watcher.GetWatcherKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryFailed()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _RetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryIgnored( ignored_regex = ignored_regex )
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _SetOptionsToWatchers( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        message = 'Set the current checker and import options to all the selected watchers?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            checker_options = self._checker_options.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            note_import_options = self._import_options_button.GetNoteImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            
            for watcher in watchers:
                
                watcher.SetCheckerOptions( checker_options )
                watcher.SetFileImportOptions( file_import_options )
                watcher.SetNoteImportOptions( note_import_options )
                watcher.SetTagImportOptions( tag_import_options )
                
            
            self._UpdateImportOptionsSetButton()
            
        
    
    def _ShowSelectedImportersFileSeedCaches( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        watcher = watchers[0]
        
        file_seed_cache = watcher.GetFileSeedCache()
        
        title = 'file log'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIFileSeedCache.EditFileSeedCachePanel( frame, file_seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _ShowSelectedImportersFiles( self, presentation_import_options = None ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for watcher in watchers:
            
            watcher_hashes = watcher.GetPresentedHashes( presentation_import_options = presentation_import_options )
            
            new_hashes = [ hash for hash in watcher_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
            
            self._page.SwapMediaResultsPanel( panel )
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No presented files for that selection!' )
            
        
    
    def _ShowSelectedImportersGallerySeedLogs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        watcher = watchers[0]
        
        gallery_seed_log = watcher.GetGallerySeedLog()
        
        title = 'check log'
        frame_key = 'gallery_import_log'
        
        read_only = True
        can_generate_more_pages = False
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIGallerySeedLog.EditGallerySeedLogPanel( frame, read_only, can_generate_more_pages, 'check', gallery_seed_log )
        
        frame.SetPanel( panel )
        
    
    def _ThisIsTheCurrentOrLoadingHighlight( self, watcher ):
        
        if self._highlighted_watcher is not None and watcher == self._highlighted_watcher:
            
            return True
            
        else:
            
            if not self._loading_highlight_job_status.IsDone():
                
                downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
                
                if downloader is not None and downloader == watcher:
                    
                    return True
                    
                
            
            return False
            
        
    
    def _UpdateImportOptionsSetButton( self ):
        
        selected_watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        show_it = False
        
        if len( selected_watchers ) > 0:
            
            # ok the serialisable comparison sucks, but we can cut down the repeated work to just one per future run of this method by updating our children with exactly our object
            
            checker_options = self._checker_options.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            note_import_options = self._import_options_button.GetNoteImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            
            checker_options_string = None
            file_import_options_string = None
            note_import_options_string = None
            tag_import_options_string = None
            
            for watcher in selected_watchers:
                
                watcher_checker_options = watcher.GetCheckerOptions()
                
                if watcher_checker_options != checker_options:
                    
                    if checker_options_string is None:
                        
                        checker_options_string = checker_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if watcher_checker_options.DumpToString() == checker_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        watcher.SetCheckerOptions( checker_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
                watcher_file_import_options = watcher.GetFileImportOptions()
                
                if watcher_file_import_options != file_import_options:
                    
                    if file_import_options_string is None:
                        
                        file_import_options_string = file_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if watcher_file_import_options.DumpToString() == file_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        watcher.SetFileImportOptions( file_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
                watcher_note_import_options = watcher.GetNoteImportOptions()
                
                if watcher_note_import_options != note_import_options:
                    
                    if note_import_options_string is None:
                        
                        note_import_options_string = note_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if watcher_note_import_options.DumpToString() == note_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        watcher.SetNoteImportOptions( note_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
                watcher_tag_import_options = watcher.GetTagImportOptions()
                
                if watcher_tag_import_options != tag_import_options:
                    
                    if tag_import_options_string is None:
                        
                        tag_import_options_string = tag_import_options.DumpToString()
                        
                    
                    # not the same object, let's see if they have the same value
                    if watcher_tag_import_options.DumpToString() == tag_import_options_string:
                        
                        # we have the same value here, just not the same object. let's make the check faster next time
                        watcher.SetTagImportOptions( tag_import_options )
                        
                    else:
                        
                        show_it = True
                        
                        break
                        
                    
                
            
        
        self._set_options_to_watchers_button.setVisible( show_it )
        
    
    def _UpdateImportStatus( self ):
        
        # TODO: Surely this can be optimised, especially with our new multi-column list tech
        # perhaps break any sort to a ten second timer or something
        
        if HydrusTime.TimeHasPassedFloat( self._next_update_time ):
            
            num_items = len( self._watchers_listctrl.GetData() )
            
            min_time = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'watcher_page_status_update_time_minimum_ms' ) )
            denominator = CG.client_controller.new_options.GetInteger( 'watcher_page_status_update_time_ratio_denominator' )
            
            try:
                
                update_period = max( min_time, num_items / denominator )
                
            except Exception as e:
                
                update_period = 1.0
                
            
            self._next_update_time = HydrusTime.GetNowFloat() + update_period
            
            #
            
            last_time_watchers_changed = self._multiple_watcher_import.GetLastTimeWatchersChanged()
            num_watchers = self._multiple_watcher_import.GetNumWatchers()
            
            #
            
            if num_watchers == 0:
                
                text_top = 'waiting for new watchers'
                text_bottom = ''
                
            else:
                
                num_dead = self._multiple_watcher_import.GetNumDead()
                
                if num_dead == 0:
                    
                    num_dead_text = ''
                    
                else:
                    
                    num_dead_text = HydrusNumbers.ToHumanInt( num_dead ) + ' DEAD - '
                    
                
                file_seed_cache_status = self._multiple_watcher_import.GetTotalStatus()
                
                ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
                
                text_top = '{} watchers - {}'.format( HydrusNumbers.ToHumanInt( num_watchers ), HydrusNumbers.ValueRangeToPrettyString( num_done, num_total ) )
                text_bottom = file_seed_cache_status.GetStatusText()
                
            
            self._watchers_status_st_top.setText( text_top )
            self._watchers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_watchers_changed != last_time_watchers_changed:
                
                self._last_time_watchers_changed = last_time_watchers_changed
                
                watchers = self._multiple_watcher_import.GetWatchers()
                
                self._watchers_listctrl.SetData( watchers )
                
                ideal_rows = len( watchers )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._watchers_listctrl.ForceHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._watchers_listctrl.UpdateDatas( check_for_changed_sort_data = True )
                
                if sort_data_has_changed:
                    
                    self._watchers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0.0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        num_working = 0
        num_items = 0
        
        for watcher in self._multiple_watcher_import.GetWatchers():
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            num_items += len( watcher.GetFileSeedCache() )
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusNumbers.ToHumanInt( num_working ) + ' watchers are still importing.' )
            
        
        if not for_session_close and CG.client_controller.new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) and num_items > 0:
            
            raise HydrusExceptions.VetoException( f'This is a watcher page holding {HydrusNumbers.ToHumanInt(num_items)} import objects.' )
            
        
    
    def PendURL( self, url, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._AddURLs( ( url, ), filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._watcher_url_input )
        
    
    def Start( self ):
        
        self._multiple_watcher_import.Start( self._page_key )
        
    

class SidebarImporterSimpleDownloader( SidebarImporter ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        self._simple_downloader_import: ClientImportSimpleURLs.SimpleDownloaderImport = self._page_manager.GetVariable( 'simple_downloader_import' )
        
        #
        
        self._simple_downloader_panel = ClientGUICommon.StaticBox( self, 'simple downloader', start_expanded = True, can_expand = True )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'imports' )
        
        self._pause_files_button = ClientGUICommon.IconButton( self._import_queue_panel, CC.global_icons().file_pause, self.PauseFiles )
        self._pause_files_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play files' ) )
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        #
        
        self._simple_parsing_jobs_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'parsing' )
        
        self._pause_queue_button = ClientGUICommon.IconButton( self._simple_parsing_jobs_panel, CC.global_icons().gallery_pause, self.PauseQueue )
        self._pause_queue_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play queue' ) )
        
        self._parser_status = ClientGUICommon.BetterStaticText( self._simple_parsing_jobs_panel, ellipsize_end = True )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._simple_parsing_jobs_panel, True, False, 'parsing', self._page_key )
        
        self._page_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._simple_parsing_jobs_panel )
        
        self._pending_jobs_queue_box = ClientGUIListBoxes.QueueListBox(
            self._simple_parsing_jobs_panel,
            8,
            self._ConvertPendingJobToString,
        )
        
        self._page_url_input = ClientGUITextInput.TextAndPasteCtrl( self._simple_parsing_jobs_panel, self._PendPageURLs )
        
        self._page_url_input.setPlaceholderText( 'url to be parsed by the selected formula' )
        
        self._formulae = ClientGUICommon.BetterChoice( self._simple_parsing_jobs_panel )
        
        formulae_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._formulae, 10 )
        
        self._formulae.setMinimumWidth( formulae_width )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit formulae', 'Edit these parsing formulae.', self._EditFormulae ) )
        
        self._formula_cog = ClientGUIMenuButton.CogIconButton( self._simple_parsing_jobs_panel, menu_template_items )
        
        self._RefreshFormulae()
        
        file_import_options = self._simple_downloader_import.GetFileImportOptions()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._current_action, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_files_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        formulae_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( formulae_hbox, self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( formulae_hbox, self._formula_cog, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._parser_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_queue_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._simple_parsing_jobs_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._page_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._pending_jobs_queue_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._simple_parsing_jobs_panel.Add( self._page_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._simple_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._simple_parsing_jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._simple_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._formulae.currentIndexChanged.connect( self.EventFormulaChanged )
        
        file_seed_cache = self._simple_downloader_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._simple_downloader_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._simple_downloader_import.SetFileImportOptions )
        
        self._pending_jobs_queue_box.listBoxContentsDeleted.connect( self._QueueBoxContentsDeleted )
        self._pending_jobs_queue_box.listBoxOrderChanged.connect( self._QueueBoxOrderChanged )
        
    
    def _ConvertPendingJobToString( self, job ):
        
        ( url, simple_downloader_formula ) = job
        
        pretty_job = simple_downloader_formula.GetName() + ': ' + url
        
        return pretty_job
        
    
    def _EditFormulae( self ):
        
        def data_to_pretty_callable( data ):
            
            simple_downloader_formula = data
            
            return simple_downloader_formula.GetName()
            
        
        def edit_callable( data ):
            
            simple_downloader_formula = data
            
            name = simple_downloader_formula.GetName()
            
            try:
                
                name = ClientGUIDialogsQuick.EnterText( dlg, 'Edit name.', default = name )
                
            except HydrusExceptions.CancelledException:
                
                raise
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( dlg, 'edit formula' ) as dlg_3:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_3 )
                
                formula = simple_downloader_formula.GetFormula()
                
                control = ClientGUIParsingFormulae.EditFormulaPanel( panel, formula, lambda: ClientParsing.ParsingTestData( {}, ( '', ) ) )
                
                panel.SetControl( control )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    formula = control.GetValue()
                    
                    simple_downloader_formula = ClientParsing.SimpleDownloaderParsingFormula( name = name, formula = formula )
                    
                    return simple_downloader_formula
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def add_callable():
            
            data = ClientParsing.SimpleDownloaderParsingFormula()
            
            return edit_callable( data )
            
        
        formulae = list( CG.client_controller.new_options.GetSimpleDownloaderFormulae() )
        
        formulae.sort( key = lambda o: o.GetName() )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit simple downloader formulae' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUIListBoxes.AddEditDeleteListBoxUniqueNamedObjects( panel, height_num_chars, data_to_pretty_callable, add_callable, edit_callable )
            
            control.AddSeparator()
            control.AddImportExportButtons( ( ClientParsing.SimpleDownloaderParsingFormula, ) )
            control.AddSeparator()
            control.AddDefaultsButton( ClientDefaults.GetDefaultSimpleDownloaderFormulae )
            
            control.AddDatas( formulae )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                formulae = control.GetData()
                
                CG.client_controller.new_options.SetSimpleDownloaderFormulae( formulae )
                
            
        
        self._RefreshFormulae()
        
    
    def _PendPageURLs( self, unclean_urls ):
        
        urls = [ ClientNetworkingFunctions.EnsureURLIsEncoded( unclean_url ) for unclean_url in unclean_urls if ClientNetworkingFunctions.LooksLikeAFullURL( unclean_url ) ]
        
        simple_downloader_formula = self._formulae.GetValue()
        
        for url in urls:
            
            job = ( url, simple_downloader_formula )
            
            self._simple_downloader_import.PendJob( job )
            
        
        self._UpdateImportStatus()
        
    
    def _RefreshFormulae( self ):
        
        self._formulae.blockSignals( True )
        
        self._formulae.clear()
        
        to_select = None
        
        select_name = self._simple_downloader_import.GetFormulaName()
        
        simple_downloader_formulae = list( CG.client_controller.new_options.GetSimpleDownloaderFormulae() )
        
        simple_downloader_formulae.sort( key = lambda o: o.GetName() )
        
        for ( i, simple_downloader_formula ) in enumerate( simple_downloader_formulae ):
            
            name = simple_downloader_formula.GetName()
            
            self._formulae.addItem( name, simple_downloader_formula )
            
            if name == select_name:
                
                to_select = i
                
            
        
        self._formulae.blockSignals( False )
        
        if to_select is not None:
            
            self._formulae.setCurrentIndex( to_select )
            
        
    
    def _QueueBoxContentsDeleted( self ):
        
        jobs = self._pending_jobs_queue_box.GetData()
        
        self._simple_downloader_import.SetPendingJobs( jobs )
        
    
    def _QueueBoxOrderChanged( self ):
        
        jobs = self._pending_jobs_queue_box.GetData()
        
        self._simple_downloader_import.SetPendingJobsOrder( jobs )
        
    
    def _UpdateImportStatus( self ):
        
        ( pending_jobs, parser_status, current_action, queue_paused, files_paused ) = self._simple_downloader_import.GetStatus()
        
        current_pending_jobs = self._pending_jobs_queue_box.GetData()
        
        if current_pending_jobs != pending_jobs:
            
            self._pending_jobs_queue_box.SetData( pending_jobs )
            
        
        self._parser_status.setText( parser_status )
        
        self._current_action.setText( current_action )
        
        if files_paused:
            
            self._pause_files_button.SetIconSmart( CC.global_icons().file_play )
            
        else:
            
            self._pause_files_button.SetIconSmart( CC.global_icons().file_pause )
            
        
        if queue_paused:
            
            self._pause_queue_button.SetIconSmart( CC.global_icons().gallery_play )
            
        else:
            
            self._pause_queue_button.SetIconSmart( CC.global_icons().gallery_pause )
            
        
        ( file_network_job, page_network_job ) = self._simple_downloader_import.GetNetworkJobs()
        
        if file_network_job is None:
            
            self._file_download_control.ClearNetworkJob()
            
        else:
            
            self._file_download_control.SetNetworkJob( file_network_job )
            
        
        if page_network_job is None:
            
            self._page_download_control.ClearNetworkJob()
            
        else:
            
            self._page_download_control.SetNetworkJob( page_network_job )
            
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        if self._simple_downloader_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
        num_items = len( self._simple_downloader_import.GetFileSeedCache() )
        
        if not for_session_close and CG.client_controller.new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) and num_items > 0:
            
            raise HydrusExceptions.VetoException( f'This is a simple urls import page holding {HydrusNumbers.ToHumanInt( num_items )} import objects.' )
            
        
    
    def EventFormulaChanged( self ):
        
        formula = self._formulae.GetValue()
        
        formula_name = formula.GetName()
        
        self._simple_downloader_import.SetFormulaName( formula_name )
        CG.client_controller.new_options.SetString( 'favourite_simple_downloader_formula', formula_name )
        
    
    def PauseQueue( self ):
        
        self._simple_downloader_import.PausePlayQueue()
        
        self._UpdateImportStatus()
        
    
    def PauseFiles( self ):
        
        self._simple_downloader_import.PausePlayFiles()
        
        self._UpdateImportStatus()
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._page_url_input )
        
    
    def Start( self ):
        
        self._simple_downloader_import.Start( self._page_key )
        
    

class SidebarImporterURLs( SidebarImporter ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        #
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'url downloader', start_expanded = True, can_expand = True )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._url_panel, 'imports' )
        
        self._pause_button = ClientGUICommon.IconButton( self._import_queue_panel, CC.global_icons().file_pause, self.Pause )
        self._pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play files' ) )
        
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        self._urls_import: ClientImportSimpleURLs.URLsImport = self._page_manager.GetVariable( 'urls_import' )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, page_key = self._page_key )
        
        #
        
        self._gallery_panel = ClientGUICommon.StaticBox( self._url_panel, 'search' )
        
        self._gallery_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._gallery_panel )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._gallery_panel, False, False, 'search', page_key = self._page_key )
        
        #
        
        self._url_input = ClientGUITextInput.TextAndPasteCtrl( self._url_panel, self._PendURLs )
        
        self._url_input.setPlaceholderText( 'any url hydrus recognises, or a raw file url' )
        
        file_import_options = self._urls_import.GetFileImportOptions()
        tag_import_options = self._urls_import.GetTagImportOptions()
        note_import_options = self._urls_import.GetNoteImportOptions()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        #
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pause_button, CC.FLAGS_ON_RIGHT )

        self._import_queue_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._gallery_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._url_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._urls_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._urls_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._urls_import.SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._urls_import.SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._urls_import.SetTagImportOptions )
        
    
    def _PendURLs( self, unclean_urls, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        urls = [ ClientNetworkingFunctions.EnsureURLIsEncoded( unclean_url ) for unclean_url in unclean_urls if ClientNetworkingFunctions.LooksLikeAFullURL( unclean_url ) ]
        
        self._urls_import.PendURLs( urls, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        paused = self._urls_import.IsPaused()
        
        if paused:
            
            self._pause_button.SetIconSmart( CC.global_icons().file_play )
            
        else:
            
            self._pause_button.SetIconSmart( CC.global_icons().file_pause )
            
        
        ( file_network_job, gallery_network_job ) = self._urls_import.GetNetworkJobs()
        
        if file_network_job is None:
            
            self._file_download_control.ClearNetworkJob()
            
        else:
            
            self._file_download_control.SetNetworkJob( file_network_job )
            
        
        if gallery_network_job is None:
            
            self._gallery_download_control.ClearNetworkJob()
            
        else:
            
            self._gallery_download_control.SetNetworkJob( gallery_network_job )
            
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        if self._urls_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
        num_items = len( self._urls_import.GetFileSeedCache() )
        
        if not for_session_close and CG.client_controller.new_options.GetBoolean( 'confirm_non_empty_downloader_page_close' ) and num_items > 0:
            
            raise HydrusExceptions.VetoException( f'This is a urls import page holding {HydrusNumbers.ToHumanInt( num_items )} import objects.' )
            
        
    
    def Pause( self ):
        
        self._urls_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def PendURL( self, url, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._PendURLs( ( url, ), filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._url_input )
        
    
    def Start( self ):
        
        self._urls_import.Start( self._page_key )
        
    
