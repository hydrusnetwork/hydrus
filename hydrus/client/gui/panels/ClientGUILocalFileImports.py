import collections
import collections.abc
import os
import queue
import threading

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.files import ClientFiles
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsFiles
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.metadata import ClientTags

RESULT_NOT_PARSED = 0
RESULT_GOOD = 1
RESULT_EMPTY = 2
RESULT_MISSING = 3
RESULT_UNIMPORTABLE = 4
RESULT_OCCUPIED = 5
RESULT_SIDECAR = 6
RESULT_DIRECTORY = 7

result_str_lookup = {    
    RESULT_NOT_PARSED : 'not yet parsed',
    RESULT_GOOD : 'good (you should not see this)',
    RESULT_EMPTY : 'PROBLEM: file empty',
    RESULT_MISSING : 'PROBLEM: file missing',
    RESULT_UNIMPORTABLE : 'PROBLEM: filetype unsupported',
    RESULT_OCCUPIED : 'PROBLEM: file in use by other program',
    RESULT_SIDECAR : 'sidecar',
    RESULT_DIRECTORY : 'directory (you should not see this)'
}

class LocalFileParse( object ):
    
    def __init__( self, path: str ):
        
        self.path = path
        self.result = RESULT_NOT_PARSED
        self.index = 0
        self.mime = HC.APPLICATION_UNKNOWN
        self.size = 0
        
    
    def __eq__( self, other ):
        
        if isinstance( other, LocalFileParse ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self.path.__hash__()
        
    
    def GetPrettyMime( self ):
        
        if self.result == RESULT_GOOD:
            
            return HC.mime_string_lookup[ self.mime ]
            
        else:
            
            return result_str_lookup[ self.result ]
            
        
    
    def IsDir( self ):
        
        return os.path.isdir( self.path )
        
    

class ReviewLocalFileImports( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, paths = None ):
        
        if paths is None:
            
            paths = []
            
        
        super().__init__( parent )
        
        self._result_types_to_count = collections.Counter()
        
        self._unparsed_paths_queue = queue.Queue()
        self._parsed_paths_queue = queue.Queue()
        self._comparable_sidecar_prefixes = set()
        
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        
        self._parse_work_updater = self._InitialiseParseWorkUpdater()
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_INPUT_LOCAL_FILES.ID, self._ConvertPathToDisplayTuple, self._ConvertPathToSortTuple )
        
        self._paths_list = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, 12, model, delete_key_callback = self.RemovePaths )
        
        self._search_subdirectories = QW.QCheckBox( self._paths_list )
        self._search_subdirectories.setText( 'search subdirectories' )
        self._search_subdirectories.setChecked( True )
        
        listctrl_panel.SetListCtrl( self._paths_list )
        
        listctrl_panel.AddButton( 'add files', self.AddPaths )
        listctrl_panel.AddButton( 'add folder', self.AddFolder )
        listctrl_panel.AddWindow( self._search_subdirectories )
        listctrl_panel.AddButton( 'remove files', self.RemovePaths, enabled_only_on_selection = True )
        
        self._progress = ClientGUICommon.TextAndGauge( self )
        
        self._progress_pause = ClientGUICommon.IconButton( self, CC.global_icons().pause, self.PauseProgress )
        self._progress_pause.setEnabled( False )
        
        self._progress_cancel = ClientGUICommon.IconButton( self, CC.global_icons().stop, self.Cancel )
        self._progress_cancel.setEnabled( False )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        show_downloader_options = False
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
        self._delete_after_success_st = ClientGUICommon.BetterStaticText( self )
        self._delete_after_success_st.setAlignment( QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
        self._delete_after_success_st.setObjectName( 'HydrusWarning' )
        
        self._delete_after_success = QW.QCheckBox( 'delete original files after successful import', self )
        self._delete_after_success.clicked.connect( self.EventDeleteAfterSuccessCheck )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'import now', self._DoImport )
        self._add_button.setObjectName( 'HydrusAccept' )
        
        self._tag_button = ClientGUICommon.BetterButton( self, 'add tags/urls with the import >>', self._AddTags )
        self._tag_button.setObjectName( 'HydrusAccept' )
        
        self._tag_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can add specific tags to these files, import from sidecar files, or generate them based on filename. Don\'t be afraid to experiment!' ) )
        
        gauge_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( gauge_sizer, self._progress, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( gauge_sizer, self._progress_pause, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gauge_sizer, self._progress_cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        delete_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( delete_hbox, self._delete_after_success_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( delete_hbox, self._delete_after_success, CC.FLAGS_CENTER_PERPENDICULAR )
        
        import_options_buttons = QP.HBoxLayout()
        
        QP.AddToLayout( import_options_buttons, self._import_options_button, CC.FLAGS_CENTER )
        
        buttons = QP.HBoxLayout()
        
        QP.AddToLayout( buttons, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttons, self._tag_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, delete_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, import_options_buttons, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, buttons, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self.widget().installEventFilter( ClientGUIDragDrop.FileDropTarget( self.widget(), filenames_callable = self._AddPathsToList ) )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        self._DoParseWork()
        
    
    def _AddPathsToList( self, paths ):
        
        if self._cancel_event.is_set():
            
            message = 'Please wait for the cancel to clear.'
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
            self._DoParseWork()
            
            return
            
        
        for path in paths:
            
            local_file_parse = LocalFileParse( path )
            
            # don't do a 'if not path_list.has( path )' here. user appreciates the flicker of feedback to see the dupe checked and discounted
            # subfolders don't fit this test anyway, so we are only talking about clumps of files. no worries about wasted time
            
            self._unparsed_paths_queue.put( local_file_parse )
            
        
        self._DoParseWork()
        
    
    def _AddTags( self ):
        
        # TODO: convert this class to have a filenametaggingoptions and the structure for 'tags for these files', which is separate
        # then make this button not start the import. just edit the options and routers and return
        # if needed, we convert to paths_to_additional_tags on ultimate ok, or we convert the hdd import to just hold service_keys_to_filenametaggingoptions, like an import folder does
        
        good_paths = self._GetGoodPaths()
        
        if len( good_paths ) > 0:
            
            file_import_options = self._import_options_button.GetFileImportOptions()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'filename tagging', frame_key = 'local_import_filename_tagging' ) as dlg:
                
                panel = ClientGUIImport.EditLocalImportFilenameTaggingPanel( dlg, good_paths )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    ( metadata_routers, paths_to_additional_service_keys_to_tags ) = panel.GetValue()
                    
                    delete_after_success = self._delete_after_success.isChecked()
                    
                    CG.client_controller.pub( 'new_hdd_import', good_paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success )
                    
                    self._OKParent()
                    
                
            
        
    
    def _ConvertPathToDisplayTuple( self, local_file_parse: LocalFileParse ):
        
        pretty_index = HydrusNumbers.ToHumanInt( local_file_parse.index )
        
        path = local_file_parse.path
        
        if local_file_parse.result in ( RESULT_MISSING, RESULT_OCCUPIED ):
            
            pretty_size = '-'
            
        else:
            
            pretty_size = HydrusData.ToHumanBytes( local_file_parse.size )
            
        
        pretty_mime = local_file_parse.GetPrettyMime()
        
        display_tuple = ( pretty_index, path, pretty_mime, pretty_size )
        
        return display_tuple
        
    
    def _ConvertPathToSortTuple( self, local_file_parse: LocalFileParse ):
        
        sort_tuple = (
            local_file_parse.index,
            local_file_parse.path,
            ( local_file_parse.result != RESULT_GOOD, local_file_parse.GetPrettyMime() ),
            local_file_parse.size
        )
        
        return sort_tuple
        
    
    def _DoImport( self ):
        
        good_paths = self._GetGoodPaths()
        
        if len( good_paths ) > 0:
            
            file_import_options = self._import_options_button.GetFileImportOptions()
            
            metadata_routers = []
            paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
            
            delete_after_success = self._delete_after_success.isChecked()
            
            CG.client_controller.pub( 'new_hdd_import', good_paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success )
            
        
        self._OKParent()
        
    
    def _DoParseWork( self ):
        
        self._parse_work_updater.update()
        
    
    def _GetGoodPaths( self ):
        
        local_file_parses: list[ LocalFileParse ] = sorted( self._paths_list.GetData(), key = lambda lfp: lfp.index )
        
        good_paths = [ local_file_parse.path for local_file_parse in local_file_parses if local_file_parse.result == RESULT_GOOD ]
        
        return good_paths
        
    
    def _InitialiseParseWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            self._UpdateWidgets()
            
            if self._unparsed_paths_queue.empty():
                
                raise HydrusExceptions.CancelledException()
                
            
            if self._cancel_event.is_set():
                
                self._unparsed_paths_queue = queue.Queue()
                
                self._cancel_event.clear()
                self._pause_event.clear()
                
            
            if self._pause_event.is_set():
                
                raise HydrusExceptions.CancelledException()
                
            
            search_subdirectories = self._search_subdirectories.isChecked()
            
            return ( self._unparsed_paths_queue, self._parsed_paths_queue, search_subdirectories, self._comparable_sidecar_prefixes )
            
        
        def work_callable( args ):
            
            ( unparsed_paths_queue, parsed_paths_queue, search_subdirectories, comparable_sidecar_prefixes ) = args
            
            start_time = HydrusTime.GetNowFloat()
            
            while not unparsed_paths_queue.empty():
                
                try:
                    
                    local_file_parse: LocalFileParse = unparsed_paths_queue.get( block = False )
                    
                except queue.Empty:
                    
                    raise Exception( 'File parse queue was somehow empty!' )
                    
                
                path = local_file_parse.path
                
                # do dir/file here I guess
                
                if local_file_parse.IsDir():
                    
                    ( new_file_paths, sidecar_paths ) = ClientFiles.GetAllFilePaths(
                        path,
                        search_subdirectories = search_subdirectories,
                        comparable_sidecar_prefixes = comparable_sidecar_prefixes
                    )
                    
                    for new_file_path in new_file_paths:
                        
                        new_local_file_parse = LocalFileParse( new_file_path )
                        
                        unparsed_paths_queue.put( new_local_file_parse )
                        
                    
                    for sidecar_path in sidecar_paths:
                        
                        sidecar_local_file_parse = LocalFileParse( sidecar_path )
                        
                        sidecar_local_file_parse.result = RESULT_SIDECAR
                        
                        try:
                            
                            sidecar_local_file_parse.size = os.path.getsize( sidecar_path )
                            
                        except:
                            
                            sidecar_local_file_parse.size = 0
                            
                        
                        parsed_paths_queue.put( sidecar_local_file_parse )
                        
                    
                    local_file_parse.result = RESULT_DIRECTORY
                    
                else:
                    
                    if not os.path.exists( path ):
                        
                        HydrusData.Print( 'Missing file: ' + path )
                        
                        local_file_parse.result = RESULT_MISSING
                        
                    elif not HydrusPaths.PathIsFree( path ):
                        
                        HydrusData.Print( 'File currently in use: ' + path )
                        
                        local_file_parse.result = RESULT_OCCUPIED
                        
                    else:
                        
                        try:
                            
                            size = os.path.getsize( path )
                            
                        except:
                            
                            size = 0
                            
                        
                        local_file_parse.size = size
                        
                        if size == 0:
                            
                            HydrusData.Print( 'Empty file: ' + path )
                            
                            local_file_parse.result = RESULT_EMPTY
                            
                        elif path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                            
                            HydrusData.Print( 'In import parse, skipping Thumbs.db: ' + path )
                            
                            local_file_parse.result = RESULT_UNIMPORTABLE
                            
                        else:
                            
                            # looks good, let's burn some CPU
                            
                            try:
                                
                                mime = HydrusFileHandling.GetMime( path )
                                
                            except Exception as e:
                                
                                HydrusData.Print( 'Problem parsing mime for: ' + path )
                                HydrusData.PrintException( e )
                                
                                mime = HC.APPLICATION_UNKNOWN
                                
                            
                            local_file_parse.mime = mime
                            
                            if mime in HC.ALLOWED_MIMES:
                                
                                local_file_parse.result = RESULT_GOOD
                                
                            else:
                                
                                HydrusData.Print( 'During file import scan, unparsable file: ' + path )
                                
                                local_file_parse.result = RESULT_UNIMPORTABLE
                                
                            
                        
                    
                
                parsed_paths_queue.put( local_file_parse )
                
                if HydrusTime.TimeHasPassedFloat( start_time + 0.1 ):
                    
                    break
                    
                
            
            # get the paths/queue and work them
            # return parsedresults. do we have classes here yet? mite b nice to do so!
            # would be cool to list failures in the list too! could put some note info in the mime spot or something
            # might want an extra column for this but whatever. maybe rename the mime one to 'result'
            
            return 1
            
        
        def publish_callable( result ):
            
            stuff_to_add = []
            next_index = self._paths_list.count() + 1
            
            while not self._parsed_paths_queue.empty():
                
                try:
                    
                    local_file_parse: LocalFileParse = self._parsed_paths_queue.get( block = False )
                    
                except queue.Empty:
                    
                    raise Exception( 'File parse queue was somehow empty!' )
                    
                
                if local_file_parse.result != RESULT_DIRECTORY:
                    
                    if not self._paths_list.HasData( local_file_parse ) and local_file_parse not in stuff_to_add:
                        
                        local_file_parse.index = next_index
                        
                        next_index += 1
                        
                        self._result_types_to_count[ local_file_parse.result ] += 1
                        
                        stuff_to_add.append( local_file_parse )
                        
                    
                
            
            if len( stuff_to_add ) > 0:
                
                self._paths_list.AddDatas( stuff_to_add )
                
            
            if self._unparsed_paths_queue.empty():
                
                self._paths_list.Sort()
                
            
            self._DoParseWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'local file imports parser', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _UpdateWidgets( self ):
        
        # this guy is tricky to keep updated, so we'll just bruteforce it here mate
        self._result_types_to_count[ RESULT_NOT_PARSED ] = self._unparsed_paths_queue.qsize()
        
        good_files_in_list = self._result_types_to_count[ RESULT_GOOD ] > 0
        
        no_work_in_queue = self._result_types_to_count[ RESULT_NOT_PARSED ] == 0
        paused = self._pause_event.is_set()
        
        can_import = good_files_in_list and ( no_work_in_queue or paused )
        
        if no_work_in_queue:
            
            self._progress_pause.setEnabled( False )
            self._progress_cancel.setEnabled( False )
            
        else:
            
            self._progress_pause.setEnabled( True )
            self._progress_cancel.setEnabled( True )
            
        
        if can_import:
            
            self._add_button.setEnabled( True )
            self._tag_button.setEnabled( True )
            
        else:
            
            self._add_button.setEnabled( False )
            self._tag_button.setEnabled( False )
            
        
        if paused:
            
            self._progress_pause.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._progress_pause.SetIconSmart( CC.global_icons().pause )
            
        
        #
        
        num_total_paths = sum( self._result_types_to_count.values() )
        num_unparsed_paths = self._result_types_to_count[ RESULT_NOT_PARSED ]
        num_files_done = num_total_paths - num_unparsed_paths
        num_good_files = self._result_types_to_count[ RESULT_GOOD ]
        
        num_empty_files = self._result_types_to_count[ RESULT_EMPTY ]
        num_unimportable = self._result_types_to_count[ RESULT_UNIMPORTABLE ]
        num_occupied = self._result_types_to_count[ RESULT_OCCUPIED ]
        num_missing = self._result_types_to_count[ RESULT_MISSING ]
        
        num_bad_files = num_empty_files + num_unimportable + num_occupied + num_missing
        
        num_sidecars = self._result_types_to_count[ RESULT_SIDECAR ]
        
        if num_total_paths == 0:
            
            message = 'waiting for paths to parse'
            
        elif num_files_done < num_total_paths:
            
            message = f'{HydrusNumbers.ValueRangeToPrettyString( num_files_done, num_total_paths )} files parsed'
            
        else:
            
            message = f'{HydrusNumbers.ToHumanInt( num_total_paths )} files parsed'
            
        
        if num_bad_files > 0:
            
            message += ' - '
            
            if num_good_files > 0:
                
                message += f'{HydrusNumbers.ToHumanInt( num_good_files )} good | {HydrusNumbers.ToHumanInt( num_bad_files )} bad'
                
            elif num_bad_files == num_files_done:
                
                message += 'all bad'
                
            
            message += ': '
            
            bad_comments = []
            
            if num_empty_files > 0:
                
                bad_comments.append( HydrusNumbers.ToHumanInt( num_empty_files ) + ' were empty' )
                
            
            if num_missing > 0:
                
                bad_comments.append( HydrusNumbers.ToHumanInt( num_missing ) + ' were missing' )
                
            
            if num_unimportable > 0:
                
                bad_comments.append( HydrusNumbers.ToHumanInt( num_unimportable ) + ' had unsupported file types' )
                
            
            if num_occupied > 0:
                
                bad_comments.append( HydrusNumbers.ToHumanInt( num_occupied ) + ' were inaccessible (maybe in use by another process)' )
                
            
            message += ', '.join( bad_comments )
            
        
        if num_sidecars > 0:
            
            message += f' - and looks like {HydrusNumbers.ToHumanInt( num_sidecars )} txt/json/xml sidecars'
            
        
        message += '.'
        
        self._progress.SetValue( message, num_files_done, num_total_paths )
        
    
    def AddFolder( self ):
        
        with ClientGUIDialogsFiles.DirDialog( self, 'Select a folder to add.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = dlg.GetPath()
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def AddPaths( self ):
        
        with ClientGUIDialogsFiles.FileDialog( self, 'Select the files to add.', fileMode = QW.QFileDialog.FileMode.ExistingFiles ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._AddPathsToList( paths )
                
            
        
    
    def Cancel( self ):
        
        self._cancel_event.set()
        
        self._DoParseWork()
        
    
    def EventDeleteAfterSuccessCheck( self ):
        
        if self._delete_after_success.isChecked():
            
            self._delete_after_success_st.setText( 'YOUR ORIGINAL FILES WILL BE DELETED' )
            
        else:
            
            self._delete_after_success_st.clear()
            
        
    
    def PauseProgress( self ):
        
        if self._pause_event.is_set():
            
            self._pause_event.clear()
            
        else:
            
            self._pause_event.set()
            
        
        self._DoParseWork()
        
    
    def RemovePaths( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._paths_list.DeleteSelected()
            
            # re-do the indices
            
            local_file_parses = self._paths_list.GetData()
            
            self._result_types_to_count = collections.Counter()
            
            flat_local_file_parses_sorted = sorted( local_file_parses, key = lambda pr: pr.index )
            
            new_index = 1
            
            for local_file_parse in flat_local_file_parses_sorted:
                
                self._result_types_to_count[ local_file_parse.result ] += 1
                
                local_file_parse.index = new_index
                
                new_index += 1
                
            
            self._paths_list.UpdateDatas()
            
            self._DoParseWork()
            
        
    
