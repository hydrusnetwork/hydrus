from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIOptionsPanels
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUITagFilter
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing.options import ExternalProgramsImportOptions
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import ImportOptionsConstants as IOC
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagFilteringImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.metadata import ClientTags

class EditExternalProgramsImportOptionsSingleEntryPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, external_programs_import_options_single_entry: ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry, possible_ids_and_names: list[ HydrusSerialisable.IdAndName ] ):
        
        super().__init__( parent )
        
        self._id_and_name = ClientGUICommon.BetterChoice( self )
        
        for possible_id_and_name in possible_ids_and_names:
            
            self._id_and_name.addItem( possible_id_and_name.name, possible_id_and_name )
            
        
        self._when_to_do_it = ClientGUICommon.BetterChoice( self )
        
        self._when_to_do_it.addItem( 'all file imports', ( True, True ) )
        self._when_to_do_it.addItem( 'all new file imports', ( True, False ) )
        self._when_to_do_it.addItem( 'all "already in db" imports', ( False, True ) )
        self._when_to_do_it.addItem( 'no imports (will do nothing!)', ( False, False ) )
        
        self._id_and_name.SetValue( external_programs_import_options_single_entry.GetIdAndName() )
        self._when_to_do_it.SetValue( ( external_programs_import_options_single_entry.DoItOnNew(), external_programs_import_options_single_entry.DoItOnAlreadyIn() ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._id_and_name, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( hbox, self._when_to_do_it, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( hbox )
        
    
    def GetValue( self ) -> ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry:
        
        id_and_name = self._id_and_name.GetValue()
        ( do_it_on_new, do_it_on_already_in ) = self._when_to_do_it.GetValue()
        
        entry = ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry()
        
        entry.SetIdAndName( id_and_name )
        entry.SetDoItOnNew( do_it_on_new )
        entry.SetDoItOnAlreadyIn( do_it_on_already_in )
        
        return entry
        
    

class EditExternalProgramsImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, external_programs_import_options: ExternalProgramsImportOptions.ExternalProgramsImportOptions ):
        
        super().__init__( parent )
        
        #
        
        self._entries = ClientGUIListBoxes.AddEditDeleteListBox( self, 6, self._EntryToStringForList, self._AddEntry, self._EditEntry )
        
        #
        
        self.SetValue( external_programs_import_options )
        
        #
        
        vbox = QP.VBoxLayout()
        
        #
        
        QP.AddToLayout( vbox, self._entries, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._entries.listBoxChanged.connect( self.valueChanged )
        
    
    def _AddEntry( self ):
        
        entry = ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry()
        
        from hydrus.client.executables import ClientExecutablePipelines
        
        possible_ids_and_names = CG.client_controller.executable_manager.GetIdsAndNamesOfType( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE )
        
        if len( possible_ids_and_names ) > 0:
            
            entry.SetIdAndName( possible_ids_and_names[ 0 ] )
            
        
        return self._EditEntry( entry )
        
    
    def _EditEntry( self, entry: ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry ):
        
        from hydrus.client.executables import ClientExecutablePipelines
        
        possible_ids_and_names = CG.client_controller.executable_manager.GetIdsAndNamesOfType( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE )
        
        if len( possible_ids_and_names ) == 0:
            
            message = f'Hey, there do not seem to be any "{ClientExecutablePipelines.executable_pipeline_types_to_strs[ ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE ]}" external program calls set! If you are in the options dialog and only just added some, please apply and re-open.'
            
            ClientGUIDialogsMessage.ShowCritical( self, 'No external calls!', message )
            
            raise HydrusExceptions.CancelledException( 'No calls to make!' )
            
        
        if entry.GetIdAndName() not in possible_ids_and_names:
            
            message = 'Hey, just so you know, I do not see the entry\'s external call in the currently list of available calls. If you are fixing that now, great.'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'Edit external program call' ) as dlg:
            
            panel = EditExternalProgramsImportOptionsSingleEntryPanel( dlg, entry, possible_ids_and_names )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_entry = panel.GetValue()
                
                return edited_entry
                
            else:
                
                raise HydrusExceptions.CancelledException( 'User cancelled out!' )
                
            
        
    
    def _EntryToStringForList( self, entry: ExternalProgramsImportOptions.ExternalProgramsImportOptionsSingleEntry ) -> str:
        
        return entry.GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL )
        
    
    def GetValue( self ) -> ExternalProgramsImportOptions.ExternalProgramsImportOptions:
        
        entries = self._entries.GetData()
        
        external_program_import_options = ExternalProgramsImportOptions.ExternalProgramsImportOptions()
        
        external_program_import_options.SetEntries( entries )
        
        return external_program_import_options
        
    
    def SetValue( self, external_program_import_options: ExternalProgramsImportOptions.ExternalProgramsImportOptions ):
        
        self._entries.Clear()
        
        self._entries.AddDatas( external_program_import_options.GetEntries() )
        
    

class EditFileFilteringImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, file_filtering_import_options: FileFilteringImportOptions.FileFilteringImportOptions ):
        
        super().__init__( parent )
        
        #
        
        filetype_selector_panel = ClientGUICommon.StaticBox( self, 'allowed filetypes' )
        
        self._exclude_deleted = QW.QCheckBox( self )
        
        tt = 'By default, the client will not try to reimport files that it knows were deleted before. This is a good setting and should be left on in general.'
        tt += '\n' * 2
        tt += 'However, you might like to turn it off for a one-time job where you want to force an import of previously deleted files.'
        
        self._exclude_deleted.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimesTree( filetype_selector_panel, HC.ALLOWED_MIMES )
        
        #
        
        self._allow_decompression_bombs = QW.QCheckBox( self )
        
        tt = 'This is an old setting, it basically just rejects all jpegs and pngs with more than a 1GB bitmap, or about 250-350 Megapixels. In can be useful if you have an older computer that will die at a 16,000x22,000 png.'
        
        self._allow_decompression_bombs.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._min_size = ClientGUIBytes.NoneableBytesControl( self, 5 * 1024 )
        
        self._max_size = ClientGUIBytes.NoneableBytesControl( self, 100 * 1024 * 1024 )
        
        self._max_gif_size = ClientGUIBytes.NoneableBytesControl( self, 32 * 1024 * 1024 )
        
        tt = 'This catches most of those gif conversions of webms. These files are low quality but huge and mostly a waste of storage and bandwidth.'
        
        self._max_gif_size.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._min_resolution = ClientGUICommon.NoneableDoubleSpinCtrl( self, ( 50, 50 ) )
        
        self._max_resolution = ClientGUICommon.NoneableDoubleSpinCtrl( self, ( 8192, 8192 ) )
        
        tt = 'If either width or height is violated, the file will fail this test and be ignored. It does not have to be both.'
        
        self._min_resolution.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        self._max_resolution.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self.SetValue( file_filtering_import_options )
        
        #
        
        filetype_selector_panel.Add( self._mimes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, filetype_selector_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'exclude previously deleted files: ', self._exclude_deleted ) )
        rows.append( ( 'allow decompression bombs: ', self._allow_decompression_bombs ) )
        rows.append( ( 'minimum filesize: ', self._min_size ) )
        rows.append( ( 'maximum filesize: ', self._max_size ) )
        rows.append( ( 'maximum gif filesize: ', self._max_gif_size ) )
        rows.append( ( 'minimum resolution: ', self._min_resolution ) )
        rows.append( ( 'maximum resolution: ', self._max_resolution ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._mimes.valueChanged.connect( self.valueChanged )
        self._exclude_deleted.clicked.connect( self.valueChanged )
        self._allow_decompression_bombs.clicked.connect( self.valueChanged )
        self._min_size.valueChanged.connect( self.valueChanged )
        self._max_size.valueChanged.connect( self.valueChanged )
        self._max_gif_size.valueChanged.connect( self.valueChanged )
        self._min_resolution.valueChanged.connect( self.valueChanged )
        self._max_resolution.valueChanged.connect( self.valueChanged )
        
    
    def GetValue( self ) -> FileFilteringImportOptions.FileFilteringImportOptions:
        
        file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
        
        file_filtering_import_options.SetAllowedSpecificFiletypes( self._mimes.GetValue() )
        
        file_filtering_import_options.SetAllowsDecompressionBombs( self._allow_decompression_bombs.isChecked() )
        file_filtering_import_options.SetExcludesDeleted( self._exclude_deleted.isChecked() )
        file_filtering_import_options.SetMinSize( self._min_size.GetValue() )
        file_filtering_import_options.SetMaxSize( self._max_size.GetValue() )
        file_filtering_import_options.SetMaxGifSize( self._max_gif_size.GetValue() )
        file_filtering_import_options.SetMinResolution( self._min_resolution.GetValue() )
        file_filtering_import_options.SetMaxResolution( self._max_resolution.GetValue() )
        
        return file_filtering_import_options
        
    
    def SetValue( self, file_filtering_import_options: FileFilteringImportOptions.FileFilteringImportOptions ):
        
        mimes = file_filtering_import_options.GetAllowedSpecificFiletypes()
        
        self._mimes.SetValue( mimes )
        
        self._allow_decompression_bombs.setChecked( file_filtering_import_options.AllowsDecompressionBombs() )
        self._exclude_deleted.setChecked( file_filtering_import_options.ExcludesDeleted() )
        self._min_size.SetValue( file_filtering_import_options.GetMinSize() )
        self._max_size.SetValue( file_filtering_import_options.GetMaxSize() )
        self._max_gif_size.SetValue( file_filtering_import_options.GetMaxGifSize() )
        self._min_resolution.SetValue( file_filtering_import_options.GetMinResolution() )
        self._max_resolution.SetValue( file_filtering_import_options.GetMaxResolution() )
        
    

class EditLocationImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, location_import_options: LocationImportOptions.LocationImportOptions, import_options_caller_type: int ):
        
        super().__init__( parent )
        
        show_downloader_options = import_options_caller_type not in IOC.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES
        
        #
        
        self._destination_location_context_st = ClientGUICommon.BetterStaticText( self, label = 'THIS WILL NOT IMPORT ANYWHERE! Any import queue using this File Import Options will halt!\n\nWas the file service it was previously importing to deleted?' )
        self._destination_location_context_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        self._destination_location_context_st.setWordWrap( True )
        self._destination_location_context_st.setObjectName( 'HydrusWarning' )
        self._destination_location_context_st.style().polish( self._destination_location_context_st )
        
        destination_location_context = location_import_options.GetDestinationLocationContext()
        
        destination_location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._destination_location_context = ClientGUILocation.LocationSearchContextButton( self, destination_location_context )
        self._destination_location_context.SetOnlyImportableDomainsAllowed( True )
        self._destination_location_context.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you have more than one local file domain, you can send these imports to other/multiple locations.' ) )
        
        #
        
        self._do_import_destinations_on_already_in_db_files = QW.QCheckBox( self )
        tt = 'Should a file that is "already in db" be force-added to the import destinations set by these options, if it is missing from any of them? This only matters for clients with multiple local file domains. It is often annoying, so only check this if you are sure you want it (usually for a one-time job).'
        self._do_import_destinations_on_already_in_db_files.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._auto_archive = QW.QCheckBox( self )
        tt = 'Instead of adding imports to the inbox for further processing, this will archive them immediately. You can do this on an import you absolutely know is all good.'
        self._auto_archive.setToolTip( tt )
        
        self._do_archive_on_already_in_db_files = QW.QCheckBox( self )
        tt = 'Should a file that is "already in db" be retroactively archived? If you want to only do this on new files, uncheck this.'
        self._do_archive_on_already_in_db_files.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._associate_primary_urls = QW.QCheckBox( self )
        tt = 'Any URL in the \'chain\' to the file will be linked to it as a \'known url\' unless that URL has a matching URL Class that is set otherwise. Normally, since Gallery URL Classes are by default set not to associate, this means the file will get a visible Post URL and a less prominent direct File URL.'
        tt += '\n' * 2
        tt += 'If you are doing a one-off job and do not want to associate these URLs, disable it here. Do not unset this unless you have a reason to!'
        self._associate_primary_urls.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._associate_source_urls = QW.QCheckBox( self )
        tt = 'If the parser discovers an additional source URL for another site (e.g. "This file on wewbooru was originally posted to Bixiv [here]."), should that URL be associated with the final URL? Should it be trusted to make \'already in db/previously deleted\' determinations?'
        tt += '\n' * 2
        tt += 'You should turn this off if the site supplies bad (incorrect or imprecise or malformed) source urls.'
        self._associate_source_urls.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self.SetValue( location_import_options )
        
        #
        
        rows = []
        
        rows.append( ( 'destination file service(s):', self._destination_location_context ) )
        rows.append( ( '-- ensure \'already in db\' files are added to destinations?: ', self._do_import_destinations_on_already_in_db_files ) )
        rows.append( ( 'auto-archive imports: ', self._auto_archive ) )
        rows.append( ( '-- even for \'already in db\' files?: ', self._do_archive_on_already_in_db_files ) )
        
        if show_downloader_options:
            
            rows.append( ( 'associate primary urls: ', self._associate_primary_urls ) )
            rows.append( ( 'associate (and trust) additional source urls: ', self._associate_source_urls ) )
            
        else:
            
            self._associate_primary_urls.setVisible( False )
            self._associate_source_urls.setVisible( False )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._destination_location_context_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._destination_location_context.locationChanged.connect( self._UpdateLocationText )
        self._auto_archive.clicked.connect( self._UpdateDoArchiveWidget )
        
        self._UpdateLocationText()
        self._UpdateDoArchiveWidget()
        
        self._destination_location_context.locationChanged.connect( self.valueChanged )
        self._do_import_destinations_on_already_in_db_files.clicked.connect( self.valueChanged )
        self._auto_archive.clicked.connect( self.valueChanged )
        self._do_archive_on_already_in_db_files.clicked.connect( self.valueChanged )
        self._associate_primary_urls.clicked.connect( self.valueChanged )
        self._associate_source_urls.clicked.connect( self.valueChanged )
        
    
    def _UpdateDoArchiveWidget( self ):
        
        auto_archive = self._auto_archive.isChecked()
        
        self._do_archive_on_already_in_db_files.setEnabled( auto_archive )
        
    
    def _UpdateLocationText( self ):
        
        location_context = self._destination_location_context.GetValue()
        
        self._destination_location_context_st.setVisible( location_context.IsEmpty() )
        
    
    def GetValue( self ) -> LocationImportOptions.LocationImportOptions:
        
        location_import_options = LocationImportOptions.LocationImportOptions()
        
        location_import_options.SetDestinationLocationContext( self._destination_location_context.GetValue() )
        location_import_options.SetAutomaticallyArchives( self._auto_archive.isChecked() )
        location_import_options.SetShouldAssociatePrimaryURLs( self._associate_primary_urls.isChecked() )
        location_import_options.SetShouldAssociateSourceURLs( self._associate_source_urls.isChecked() )
        location_import_options.SetDoAutomaticArchiveOnAlreadyInDBFiles( self._do_archive_on_already_in_db_files.isChecked() )
        location_import_options.SetDoImportDestinationsOnAlreadyInDBFiles( self._do_import_destinations_on_already_in_db_files.isChecked() )
        
        return location_import_options
        
    
    def SetValue( self, location_import_options: LocationImportOptions.LocationImportOptions ):
        
        destination_location_context = location_import_options.GetDestinationLocationContext()
        
        destination_location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._destination_location_context.SetValue( destination_location_context )
        
        self._auto_archive.setChecked( location_import_options.AutomaticallyArchives() )
        self._do_archive_on_already_in_db_files.setChecked( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles() )
        self._do_import_destinations_on_already_in_db_files.setChecked( location_import_options.DoImportDestinationsOnAlreadyInDBFiles() )
        self._associate_primary_urls.setChecked( location_import_options.ShouldAssociatePrimaryURLs() )
        self._associate_source_urls.setChecked( location_import_options.ShouldAssociateSourceURLs() )
        
    

class EditNoteImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, note_import_options: NoteImportOptions.NoteImportOptions, simple_mode = False ):
        
        super().__init__( parent )
        
        self._simple_mode = simple_mode
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        
        #
        
        self._specific_options_panel = QW.QWidget( self )
        
        #
        
        self._get_notes = QW.QCheckBox( self._specific_options_panel )
        
        tt = 'Check this to get notes. Uncheck to disable it and get nothing.'
        
        self._get_notes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._extend_existing_note_if_possible = QW.QCheckBox( self._specific_options_panel )
        
        tt = 'If a note with the same name already exists on the file, but the new note text is just the same as what exists but with something new appended, should we just replace the existing note with the new extended one?'
        
        self._extend_existing_note_if_possible.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._conflict_resolution = ClientGUICommon.BetterChoice( self._specific_options_panel )
        
        for conflict_resolution_type in [
            NoteImportOptions.NOTE_IMPORT_CONFLICT_REPLACE,
            NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE,
            NoteImportOptions.NOTE_IMPORT_CONFLICT_APPEND,
            NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME
        ]:
            
            self._conflict_resolution.addItem( NoteImportOptions.note_import_conflict_str_lookup[ conflict_resolution_type ], conflict_resolution_type )
            
        
        tt = 'If a note with the same name already exists on the file and the above \'extend\' rule does not apply, what should we do?'
        
        self._conflict_resolution.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._name_whitelist = ClientGUIListBoxes.AddEditDeleteListBox( self._specific_options_panel, 6, str, self._AddWhitelistItem, self._EditWhitelistItem )
        
        tt = 'If you only want some of the notes the parser provides, state them here. Leave this box blank to allow all notes.'
        
        self._name_whitelist.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._names_to_name_overrides = ClientGUIStringControls.StringToStringDictControl( self._specific_options_panel, dict(), min_height = 6, key_name = 'parser name', value_name = 'saved name' )
        
        tt = 'If you want to rename any of the notes the parser provides, set it up here.'
        
        self._names_to_name_overrides.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._all_name_override = ClientGUICommon.NoneableTextCtrl( self._specific_options_panel, '', none_phrase = 'do not mass-rename' )
        
        tt = 'If you want a hacky way to rename one note that is not caught by the above rename rules, whatever it is originally called, set this.'
        tt += '\n' * 2
        tt += 'If multiple notes get renamed this way, then the note conflict rules will apply as they conflict with each other. New notes are processed in original name alphabetical order.'
        
        self._all_name_override.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._SetValue( note_import_options )
        
        #
        
        rows = []
        
        if self._simple_mode:
            
            help_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( help_hbox, help_button, CC.FLAGS_ON_RIGHT )
            
            help_button.setVisible( False )
            
            self._get_notes.setVisible( False )
            self._name_whitelist.setVisible( False )
            self._names_to_name_overrides.setVisible( False )
            self._all_name_override.setVisible( False )
            
            rows.append( ( 'if possible, extend existing notes: ', self._extend_existing_note_if_possible ) )
            rows.append( ( 'if existing note-name conflict, what to do: ', self._conflict_resolution ) )
            
            
        else:
            
            help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
            
            rows.append( ( 'get notes: ', self._get_notes ) )
            rows.append( ( 'if possible, extend existing notes: ', self._extend_existing_note_if_possible ) )
            rows.append( ( 'if existing note-name conflict, what to do: ', self._conflict_resolution ) )
            rows.append( ( 'only allow these note names' + '\n' + '(leave blank for \'get all\'): ', self._name_whitelist ) )
            rows.append( ( 'rename these notes as they come in: ', self._names_to_name_overrides ) )
            rows.append( ( 'rename spare note(s) to this: ', self._all_name_override ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self._specific_options_panel, rows )
        
        self._specific_options_panel.setLayout( gridbox )
        
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._get_notes.clicked.connect( self.valueChanged )
        self._extend_existing_note_if_possible.clicked.connect( self.valueChanged )
        self._conflict_resolution.currentIndexChanged.connect( self.valueChanged )
        self._name_whitelist.listBoxChanged.connect( self.valueChanged )
        self._names_to_name_overrides.columnListContentsChanged.connect( self.valueChanged )
        self._all_name_override.valueChanged.connect( self.valueChanged )
        
    
    def _AddWhitelistItem( self ):
        
        try:
            
            whitelist_name = ClientGUIDialogsQuick.EnterText( self, 'enter the note name', placeholder = 'note name to allow' )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return whitelist_name
        
    
    def _EditWhitelistItem( self, whitelist_name ):
        
        try:
            
            edited_whitelist_name = ClientGUIDialogsQuick.EnterText( self, 'edit the note name', default = whitelist_name, placeholder = 'note name to allow' )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return edited_whitelist_name
        
    
    def _SetValue( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._get_notes.setChecked( note_import_options.GetGetNotes() )
        self._extend_existing_note_if_possible.setChecked( note_import_options.GetExtendExistingNoteIfPossible() )
        self._conflict_resolution.SetValue( note_import_options.GetConflictResolution() )
        
        self._name_whitelist.Clear()
        
        self._name_whitelist.AddDatas( note_import_options.GetNameWhitelist() )
        
        self._names_to_name_overrides.SetValue( note_import_options.GetNamesToNameOverrides() )
        
        self._all_name_override.SetValue( note_import_options.GetAllNameOverride() )
        
    
    def _ShowHelp( self ):
        
        help_message = '''A \'note\' exists in hydrus as the pair of ( name, text ). A file can only have one note for each name. If a downloader provides some notes, normally they will simply be added to your files. The main tricky part comes when a new note conflicts with an existing one.

If a new note coming in has exactly the same text as any note the file already has, no change is made.

If a new note coming in has the same name but different text, then two things can happen:

1) If the new text is the same as the existing text but it has more appended (e.g. an artist comment that since had an extra paragraph added), then if you have \'extend existing notes\' checked, the new note will replace the existing one.

- ADVANCED: Note this can also apply to 'name (1)' renames. If ( name, text ) comes in, and 'text' is an extension of 'name (1)' or 'name (3)', _that_ renamed note will be extended.

2) If the new note is more complicated than an extension, or that checkbox is not checked, then the \'conflict\' action occurs. Think about what you want.

Beyond that, you can filter and rename notes. Check the tooltips for more info.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, help_message )
        
    
    def GetValue( self ) -> NoteImportOptions.NoteImportOptions:
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetGetNotes( self._get_notes.isChecked() )
        note_import_options.SetExtendExistingNoteIfPossible( self._extend_existing_note_if_possible.isChecked() )
        note_import_options.SetConflictResolution( self._conflict_resolution.GetValue() )
        note_import_options.SetNameWhitelist( self._name_whitelist.GetValue() )
        note_import_options.SetNamesToNameOverrides( self._names_to_name_overrides.GetValue() )
        note_import_options.SetAllNameOverride( self._all_name_override.GetValue() )
        
        return note_import_options
        
    
    def SetValue( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._SetValue( note_import_options )
        
    

class EditPrefetchImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, prefetch_import_options: PrefetchImportOptions.PrefetchImportOptions ):
        
        super().__init__( parent )
        
        #
        
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db = QW.QCheckBox( self )
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db = QW.QCheckBox( self )
        
        tt = 'I strongly recommend you uncheck this for normal use. When it is on, downloaders are inefficent!'
        tt += '\n' * 2
        tt += 'This will force the client to download the metadata for a file even if it recognises the URL and thinks it already has it. Normally, hydrus will skip an URL in this case. It is useful to turn this on if you want to force a recheck of the tags in that page.'
        
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        tt = 'I strongly recommend you uncheck this for normal use.  When it is on, downloaders could be inefficent!'
        tt += '\n' * 2
        tt += 'This will force the client to download further metadata for a file even if an earlier parsing step has given a hash it recognises and thinks it already has it. Normally, hydrus will skip downloading an URL in this case. It is useful to turn this on if you want to force a recheck of the tags in that page.'
        
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._preimport_hash_check_type = ClientGUICommon.BetterChoice( self )
        self._preimport_url_check_type = ClientGUICommon.BetterChoice( self )
        
        jobs = [
            ( 'do not check', PrefetchImportOptions.DO_NOT_CHECK),
            ( 'check', PrefetchImportOptions.DO_CHECK ),
            ( 'check - and matches are dispositive', PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE )
        ]
        
        for ( display_string, client_data ) in jobs:
            
            self._preimport_hash_check_type.addItem( display_string, client_data )
            self._preimport_url_check_type.addItem( display_string, client_data )
            
        
        tt = 'DO NOT SET THESE AS THE EXPENSIVE "DO NOT CHECK" UNLESS YOU KNOW YOU NEED IT FOR THIS ONE JOB'
        tt += '\n' * 2
        tt += 'If hydrus recognises a file\'s URL or hash, it can determine that it is "already in db" or "previously deleted" and skip the download entirely, saving a huge amount of time and bandwidth. The logic behind this can get quite complicated, and it is usually best to let it work normally.'
        tt += '\n' * 2
        tt += 'If the checking is set to "dispositive", then if a match is found, that match will be trusted and the other match type is not consulted. Note that, for now, SHA256 hashes your client has never seen before will never count as "matches", just like an MD5 it has not seen before, so in all cases the import will defer to any set url check that says "already in db/previously deleted". (This is to deal with some cloud-storage in-transfer optimisation hash-changing. Novel SHA256 hashes are not always trustworthy.)'
        tt += '\n' * 2
        tt += 'If you believe your clientside parser or url mappings are completely broken, and these logical tests are producing false positive "deleted" or "already in db" results, then set one or both of these to "do not check". Only ever do this for one-time manually fired jobs. Do not turn this on for a normal download or a subscription! You do not need to switch off checking for a file maintenance job that is filling in missing files, as missing files are automatically detected in the logic.'
        
        self._preimport_hash_check_type.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        self._preimport_url_check_type.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._preimport_url_check_looks_for_neighbour_spam = QW.QCheckBox( self )
        
        tt = 'When a file-url mapping is found, an additional check can be performed to see if it is trustworthy.'
        tt += '\n' * 2
        tt += 'If the URL we are checking is recognised as a Post URL, and the file it appears to refer to has other URLs with the same domain & URL Class as what we parsed for the current job (basically the file has or would get multiple URLs on the same site), then this discovered mapping is assumed to be some parse spam and not trustworthy (leading to a "this file looks new" result in the pre-check).'
        tt += '\n' * 2
        tt += 'This test is best left on unless you are doing a single job that is messed up by the logic.'
        
        self._preimport_url_check_looks_for_neighbour_spam.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self.SetValue( prefetch_import_options )
        
        #
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label = 'BE CAREFUL, PREFETCH LOGIC IS ADVANCED' )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        st.setWordWrap( True )
        st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'check hashes to determine "already in db/previously deleted" outcome?: ', self._preimport_hash_check_type ) )
        rows.append( ( 'check URLs to determine "already in db/previously deleted" outcome?: ', self._preimport_url_check_type ) )
        rows.append( ( 'force metadata/page fetch even if hash recognised and file appears "already in db"?: ', self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db ) )
        rows.append( ( 'force metadata/page fetch even if url recognised and file appears "already in db"?: ', self._fetch_metadata_even_if_url_recognised_and_file_already_in_db ) )
        rows.append( ( 'during URL check, check for neighbour-spam?: ', self._preimport_url_check_looks_for_neighbour_spam ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._preimport_hash_check_type.currentIndexChanged.connect( self._UpdateDispositiveFromHash )
        self._preimport_url_check_type.currentIndexChanged.connect( self._UpdateDispositiveFromURL )
        
        self._UpdateDispositiveFromHash()
        self._UpdateDispositiveFromURL()
        
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db.clicked.connect( self.valueChanged )
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db.clicked.connect( self.valueChanged )
        self._preimport_url_check_looks_for_neighbour_spam.clicked.connect( self.valueChanged )
        
    
    def _UpdateDispositiveFromHash( self ):
        
        preimport_hash_check_type = self._preimport_hash_check_type.GetValue()
        preimport_url_check_type = self._preimport_url_check_type.GetValue()
        
        if preimport_hash_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE and preimport_url_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE:
            
            self._preimport_url_check_type.SetValue( PrefetchImportOptions.DO_CHECK )
            
        
        self.valueChanged.emit()
        
    
    def _UpdateDispositiveFromURL( self ):
        
        preimport_hash_check_type = self._preimport_hash_check_type.GetValue()
        preimport_url_check_type = self._preimport_url_check_type.GetValue()
        
        if preimport_hash_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE and preimport_url_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE:
            
            self._preimport_hash_check_type.SetValue( PrefetchImportOptions.DO_CHECK )
            
        
        self._preimport_url_check_looks_for_neighbour_spam.setEnabled( preimport_url_check_type != PrefetchImportOptions.DO_NOT_CHECK )
        
        self.valueChanged.emit()
        
    
    def GetValue( self ) -> PrefetchImportOptions.PrefetchImportOptions:
        
        prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
        
        prefetch_import_options.SetShouldFetchMetadataEvenIfHashKnownAndFileAlreadyInDB( self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db.isChecked())
        prefetch_import_options.SetShouldFetchMetadataEvenIfURLKnownAndFileAlreadyInDB( self._fetch_metadata_even_if_url_recognised_and_file_already_in_db.isChecked())
        
        prefetch_import_options.SetPreImportHashCheckType( self._preimport_hash_check_type.GetValue() )
        prefetch_import_options.SetPreImportURLCheckType( self._preimport_url_check_type.GetValue() )
        prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( self._preimport_url_check_looks_for_neighbour_spam.isChecked() )
        
        return prefetch_import_options
        
    
    def SetValue( self, prefetch_import_options: PrefetchImportOptions.PrefetchImportOptions ):
        
        self._fetch_metadata_even_if_hash_recognised_and_file_already_in_db.setChecked( prefetch_import_options.ShouldFetchMetadataEvenIfHashKnownAndFileAlreadyInDB() )
        self._fetch_metadata_even_if_url_recognised_and_file_already_in_db.setChecked( prefetch_import_options.ShouldFetchMetadataEvenIfURLKnownAndFileAlreadyInDB() )
        
        preimport_hash_check_type = prefetch_import_options.GetPreImportHashCheckType()
        preimport_url_check_type = prefetch_import_options.GetPreImportURLCheckType()
        preimport_url_check_looks_for_neighbour_spam = prefetch_import_options.PreImportURLCheckLooksForNeighbourSpam()
        
        self._preimport_hash_check_type.SetValue( preimport_hash_check_type )
        self._preimport_url_check_type.SetValue( preimport_url_check_type )
        self._preimport_url_check_looks_for_neighbour_spam.setChecked( preimport_url_check_looks_for_neighbour_spam )
        
    

class EditPresentationImportOptions( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, presentation_import_options: PresentationImportOptions.PresentationImportOptions ):
        
        super().__init__( parent )
        
        #
        
        self._presentation_status = ClientGUICommon.BetterChoice( self )
        
        for value in ( PresentationImportOptions.PRESENTATION_STATUS_ANY_GOOD, PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY, PresentationImportOptions.PRESENTATION_STATUS_NONE ):
            
            self._presentation_status.addItem( PresentationImportOptions.presentation_status_enum_str_lookup[ value ], value )
            
        
        tt = 'All files means \'successful\' and \'already in db\'.'
        tt += '\n' * 2
        tt += 'New means only \'successful\'.'
        tt += '\n' * 2
        tt += 'None means this is a silent importer. This is rarely useful.'
        
        self._presentation_status.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._presentation_inbox = ClientGUICommon.BetterChoice( self )
        
        tt = 'Inbox or archive means all files.'
        tt += '\n' * 2
        tt += 'Must be in inbox means only inbox files _at the time of the presentation_. This can be neat as you process and revisit currently watched threads.'
        tt += '\n' * 2
        tt += 'Or in inbox (which only shows if you are set to only see new files) allows already in db results if they are currently in the inbox. Essentially you are just excluding already-in-archive files.'
        
        self._presentation_inbox.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._presentation_location = ClientGUILocation.LocationSearchContextButton( self, presentation_import_options.GetLocationContext() )
        
        tt = 'This is mostly for technical purposes on hydev\'s end, but if you want, you can filter the presented files based on a location context.'
        
        self._presentation_location.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._presentation_status.SetValue( presentation_import_options.GetPresentationStatus() )
        
        self._UpdateInboxChoices()
        
        self._presentation_inbox.SetValue( presentation_import_options.GetPresentationInbox() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._presentation_status, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._presentation_inbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._presentation_location, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._presentation_status.currentIndexChanged.connect( self._UpdateInboxChoices )
        self._presentation_status.currentIndexChanged.connect( self._UpdateEnabled )
        
        self._presentation_status.currentIndexChanged.connect( self.valueChanged )
        self._presentation_inbox.currentIndexChanged.connect( self.valueChanged )
        self._presentation_location.locationChanged.connect( self.valueChanged )
        
    
    def _UpdateEnabled( self ):
        
        enabled = self._presentation_status.GetValue() != PresentationImportOptions.PRESENTATION_STATUS_NONE
        
        self._presentation_inbox.setEnabled( enabled )
        self._presentation_location.setEnabled( enabled )
        
    
    def _UpdateInboxChoices( self ):
        
        do_it = False
        
        previous_presentation_inbox = self._presentation_inbox.GetValue()
        
        presentation_status = self._presentation_status.GetValue()
        
        allowed_values = []
        
        if presentation_status == PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY:
            
            if self._presentation_inbox.count() != 3:
                
                do_it = True
                
                allowed_values = ( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC, PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX, PresentationImportOptions.PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX )
                
            
        else:
            
            if self._presentation_inbox.count() != 2:
                
                do_it = True
                
                allowed_values = ( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC, PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX )
                
                if previous_presentation_inbox == PresentationImportOptions.PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX:
                    
                    previous_presentation_inbox = PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC
                    
                
            
        
        if do_it:
            
            self._presentation_inbox.clear()
            
            for value in allowed_values:
                
                self._presentation_inbox.addItem( PresentationImportOptions.presentation_inbox_enum_str_lookup[ value ], value )
                
            
            self._presentation_inbox.SetValue( previous_presentation_inbox )
            
        
    
    def GetValue( self ) -> PresentationImportOptions.PresentationImportOptions:
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( self._presentation_status.GetValue() )
        presentation_import_options.SetPresentationInbox( self._presentation_inbox.GetValue() )
        presentation_import_options.SetLocationContext( self._presentation_location.GetValue() )
        
        return presentation_import_options
        
    
    def SetValue( self, presentation_import_options: PresentationImportOptions.PresentationImportOptions ):
        
        self._presentation_location.SetValue( presentation_import_options.GetLocationContext() )
        self._presentation_status.SetValue( presentation_import_options.GetPresentationStatus() )
        self._presentation_inbox.SetValue( presentation_import_options.GetPresentationInbox() )
        
    

class EditServiceTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, service_tag_import_options: TagImportOptions.ServiceTagImportOptions, show_downloader_options: bool = True ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._show_downloader_options = show_downloader_options
        
        name = CG.client_controller.services_manager.GetNameSafe( self._service_key )
        
        main_box = ClientGUICommon.StaticBox( self, name )
        
        #
        
        (
            get_tags,
            get_tags_filter,
            self._additional_tags,
            self._to_new_files,
            self._to_already_in_inbox,
            self._to_already_in_archive,
            self._only_add_existing_tags,
            self._only_add_existing_tags_filter,
            self._get_tags_overwrite_deleted,
            self._additional_tags_overwrite_deleted
        ) = service_tag_import_options.ToTuple()
        
        #
        
        menu_template_items = self._GetCogIconMenuItems()
        
        cog_button = ClientGUIMenuButton.CogIconButton( main_box, menu_template_items )
        
        #
        
        tag_parsing_panel = ClientGUICommon.StaticBox( main_box, 'tag parsing' )
        
        self._get_tags_checkbox = QW.QCheckBox( 'get tags', tag_parsing_panel )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            message = None
            
        else:
            
            message = 'Here you can filter which tags are applied to the files being imported in this context. This typically means those tags on a booru file page beside the file, but other contexts provide tags from different locations and quality.'
            message += '\n' * 2
            message += 'The namespace checkboxes on the left are compiled from what all your current parsers say they can do and are simply for convenience. It is worth doing some smaller tests with a new download source to make sure you know what it can provide and what you actually want.'
            message += '\n' * 2
            message += 'Once you are happy, you might want to say \'only "character:", "creator:" and "series:" tags\', or \'everything _except_ "species:" tags\'. This tag filter can get complicated if you want it to--check the help button in the top-right for more information.'
            
        
        self._get_tags_filter_button = ClientGUITagFilter.TagFilterButton( tag_parsing_panel, message, get_tags_filter, label_prefix = 'adding: ', use_filter_language = True )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._get_tags_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._get_tags_filter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        tag_parsing_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._additional_button = ClientGUICommon.BetterButton( main_box, 'additional tags', self._DoAdditionalTags )
        
        #
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        #
        
        if not self._show_downloader_options:
            
            tag_parsing_panel.setVisible( False )
            
        
        main_box.Add( cog_button, CC.FLAGS_ON_RIGHT )
        main_box.Add( tag_parsing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_box.Add( self._additional_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, main_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateAdditionalTagsButtonLabel()
        
        self._UpdateGetTags()
        
        #
        
        self._get_tags_checkbox.clicked.connect( self._UpdateGetTags )
        
    
    def _DoAdditionalTags( self ):
        
        message = 'Any tags you enter here will be applied to every file that passes through this import context.'
        
        with ClientGUIDialogs.DialogInputTags( self, self._service_key, ClientTags.TAG_DISPLAY_STORAGE, list( self._additional_tags ), message = message ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._additional_tags = dlg.GetTags()
                
            
        
        self._UpdateAdditionalTagsButtonLabel()
        
        self.valueChanged.emit()
        
    
    def _EditOnlyAddExistingTagsFilter( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit already-exist filter' ) as dlg:
            
            namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            message = 'If you do not want the \'only add tags that already exist\' option to apply to all tags coming in, set a filter here for the tags you _want_ to be exposed to this test.'
            message += '\n' * 2
            message += 'For instance, if you only want the wash of messy unnamespaced tags to be exposed to the test, then set a simple whitelist for only \'unnamespaced\'.'
            message += '\n' * 2
            message += 'This is obviously a complicated idea, so make sure you test it on a small scale before you try anything big.'
            message += '\n' * 2
            message += 'Clicking ok on this dialog will automatically turn on the already-exists filter if it is off.'
            
            panel = ClientGUITagFilter.EditTagFilterPanel( dlg, self._only_add_existing_tags_filter, namespaces = namespaces, message = message )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._only_add_existing_tags_filter = panel.GetValue()
                
                self._only_add_existing_tags = True
                
            
        
    
    def _GetCogIconMenuItems( self ):
        
        # TODO: This is woo woo, replace it with get/set and self.valueChanged emits
        
        menu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_new_files' )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'apply tags to new files', 'Apply tags to new files.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_already_in_inbox' )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'apply tags to files already in inbox', 'Apply tags to files that are already in the db and in the inbox.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_already_in_archive' )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'apply tags to files already in archive', 'Apply tags to files that are already in the db and archived.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        if self._show_downloader_options:
            
            check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_get_tags_overwrite_deleted' )
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'parsed tags overwrite previously deleted tags', 'Tags parsed and filtered will overwrite the deleted record.', check_manager ) )
            
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_additional_tags_overwrite_deleted' )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'additional tags overwrite previously deleted tags', 'The manually added tags will overwrite the deleted record.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_only_add_existing_tags' )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'only add tags that already exist', 'Only add tags to this service if they have non-zero count.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'set a filter for already-exist test', 'Tell the already-exist test to only work on a subset of tags.', self._EditOnlyAddExistingTagsFilter ) )
        
        return menu_template_items
        
    
    def _UpdateAdditionalTagsButtonLabel( self ):
        
        button_label = HydrusNumbers.ToHumanInt( len( self._additional_tags ) ) + ' additional tags'
        
        self._additional_button.setText( button_label )
        
    
    def _UpdateGetTags( self ):
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        should_enable_filter = get_tags
        
        self._get_tags_filter_button.setEnabled( should_enable_filter )
        
        self.valueChanged.emit()
        
    
    def GetValue( self ) -> TagImportOptions.ServiceTagImportOptions:
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        get_tags_filter = self._get_tags_filter_button.GetValue()
        
        service_tag_import_options = TagImportOptions.ServiceTagImportOptions( get_tags = get_tags, get_tags_filter = get_tags_filter, additional_tags = self._additional_tags, to_new_files = self._to_new_files, to_already_in_inbox = self._to_already_in_inbox, to_already_in_archive = self._to_already_in_archive, only_add_existing_tags = self._only_add_existing_tags, only_add_existing_tags_filter = self._only_add_existing_tags_filter, get_tags_overwrite_deleted = self._get_tags_overwrite_deleted, additional_tags_overwrite_deleted = self._additional_tags_overwrite_deleted )
        
        return service_tag_import_options
        
    
    def SetValue( self, service_tag_import_options: TagImportOptions.ServiceTagImportOptions ):
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted ) = service_tag_import_options.ToTuple()
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        self._get_tags_filter_button.SetValue( get_tags_filter )
        
        self._UpdateGetTags()
        
        self._UpdateAdditionalTagsButtonLabel()
        
    

class EditTagFilteringImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, tag_filtering_import_options: TagFilteringImportOptions.TagFilteringImportOptions ):
        
        super().__init__( parent )
        
        tag_blacklist = tag_filtering_import_options.GetTagBlacklist()
        
        message = 'If a file about to be downloaded has a tag on the site that this blacklist blocks, the file will not be downloaded and imported. If you want to stop \'scat\' or \'gore\', just type them into the list.'
        message += '\n' * 2
        message += 'This system tests the all tags that are parsed from the site, not any other tags the files may have in different places. Siblings of all those tags will also be tested. If none of your tag services have excellent siblings, it is worth adding multiple versions of your tag, just to catch different sites terms. Link up \'gore\', \'guro\', \'violence\', etc...'
        message += '\n' * 2
        message += 'Additionally, unnamespaced rules will apply to namespaced tags. \'low_resolution\' in the blacklist will catch \'meta:low_resolution\' as parsed from a site.'
        message += '\n' * 2
        message += 'It is worth doing a small test here, just to make sure it is all set up how you want.'
        
        self._tag_blacklist_button = ClientGUITagFilter.TagFilterButton( self, message, tag_blacklist, only_show_blacklist = True )
        
        self._tag_blacklist_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'A blacklist will ignore files if they have any of a certain list of tags.' ) )
        
        self._tag_whitelist = list( tag_filtering_import_options.GetTagWhitelist() )
        
        self._tag_whitelist_button = ClientGUICommon.BetterButton( self, 'whitelist', self._EditWhitelist )
        
        self._tag_blacklist_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'A whitelist will ignore files if they do not have any of a certain list of tags.' ) )
        
        self._UpdateTagWhitelistLabel()
        
        #
        
        self.SetValue( tag_filtering_import_options )
        
        #
        
        rows = []
        
        rows.append( ( 'set file blacklist: ', self._tag_blacklist_button ) )
        rows.append( ( 'set file whitelist: ', self._tag_whitelist_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._tag_blacklist_button.valueChanged.connect( self.valueChanged )
        
    
    def _EditWhitelist( self ):
        
        message = 'If you add tags here, then any file importing with these options must have at least one of these tags from the download source. You can mix it with a blacklist--both will apply in turn.'
        message += '\n' * 2
        message += 'This is usually easier and faster to do just by adding tags to the downloader query (e.g. "artistname desired_tag"), so reserve this for downloaders that do not work on tags or where you want to whitelist multiple tags.'
        
        with ClientGUIDialogs.DialogInputTags( self, CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, list( self._tag_whitelist ), message = message ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_whitelist = dlg.GetTags()
                
                self._UpdateTagWhitelistLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateTagWhitelistLabel( self ):
        
        if len( self._tag_whitelist ) == 0:
            
            label = 'no whitelist'
            
        else:
            
            label = 'whitelist of {} tags'.format( HydrusNumbers.ToHumanInt( len( self._tag_whitelist ) ) )
            
        
        self._tag_whitelist_button.setText( label )
        
    
    def GetValue( self ) -> TagFilteringImportOptions.TagFilteringImportOptions:
        
        tag_blacklist = self._tag_blacklist_button.GetValue()
        tag_whitelist = list( self._tag_whitelist )
        
        tag_filtering_import_options = TagFilteringImportOptions.TagFilteringImportOptions( tag_blacklist = tag_blacklist, tag_whitelist = tag_whitelist )
        
        return tag_filtering_import_options
        
    
    def SetValue( self, tag_filtering_import_options: TagFilteringImportOptions.TagFilteringImportOptions ):
        
        self._tag_blacklist_button.SetValue( tag_filtering_import_options.GetTagBlacklist() )
        
        self._tag_whitelist = list( tag_filtering_import_options.GetTagWhitelist() )
        
        self._UpdateTagWhitelistLabel()
        
    

class EditTagImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, tag_import_options: TagImportOptions.TagImportOptions, import_options_caller_type: int ):
        
        super().__init__( parent )
        
        self._show_downloader_options = import_options_caller_type not in IOC.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES
        
        self._service_keys_to_service_tag_import_options_panels = {}
        
        #
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding these tag options.' ) )
        
        #
        
        self._no_tags_label = ClientGUICommon.BetterStaticText( self, label = 'THIS CURRENTLY GETS NO TAGS' )
        
        self._no_tags_label.setObjectName( 'HydrusWarning' )
        
        self._services_vbox = QP.VBoxLayout()
        
        #
        
        self._InitialiseServices( tag_import_options )
        
        self.SetValue( tag_import_options )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._no_tags_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._services_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._UpdateNoTagsLabel()
        
    
    def _InitialiseServices( self, tag_import_options: TagImportOptions.TagImportOptions ):
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel = EditServiceTagImportOptionsPanel( self, service_key, service_tag_import_options, show_downloader_options = self._show_downloader_options )
            
            self._service_keys_to_service_tag_import_options_panels[ service_key ] = panel
            
            QP.AddToLayout( self._services_vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            panel.valueChanged.connect( self._UpdateNoTagsLabel )
            panel.valueChanged.connect( self.valueChanged )
            
        
    
    def _ShowHelp( self ):
        
        message = '''Here you can select which kinds of tags you would like applied to the files that are imported.

If this import context can fetch and parse tags from a remote location (such as a gallery downloader, which may provide 'creator' or 'series' tags, amongst others), then the namespaces it provides will be listed here with checkboxes--simply check which ones you are interested in for the tag services you want them to be applied to and it will all occur as the importer processes its files.

You can also set some fixed 'additional' tags (like, say, 'read later' or 'from my unsorted folder') to be applied to all imported files.

---

Please note that once you know what tags you like, you can (and should) set up the 'default' values for these tag import options under _options->import options_. If you always want all the tags going to 'my tags', this is easy to set up there, and you won't have to put it in every time.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _UpdateNoTagsLabel( self ):
        
        tag_import_options = self.GetValue()
        
        we_explicitly_get_no_tags = not tag_import_options.CanAddTags()
        
        self._no_tags_label.setVisible( we_explicitly_get_no_tags )
        
    
    def GetValue( self ) -> TagImportOptions.TagImportOptions:
        
        service_keys_to_service_tag_import_options = { service_key : panel.GetValue() for ( service_key, panel ) in list( self._service_keys_to_service_tag_import_options_panels.items() ) }
        
        tag_import_options = TagImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        return tag_import_options
        
    
    def SetValue( self, tag_import_options: TagImportOptions.TagImportOptions ):
        
        for ( service_key, panel ) in self._service_keys_to_service_tag_import_options_panels.items():
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel.SetValue( service_tag_import_options )
            
        
    
