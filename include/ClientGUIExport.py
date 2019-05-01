from . import ClientConstants as CC
from . import ClientExporting
from . import ClientGUIACDropdown
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientSearch
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusPaths
import os
import stat
import time
import traceback
import wx

class EditExportFoldersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folders ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._export_folders_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', 20 ), ( 'path', -1 ), ( 'type', 12 ), ( 'query', 16 ), ( 'paused', 8 ), ( 'period', 16 ), ( 'phrase', 20 ) ]
        
        self._export_folders = ClientGUIListCtrl.BetterListCtrl( self._export_folders_panel, 'export_folders', 6, 40, columns, self._ConvertExportFolderToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        self._export_folders_panel.SetListCtrl( self._export_folders )
        
        self._export_folders_panel.AddButton( 'add', self._AddFolder )
        self._export_folders_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._export_folders_panel.AddDeleteButton()
        
        #
        
        self._export_folders.AddDatas( export_folders )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = 'Here you can set the client to regularly export a certain query to a particular location.'
        
        vbox.Add( ClientGUICommon.BetterStaticText( self, intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._export_folders_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _AddFolder( self ):
        
        new_options = HG.client_controller.new_options
        
        phrase = new_options.GetString( 'export_phrase' )
        
        name = 'export folder'
        path = ''
        export_type = HC.EXPORT_FOLDER_TYPE_REGULAR
        delete_from_client_after_export = False
        file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
        period = 15 * 60
        
        export_folder = ClientExporting.ExportFolder( name, path, export_type = export_type, delete_from_client_after_export = delete_from_client_after_export, file_search_context = file_search_context, period = period, phrase = phrase )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit export folder' ) as dlg:
            
            panel = EditExportFolderPanel( dlg, export_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                export_folder = panel.GetValue()
                
                export_folder.SetNonDupeName( self._GetExistingNames() )
                
                self._export_folders.AddDatas( ( export_folder, ) )
                
            
        
    
    def _ConvertExportFolderToListCtrlTuples( self, export_folder ):
        
        ( name, path, export_type, delete_from_client_after_export, file_search_context, run_regularly, period, phrase, last_checked, paused, run_now ) = export_folder.ToTuple()
        
        if export_type == HC.EXPORT_FOLDER_TYPE_REGULAR:
            
            pretty_export_type = 'regular'
            
        elif export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            pretty_export_type = 'synchronise'
            
        
        if delete_from_client_after_export:
            
            pretty_export_type += ' and deleting from the client!'
            
        
        pretty_file_search_context = ', '.join( predicate.ToString( with_count = False ) for predicate in file_search_context.GetPredicates() )
        
        if run_regularly:
            
            pretty_period = HydrusData.TimeDeltaToPrettyTimeDelta( period )
            
        else:
            
            pretty_period = 'not running regularly'
            
        
        if run_now:
            
            pretty_period += ' (running after dialog ok)'
            
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        pretty_phrase = phrase
        
        display_tuple = ( name, path, pretty_export_type, pretty_file_search_context, pretty_paused, pretty_period, pretty_phrase )
        
        sort_tuple = ( name, path, pretty_export_type, pretty_file_search_context, paused, period, phrase )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        export_folders = self._export_folders.GetData( only_selected = True )
        
        for export_folder in export_folders:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit export folder' ) as dlg:
                
                panel = EditExportFolderPanel( dlg, export_folder )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_export_folder = panel.GetValue()
                    
                    self._export_folders.DeleteDatas( ( export_folder, ) )
                    
                    edited_export_folder.SetNonDupeName( self._GetExistingNames() )
                    
                    self._export_folders.AddDatas( ( edited_export_folder, ) )
                    
                else:
                    
                    return
                    
                
            
        
    
    def _GetExistingNames( self ):
        
        existing_names = { export_folder.GetName() for export_folder in self._export_folders.GetData() }
        
        return existing_names
        
    
    def GetValue( self ):
        
        export_folders = self._export_folders.GetData()
        
        return export_folders
        
    
class EditExportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folder ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._export_folder = export_folder
        
        ( name, path, export_type, delete_from_client_after_export, file_search_context, run_regularly, period, phrase, self._last_checked, paused, run_now ) = self._export_folder.ToTuple()
        
        self._path_box = ClientGUICommon.StaticBox( self, 'name and location' )
        
        self._name = wx.TextCtrl( self._path_box )
        
        self._path = wx.DirPickerCtrl( self._path_box, style = wx.DIRP_USE_TEXTCTRL )
        
        #
        
        self._type_box = ClientGUICommon.StaticBox( self, 'type of export' )
        
        self._type = ClientGUICommon.BetterChoice( self._type_box )
        self._type.Append( 'regular', HC.EXPORT_FOLDER_TYPE_REGULAR )
        self._type.Append( 'synchronise', HC.EXPORT_FOLDER_TYPE_SYNCHRONISE )
        
        self._delete_from_client_after_export = wx.CheckBox( self._type_box )
        
        #
        
        self._query_box = ClientGUICommon.StaticBox( self, 'query to export' )
        
        self._page_key = 'export folders placeholder'
        
        predicates = file_search_context.GetPredicates()
        
        self._predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._query_box, self._page_key, predicates )
        
        self._searchbox = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._query_box, self._page_key, file_search_context, allow_all_known_files = False )
        
        #
        
        self._period_box = ClientGUICommon.StaticBox( self, 'export period' )
        
        self._period = ClientGUITime.TimeDeltaButton( self._period_box, min = 3 * 60, days = True, hours = True, minutes = True )
        
        self._run_regularly = wx.CheckBox( self._period_box )
        
        self._paused = wx.CheckBox( self._period_box )
        
        self._run_now = wx.CheckBox( self._period_box )
        
        #
        
        self._phrase_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = wx.TextCtrl( self._phrase_box )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._phrase_box )
        
        #
        
        self._name.SetValue( name )
        
        self._path.SetPath( path )
        
        self._type.SelectClientData( export_type )
        
        self._delete_from_client_after_export.SetValue( delete_from_client_after_export )
        
        self._period.SetValue( period )
        
        self._run_regularly.SetValue( run_regularly )
        
        self._paused.SetValue( paused )
        
        self._run_now.SetValue( run_now )
        
        self._pattern.SetValue( phrase )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'folder path: ', self._path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._path_box, rows )
        
        self._path_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        text = '''regular - try to export the files to the directory, overwriting if the filesize if different

synchronise - try to export the files to the directory, overwriting if the filesize if different, and delete anything else in the directory

If you select synchronise, be careful!'''
        
        st = ClientGUICommon.BetterStaticText( self._type_box, label = text )
        
        st.SetWrapWidth( 440 )
        
        self._type_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._type_box.Add( self._type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'delete files from client after export: ', self._delete_from_client_after_export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._type_box, rows )
        
        self._type_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._query_box.Add( self._predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._query_box.Add( self._searchbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._period_box.Add( self._period, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'run regularly?: ', self._run_regularly ) )
        rows.append( ( 'paused: ', self._paused ) )
        rows.append( ( 'run on dialog ok: ', self._run_now ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._period_box, rows )
        
        self._period_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        phrase_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        phrase_hbox.Add( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        phrase_hbox.Add( self._examples, CC.FLAGS_VCENTER )
        
        self._phrase_box.Add( phrase_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._type_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._query_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._period_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._phrase_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self._UpdateTypeDeleteUI()
        
        self._type.Bind( wx.EVT_CHOICE, self.EventTypeChoice )
        self._delete_from_client_after_export.Bind( wx.EVT_CHECKBOX, self.EventDeleteFilesAfterExport )
        
    
    def _UpdateTypeDeleteUI( self ):
        
        if self._type.GetChoice() == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            self._delete_from_client_after_export.Disable()
            
            if self._delete_from_client_after_export.GetValue():
                
                self._delete_from_client_after_export.SetValue( False )
                
            
        else:
            
            self._delete_from_client_after_export.Enable()
            
        
    
    def CanOK( self ):
        
        if self._delete_from_client_after_export.GetValue():
            
            message = 'You have set this export folder to delete the files from the client after export! Are you absolutely sure this is what you want?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return False
                    
                
            
        
        return True
        
    
    def EventDeleteFilesAfterExport( self, event ):
        
        if self._delete_from_client_after_export.GetValue():
            
            wx.MessageBox( 'This will delete the exported files from your client after the export! If you do not know what this means, uncheck it!' )
            
        
    
    def EventTypeChoice( self, event ):
        
        self._UpdateTypeDeleteUI()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        path = self._path.GetPath()
        
        export_type = self._type.GetChoice()
        
        delete_from_client_after_export = self._delete_from_client_after_export.GetValue()
        
        file_search_context = self._searchbox.GetFileSearchContext()
        
        predicates = self._predicates_box.GetPredicates()
        
        file_search_context.SetPredicates( predicates )
        
        run_regularly = self._run_regularly.GetValue()
        
        period = self._period.GetValue()
        
        phrase = self._pattern.GetValue()
        
        if self._path.GetPath() in ( '', None ):
            
            raise HydrusExceptions.VetoException( 'You must enter a folder path to export to!' )
            
        
        phrase = self._pattern.GetValue()
        
        try:
            
            ClientExporting.ParseExportPhrase( phrase )
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( 'Could not parse that export phrase! ' + str( e ) )
            
        
        run_now = self._run_now.GetValue()
        
        paused = self._paused.GetValue()
        
        export_folder = ClientExporting.ExportFolder( name, path = path, export_type = export_type, delete_from_client_after_export = delete_from_client_after_export, file_search_context = file_search_context, run_regularly = run_regularly, period = period, phrase = phrase, last_checked = self._last_checked, paused = paused, run_now = run_now )
        
        return export_folder
        
    
class ReviewExportFilesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, flat_media, do_export_and_then_quit = False ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        new_options = HG.client_controller.new_options
        
        self._media_to_paths = {}
        self._existing_filenames = set()
        self._last_phrase_used = ''
        self._last_dir_used = ''
        
        self._tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'files\' tags' )
        
        services_manager = HG.client_controller.services_manager
        
        self._neighbouring_txt_tag_service_keys = services_manager.FilterValidServiceKeys( new_options.GetKeyList( 'default_neighbouring_txt_tag_service_keys' ) )
        
        t = ClientGUIListBoxes.ListBoxTagsSelection( self._tags_box, include_counts = True, collapse_siblings = True )
        
        self._tags_box.SetTagsBox( t )
        
        self._tags_box.SetMinSize( ( 220, 300 ) )
        
        columns = [ ( 'number', 8 ), ( 'mime', 20 ), ( 'expected path', -1 ) ]
        
        self._paths = ClientGUIListCtrl.BetterListCtrl( self, 'export_files', 24, 64, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True )
        
        self._paths.Sort( 0 )
        
        self._export_path_box = ClientGUICommon.StaticBox( self, 'export path' )
        
        self._directory_picker = wx.DirPickerCtrl( self._export_path_box )
        self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventRecalcPaths )
        
        self._open_location = wx.Button( self._export_path_box, label = 'open this location' )
        self._open_location.Bind( wx.EVT_BUTTON, self.EventOpenLocation )
        
        self._filenames_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = wx.TextCtrl( self._filenames_box )
        
        self._update = wx.Button( self._filenames_box, label = 'update' )
        self._update.Bind( wx.EVT_BUTTON, self.EventRecalcPaths )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._filenames_box )
        
        self._delete_files_after_export = wx.CheckBox( self, label = 'delete files from client after export?' )
        self._delete_files_after_export.SetForegroundColour( wx.Colour( 127, 0, 0 ) )
        
        self._export_symlinks = wx.CheckBox( self, label = 'EXPERIMENTAL: export symlinks' )
        self._export_symlinks.SetForegroundColour( wx.Colour( 127, 0, 0 ) )
        
        text = 'This will export all the files\' tags, newline separated, into .txts beside the files themselves.'
        
        self._export_tag_txts = wx.CheckBox( self, label = 'export tags to .txt files?' )
        self._export_tag_txts.SetToolTip( text )
        self._export_tag_txts.Bind( wx.EVT_CHECKBOX, self.EventExportTagTxtsChanged )
        
        self._export = wx.Button( self, label = 'export' )
        self._export.Bind( wx.EVT_BUTTON, self.EventExport )
        
        #
        
        export_path = ClientExporting.GetExportPath()
        
        self._directory_picker.SetPath( export_path )
        
        phrase = new_options.GetString( 'export_phrase' )
        
        self._pattern.SetValue( phrase )
        
        if len( self._neighbouring_txt_tag_service_keys ) > 0:
            
            self._export_tag_txts.SetValue( True )
            
        
        self._paths.SetData( list( enumerate( flat_media ) ) )
        
        self._delete_files_after_export.SetValue( HG.client_controller.new_options.GetBoolean( 'delete_files_after_export' ) )
        self._delete_files_after_export.Bind( wx.EVT_CHECKBOX, self.EventDeleteFilesChanged )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._export_symlinks.Hide()
            
        
        #
        
        top_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        top_hbox.Add( self._tags_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        top_hbox.Add( self._paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._directory_picker, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._open_location, CC.FLAGS_VCENTER )
        
        self._export_path_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._update, CC.FLAGS_VCENTER )
        hbox.Add( self._examples, CC.FLAGS_VCENTER )
        
        self._filenames_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.Add( self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._delete_files_after_export, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._export_symlinks, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._export_tag_txts, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._export, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        self._RefreshTags()
        
        wx.CallAfter( self._export.SetFocus )
        
        self._paths.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectPath )
        self._paths.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectPath )
        
        if do_export_and_then_quit:
            
            wx.CallAfter( self._DoExport, True )
            
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        directory = self._directory_picker.GetPath()
        
        ( ordering_index, media ) = data
        
        number = ordering_index
        mime = media.GetMime()
        
        try:
            
            path = self._GetPath( media )
            
        except Exception as e:
            
            path = str( e )
            
        
        pretty_number = HydrusData.ToHumanInt( ordering_index + 1 )
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        pretty_path = path
        
        if not path.startswith( directory ):
            
            pretty_path = 'INVALID, above destination directory: ' + path
            
        
        display_tuple = ( pretty_number, pretty_mime, pretty_path )
        sort_tuple = ( number, pretty_mime, path )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DoExport( self, quit_afterwards = False ):
        
        delete_afterwards = self._delete_files_after_export.GetValue()
        export_symlinks = self._export_symlinks.GetValue() and not delete_afterwards
        
        if quit_afterwards:
            
            message = 'Export as shown?'
            
            if delete_afterwards:
                
                message += os.linesep * 2
                message += 'THE FILES WILL BE DELETED FROM THE CLIENT AFTERWARDS'
                
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    self.GetParent().Close()
                    
                    return
                    
                
            
        elif delete_afterwards:
            
            message = 'THE FILES WILL BE DELETED FROM THE CLIENT AFTERWARDS'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
        
        self._RefreshPaths()
        
        export_tag_txts = self._export_tag_txts.GetValue()
        
        directory = self._directory_picker.GetPath()
        
        HydrusPaths.MakeSureDirectoryExists( directory )
        
        pattern = self._pattern.GetValue()
        
        new_options = HG.client_controller.new_options
        
        new_options.SetKeyList( 'default_neighbouring_txt_tag_service_keys', self._neighbouring_txt_tag_service_keys )
        
        new_options.SetString( 'export_phrase', pattern )
        
        try:
            
            terms = ClientExporting.ParseExportPhrase( pattern )
            
        except Exception as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._export.Disable()
        
        to_do = self._paths.GetData()
        
        num_to_do = len( to_do )
        
        def wx_update_label( text ):
            
            if not self or not self._export:
                
                return
                
            
            self._export.SetLabel( text )
            
        
        def wx_done( quit_afterwards ):
            
            if not self or not self._export:
                
                return
                
            
            self._export.Enable()
            
            if quit_afterwards:
                
                wx.CallAfter( self.GetParent().Close )
                
            
        
        def do_it( directory, neighbouring_txt_tag_service_keys, delete_afterwards, export_symlinks, quit_afterwards ):
            
            pauser = HydrusData.BigJobPauser()
            
            for ( index, ( ordering_index, media ) ) in enumerate( to_do ):
                
                try:
                    
                    wx.CallAfter( wx_update_label, HydrusData.ConvertValueRangeToPrettyString( index + 1, num_to_do ) )
                    
                    hash = media.GetHash()
                    mime = media.GetMime()
                    
                    path = self._GetPath( media )
                    
                    path = os.path.normpath( path )
                    
                    if not path.startswith( directory ):
                        
                        raise Exception( 'It seems a destination path was above the main export directory! The file was "{}" and its destination path was "{}".'.format( hash.hex(), path ) )
                        
                    
                    path_dir = os.path.dirname( path )
                    
                    HydrusPaths.MakeSureDirectoryExists( path_dir )
                    
                    if export_tag_txts:
                        
                        tags_manager = media.GetTagsManager()
                        
                        tags = set()
                        
                        siblings_manager = HG.controller.tag_siblings_manager
                        
                        tag_censorship_manager = HG.client_controller.tag_censorship_manager
                        
                        for service_key in neighbouring_txt_tag_service_keys:
                            
                            current_tags = tags_manager.GetCurrent( service_key )
                            
                            current_tags = siblings_manager.CollapseTags( service_key, current_tags )
                            
                            current_tags = tag_censorship_manager.FilterTags( service_key, current_tags )
                            
                            tags.update( current_tags )
                            
                        
                        tags = list( tags )
                        
                        tags.sort()
                        
                        txt_path = path + '.txt'
                        
                        with open( txt_path, 'w', encoding = 'utf-8' ) as f:
                            
                            f.write( os.linesep.join( tags ) )
                            
                        
                    
                    source_path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
                    
                    if export_symlinks:
                        
                        os.symlink( source_path, path )
                        
                    else:
                        
                        HydrusPaths.MirrorFile( source_path, path )
                        
                        HydrusPaths.MakeFileWritable( path )
                        
                    
                except:
                    
                    wx.CallAfter( wx.MessageBox, 'Encountered a problem while attempting to export file with index ' + str( ordering_index + 1 ) + ':' + os.linesep * 2 + traceback.format_exc() )
                    
                    break
                    
                
                pauser.Pause()
                
            
            if delete_afterwards:
                
                wx.CallAfter( wx_update_label, 'deleting' )
                
                deletee_hashes = { media.GetHash() for ( ordering_index, media ) in to_do }
                
                chunks_of_hashes = HydrusData.SplitListIntoChunks( deletee_hashes, 64 )
                
                reason = 'Deleted after manual export to "{}".'.format( directory )
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) for chunk_of_hashes in chunks_of_hashes ]
                
                for content_update in content_updates:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
                    
                
            
            wx.CallAfter( wx_update_label, 'done!' )
            
            time.sleep( 1 )
            
            wx.CallAfter( wx_update_label, 'export' )
            
            wx.CallAfter( wx_done, quit_afterwards )
            
        
        HG.client_controller.CallToThread( do_it, directory, self._neighbouring_txt_tag_service_keys, delete_afterwards, export_symlinks, quit_afterwards )
        
    
    def _GetPath( self, media ):
        
        if media in self._media_to_paths:
            
            return self._media_to_paths[ media ]
            
        
        directory = self._directory_picker.GetPath()
        
        pattern = self._pattern.GetValue()
        
        terms = ClientExporting.ParseExportPhrase( pattern )
        
        filename = ClientExporting.GenerateExportFilename( directory, media, terms )
        
        i = 1
        
        while filename in self._existing_filenames:
            
            filename = ClientExporting.GenerateExportFilename( directory, media, terms + [ ( 'string', ' (' + str( i ) + ')' ) ] )
            
            i += 1
            
        
        path = os.path.join( directory, filename )
        
        path = os.path.normpath( path )
        
        self._existing_filenames.add( filename )
        self._media_to_paths[ media ] = path
        
        return path
        
    
    def _RefreshPaths( self ):
        
        pattern = self._pattern.GetValue()
        dir_path = self._directory_picker.GetPath()
        
        if pattern == self._last_phrase_used and dir_path == self._last_dir_used:
            
            return
            
        
        self._last_phrase_used = pattern
        self._last_dir_used = dir_path
        
        HG.client_controller.new_options.SetString( 'export_phrase', pattern )
        
        self._existing_filenames = set()
        self._media_to_paths = {}
        
        self._paths.UpdateDatas()
        
    
    def _RefreshTags( self ):
        
        data = self._paths.GetData( only_selected = True )
        
        if len( data ) == 0:
            
            data = self._paths.GetData()
            
        
        all_media = [ media for ( ordering_index, media ) in data ]
        
        self._tags_box.SetTagsByMedia( all_media )
        
    
    def EventExport( self, event ):
        
        self._DoExport()
        
    
    def EventDeleteFilesChanged( self, event ):
        
        value = self._delete_files_after_export.GetValue()
        
        HG.client_controller.new_options.SetBoolean( 'delete_files_after_export', value )
        
        if value:
            
            self._export_symlinks.SetValue( False )
            
        
    
    def EventExportTagTxtsChanged( self, event ):
        
        if self._export_tag_txts.GetValue() == True:
            
            services_manager = HG.client_controller.services_manager
            
            tag_services = services_manager.GetServices( HC.TAG_SERVICES )
            
            choice_tuples = [ ( service.GetName(), service.GetServiceKey(), service.GetServiceKey() in self._neighbouring_txt_tag_service_keys ) for service in tag_services ]
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'select tag services' ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    self._neighbouring_txt_tag_service_keys = panel.GetValue()
                    
                    if len( self._neighbouring_txt_tag_service_keys ) == 0:
                        
                        self._export_tag_txts.SetValue( False )
                        
                    else:
                        
                        self._export_tag_txts.SetValue( True )
                        
                    
                else:
                    
                    self._export_tag_txts.SetValue( False )
                    
                
            
        else:
            
            self._neighbouring_txt_tag_service_keys = []
            
        
    
    def EventOpenLocation( self, event ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            HydrusPaths.LaunchDirectory( directory )
            
        
    
    def EventRecalcPaths( self, event ):
        
        self._RefreshPaths()
        
    
    def EventSelectPath( self, event ):
        
        self._RefreshTags()
        
        
    
