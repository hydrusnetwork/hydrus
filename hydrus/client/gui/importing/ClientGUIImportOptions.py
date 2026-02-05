from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
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
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientTags

class EditFileFilteringImportOptionsPanel( QW.QWidget ):
    
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
        
    

class EditFileImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    isDefaultChanged = QC.Signal( bool )
    
    def __init__( self, parent: QW.QWidget, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, show_downloader_options: bool, allow_default_selection: bool ):
        
        super().__init__( parent )
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        if file_import_options.IsDefault():
            
            file_import_options = CG.client_controller.new_options.GetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_LOUD ).Duplicate()
            
            file_import_options.SetIsDefault( True )
            
        
        #
        
        default_panel = ClientGUICommon.StaticBox( self, 'default options' )
        
        self._use_default_dropdown = ClientGUICommon.BetterChoice( default_panel )
        
        self._use_default_dropdown.addItem( 'use the default file import options at the time of import', True )
        self._use_default_dropdown.addItem( 'set custom file import options just for this importer', False )
        
        tt = 'Normally, the client will refer to the defaults (as set under "options->importing") at the time of import.'
        tt += '\n' * 2
        tt += 'It is easier to work this way, since you can change a single default setting and update all current and future downloaders that refer to those defaults, whereas having specific options for every subscription or downloader means you have to update every single one just to make a little change somewhere.'
        tt += '\n' * 2
        tt += 'But if you are doing a one-time import that has some unusual file rules, set them here.'
        
        self._use_default_dropdown.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._load_default_options = ClientGUICommon.BetterButton( self, 'load one of the default options', self._LoadDefaultOptions )
        
        #
        
        self._specific_options_panel = QW.QWidget( self )
        
        #
        
        prefetch_import_panel = ClientGUICommon.StaticBox( self._specific_options_panel, 'prefetch', can_expand = True, start_expanded = False )
        
        self._prefetch_import_options_panel = EditPrefetchImportOptionsPanel( prefetch_import_panel, file_import_options.GetPrefetchImportOptions() )
        
        #
        
        file_filtering_panel = ClientGUICommon.StaticBox( self._specific_options_panel, 'file filtering' )
        
        self._file_filtering_import_options_panel = EditFileFilteringImportOptionsPanel( file_filtering_panel, file_import_options.GetFileFilteringImportOptions() )
        
        #
        
        self._use_default_dropdown.SetValue( file_import_options.IsDefault() )
        
        #
        
        locations_panel = ClientGUICommon.StaticBox( self._specific_options_panel, 'locations' )
        
        self._location_import_options_panel = EditLocationImportOptionsPanel( locations_panel, file_import_options.GetLocationImportOptions(), show_downloader_options )
        
        #
        
        presentation_static_box = ClientGUICommon.StaticBox( self._specific_options_panel, 'presentation options' )
        
        presentation_import_options = file_import_options.GetPresentationImportOptions()
        
        self._presentation_import_options_panel = EditPresentationImportOptions( presentation_static_box, presentation_import_options )
        
        #
        
        self._SetValue( file_import_options )
        
        #
        
        default_panel.Add( self._use_default_dropdown, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not allow_default_selection:
            
            default_panel.hide()
            
        
        #
        
        prefetch_import_panel.Add( self._prefetch_import_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        prefetch_import_panel.setVisible( show_downloader_options )
        
        #
        
        file_filtering_panel.Add( self._file_filtering_import_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        locations_panel.Add( self._location_import_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        presentation_static_box.Add( self._presentation_import_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        specific_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( specific_vbox, prefetch_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( specific_vbox, file_filtering_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( specific_vbox, locations_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( specific_vbox, presentation_static_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._specific_options_panel.setLayout( specific_vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, default_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._load_default_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._use_default_dropdown.currentIndexChanged.connect( self._UpdateIsDefault )
        
        self._UpdateIsDefault()
        
    
    def _LoadDefaultOptions( self ):
        
        loud_file_import_options = CG.client_controller.new_options.GetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
        quiet_file_import_options = CG.client_controller.new_options.GetDefaultFileImportOptions( FileImportOptionsLegacy.IMPORT_TYPE_QUIET )
        
        choice_tuples = []
        
        choice_tuples.append( ( 'loud default', loud_file_import_options ) )
        choice_tuples.append( ( 'quiet default', quiet_file_import_options ) )
        
        try:
            
            default_file_import_options = ClientGUIDialogsQuick.SelectFromList( self, 'Select which default', choice_tuples, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if default_file_import_options is None:
            
            return
            
        
        self._SetValue( default_file_import_options )
        
    
    def _SetValue( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        self._use_default_dropdown.SetValue( file_import_options.IsDefault() )
        
        self._prefetch_import_options_panel.SetValue( file_import_options.GetPrefetchImportOptions() )
        self._file_filtering_import_options_panel.SetValue( file_import_options.GetFileFilteringImportOptions() )
        self._location_import_options_panel.SetValue( file_import_options.GetLocationImportOptions() )
        self._presentation_import_options_panel.SetValue( file_import_options.GetPresentationImportOptions() )
        
        #
        
        self._UpdateIsDefault()
        
    
    def _ShowHelp( self ):
        
        help_message = '''-exclude previously deleted files-

If this is set and an incoming file has already been seen and deleted before by this client, the import will be abandoned. This is useful to make sure you do not keep importing and deleting the same bad files over and over. Files currently in the trash count as deleted.

-allow decompression bombs-

Some images, called Decompression Bombs, consume huge amounts of memory and CPU time (typically multiple GB and 30s+) to render. These can be malicious attacks or accidentally inelegant compressions of very large images (typically 100MegaPixel+ pngs). Keep this unchecked to catch and disallow them before they blat your computer.

-max gif size-

Some artists and over-enthusiastic fans re-encode popular webms into gif, typically so they can be viewed on simpler platforms like older phones. These people do not know what they are doing and generate 20MB, 100MB, even 220MB(!) gif files that they then upload to the boorus. Most hydrus users do not want these duplicate, bloated, bad-paletted, and CPU-laggy files on their clients, so this can probit them.

-archive all imports-

If this is set, all successful imports will be archived rather than sent to the inbox. This applies to files 'already in db' as well (these would otherwise retain their existing inbox status unaltered).

-presentation options-

For regular import pages, 'presentation' means if the imported file's thumbnail will be added. For quieter queues like subscriptions, it determines if the file will be in any popup message button.

If you have a very large (10k+ files) file import page, consider hiding some or all of its thumbs to reduce ui lag and increase overall import speed.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, help_message )
        
    
    def _UpdateIsDefault( self ):
        
        is_default = self._use_default_dropdown.GetValue()
        
        show_specific_options = not is_default
        
        self._load_default_options.setVisible( show_specific_options )
        
        self._specific_options_panel.setVisible( show_specific_options )
        
        if not show_specific_options:
            
            self.window().adjustSize()
            
        
        self.isDefaultChanged.emit( is_default )
        
    
    def GetValue( self ) -> FileImportOptionsLegacy.FileImportOptionsLegacy:
        
        is_default = self._use_default_dropdown.GetValue()
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        
        if is_default:
            
            file_import_options.SetIsDefault( True )
            
        else:
            
            file_import_options.SetPrefetchImportOptions( self._prefetch_import_options_panel.GetValue() )
            file_import_options.SetFileFilteringImportOptions( self._file_filtering_import_options_panel.GetValue() )
            file_import_options.SetLocationImportOptions( self._location_import_options_panel.GetValue() )
            file_import_options.SetPresentationImportOptions( self._presentation_import_options_panel.GetValue() )
            
        
        return file_import_options
        
    
    def CheckValid( self ):
        
        file_import_options = self.GetValue()
        
        try:
            
            file_import_options.GetLocationImportOptions().CheckReadyToImport()
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( e )
            
        
    

class EditLocationImportOptionsPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, location_import_options: LocationImportOptions.LocationImportOptions, show_downloader_options: bool ):
        
        super().__init__( parent )
        
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
        
        self.setLayout( vbox )
        
        self._destination_location_context.locationChanged.connect( self._UpdateLocationText )
        self._auto_archive.clicked.connect( self._UpdateDoArchiveWidget )
        
        self._UpdateLocationText()
        self._UpdateDoArchiveWidget()
        
    
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
    
    isDefaultChanged = QC.Signal( bool )
    
    def __init__( self, parent: QW.QWidget, note_import_options: NoteImportOptions.NoteImportOptions, allow_default_selection: bool, simple_mode = False ):
        
        super().__init__( parent )
        
        self._allow_default_selection = allow_default_selection
        self._simple_mode = simple_mode
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        
        #
        
        default_panel = ClientGUICommon.StaticBox( self, 'default options' )
        
        self._use_default_dropdown = ClientGUICommon.BetterChoice( default_panel )
        
        self._use_default_dropdown.addItem( 'use the default note import options at the time of import', True )
        self._use_default_dropdown.addItem( 'set custom note import options just for this importer', False )
        
        tt = 'Normally, the client will refer to the defaults (as set under "network->downloaders->manage default import options") at the time of import.'
        tt += '\n' * 2
        tt += 'It is easier to work this way, since you can change a single default setting and update all current and future downloaders that refer to those defaults, whereas having specific options for every subscription or downloader means you have to update every single one just to make a little change somewhere.'
        tt += '\n' * 2
        tt += 'But if you are doing a one-time import that has some unusual note merge rules, set them here.'
        
        self._use_default_dropdown.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._load_default_options = ClientGUICommon.BetterButton( self, 'load one of the default options', self._LoadDefaultOptions )
        
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
        
        self._use_default_dropdown.SetValue( note_import_options.IsDefault() )
        
        #
        
        self._SetValue( note_import_options )
        
        #
        
        default_panel.Add( self._use_default_dropdown, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not self._allow_default_selection:
            
            default_panel.setVisible( False )
            
        
        #
        
        
        rows = []
        
        if self._simple_mode:
            
            help_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( help_hbox, help_button, CC.FLAGS_ON_RIGHT )
            
            help_button.setVisible( False )
            
            default_panel.setVisible( False )
            self._load_default_options.setVisible( False )
            
            self._get_notes.setVisible( False )
            self._name_whitelist.setVisible( False )
            self._names_to_name_overrides.setVisible( False )
            self._all_name_override.setVisible( False )
            
            rows.append( ( 'if possible, extend existing notes: ', self._extend_existing_note_if_possible ) )
            rows.append( ( 'if existing note conflict, what to do: ', self._conflict_resolution ) )
            
            
        else:
            
            help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
            
            rows.append( ( 'get notes: ', self._get_notes ) )
            rows.append( ( 'if possible, extend existing notes: ', self._extend_existing_note_if_possible ) )
            rows.append( ( 'if existing note conflict, what to do: ', self._conflict_resolution ) )
            rows.append( ( 'only allow these note names' + '\n' + '(leave blank for \'get all\'): ', self._name_whitelist ) )
            rows.append( ( 'rename these notes as they come in: ', self._names_to_name_overrides ) )
            rows.append( ( 'rename spare note(s) to this: ', self._all_name_override ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self._specific_options_panel, rows )
        
        self._specific_options_panel.setLayout( gridbox )
        
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, default_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._load_default_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._use_default_dropdown.currentIndexChanged.connect( self._UpdateIsDefault )
        
        self._UpdateIsDefault()
        
    
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
        
    
    def _LoadDefaultOptions( self ):
        
        domain_manager = CG.client_controller.network_engine.domain_manager
        
        ( file_post_default_note_import_options, watchable_default_note_import_options, url_class_keys_to_default_note_import_options ) = domain_manager.GetDefaultNoteImportOptions()
        
        choice_tuples = []
        
        choice_tuples.append( ( 'file post default', file_post_default_note_import_options ) )
        choice_tuples.append( ( 'watchable default', watchable_default_note_import_options ) )
        
        if len( url_class_keys_to_default_note_import_options ) > 0:
            
            choice_tuples.append( ( '----', None ) )
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in url_classes }
            
            url_class_names_and_default_note_import_options = sorted( ( ( url_class_keys_to_url_classes[ url_class_key ].GetName(), url_class_keys_to_default_note_import_options[ url_class_key ] ) for url_class_key in list( url_class_keys_to_default_note_import_options.keys() ) if url_class_key in url_class_keys_to_url_classes ) )
            
            choice_tuples.extend( url_class_names_and_default_note_import_options )
            
        
        try:
            
            default_note_import_options = ClientGUIDialogsQuick.SelectFromList( self, 'Select which default', choice_tuples, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if default_note_import_options is None:
            
            return
            
        
        self._SetValue( default_note_import_options )
        
    
    def _SetValue( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._use_default_dropdown.SetValue( note_import_options.IsDefault() )
        
        #
        
        self._get_notes.setChecked( note_import_options.GetGetNotes() )
        self._extend_existing_note_if_possible.setChecked( note_import_options.GetExtendExistingNoteIfPossible() )
        self._conflict_resolution.SetValue( note_import_options.GetConflictResolution() )
        
        self._name_whitelist.Clear()
        
        self._name_whitelist.AddDatas( note_import_options.GetNameWhitelist() )
        
        self._names_to_name_overrides.SetValue( note_import_options.GetNamesToNameOverrides() )
        
        self._all_name_override.SetValue( note_import_options.GetAllNameOverride() )
        
        #
        
        self._UpdateIsDefault()
        
    
    def _ShowHelp( self ):
        
        help_message = '''A \'note\' exists in hydrus as the pair of ( name, text ). A file can only have one note for each name. If a downloader provides some notes, normally they will simply be added to your files. The main tricky part comes when a new note conflicts with an existing one.

If a new note coming in has exactly the same text as any note the file already has, no change is made.

If a new note coming in has the same name but different text, then two things can happen:

1) If the new text is the same as the existing text but it has more appended (e.g. an artist comment that since had an extra paragraph added), then if you have \'extend existing notes\' checked, the new note will replace the existing one.

- ADVANCED: Note this can also apply to 'name (1)' renames. If ( name, text ) comes in, and 'text' is an extension of 'name (1)' or 'name (3)', _that_ renamed note will be extended.

2) If the new note is more complicated than an extension, or that checkbox is not checked, then the \'conflict\' action occurs. Think about what you want.

Beyond that, you can filter and rename notes. Check the tooltips for more info.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, help_message )
        
    
    def _UpdateIsDefault( self ):
        
        if self._simple_mode or not self._allow_default_selection:
            
            return
            
        
        is_default = self._use_default_dropdown.GetValue()
        
        show_specific_options = not is_default
        
        self._load_default_options.setVisible( show_specific_options )
        
        self._specific_options_panel.setVisible( show_specific_options )
        
        if not show_specific_options:
            
            self.window().adjustSize()
            
        
        self.isDefaultChanged.emit( is_default )
        
    
    def GetValue( self ) -> NoteImportOptions.NoteImportOptions:
        
        is_default = self._use_default_dropdown.GetValue()
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        if is_default:
            
            note_import_options.SetIsDefault( True )
            
        else:
            
            note_import_options.SetGetNotes( self._get_notes.isChecked() )
            note_import_options.SetExtendExistingNoteIfPossible( self._extend_existing_note_if_possible.isChecked() )
            note_import_options.SetConflictResolution( self._conflict_resolution.GetValue() )
            note_import_options.SetNameWhitelist( self._name_whitelist.GetValue() )
            note_import_options.SetNamesToNameOverrides( self._names_to_name_overrides.GetValue() )
            note_import_options.SetAllNameOverride( self._all_name_override.GetValue() )
            
        
        return note_import_options
        
    

class EditPrefetchImportOptionsPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, prefetch_import_options: PrefetchImportOptions.PrefetchImportOptions ):
        
        super().__init__( parent )
        
        #
        
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
        
        rows.append( ( 'check hashes to determine "already in db/previously deleted"?: ', self._preimport_hash_check_type ) )
        rows.append( ( 'check URLs to determine "already in db/previously deleted"?: ', self._preimport_url_check_type ) )
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
        
    
    def _UpdateDispositiveFromHash( self ):
        
        preimport_hash_check_type = self._preimport_hash_check_type.GetValue()
        preimport_url_check_type = self._preimport_url_check_type.GetValue()
        
        if preimport_hash_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE and preimport_url_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE:
            
            self._preimport_url_check_type.SetValue( PrefetchImportOptions.DO_CHECK )
            
        
    
    def _UpdateDispositiveFromURL( self ):
        
        preimport_hash_check_type = self._preimport_hash_check_type.GetValue()
        preimport_url_check_type = self._preimport_url_check_type.GetValue()
        
        if preimport_hash_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE and preimport_url_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE:
            
            self._preimport_hash_check_type.SetValue( PrefetchImportOptions.DO_CHECK )
            
        
        self._preimport_url_check_looks_for_neighbour_spam.setEnabled( preimport_url_check_type != PrefetchImportOptions.DO_NOT_CHECK )
        
    
    def GetValue( self ) -> PrefetchImportOptions.PrefetchImportOptions:
        
        prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
        
        prefetch_import_options.SetPreImportHashCheckType( self._preimport_hash_check_type.GetValue() )
        prefetch_import_options.SetPreImportURLCheckType( self._preimport_url_check_type.GetValue() )
        prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( self._preimport_url_check_looks_for_neighbour_spam.isChecked() )
        
        return prefetch_import_options
        
    
    def SetValue( self, prefetch_import_options: PrefetchImportOptions.PrefetchImportOptions ):
        
        preimport_hash_check_type = prefetch_import_options.GetPreImportHashCheckType()
        preimport_url_check_type = prefetch_import_options.GetPreImportURLCheckType()
        preimport_url_check_looks_for_neighbour_spam = prefetch_import_options.PreImportURLCheckLooksForNeighbourSpam()
        
        self._preimport_hash_check_type.SetValue( preimport_hash_check_type )
        self._preimport_url_check_type.SetValue( preimport_url_check_type )
        self._preimport_url_check_looks_for_neighbour_spam.setChecked( preimport_url_check_looks_for_neighbour_spam )
        
    

class EditPresentationImportOptions( QW.QWidget ):
    
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
        
        label = 'An importer will try to import everything in its queue, but it does not have to _show_ all the successful results in the import page or subscription button/page. Many advanced users will set this to only show _new_ results to skip seeing \'already in db\' files.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        st.setWordWrap( True )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._presentation_status, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._presentation_inbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._presentation_location, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._presentation_status.currentIndexChanged.connect( self._UpdateInboxChoices )
        self._presentation_status.currentIndexChanged.connect( self._UpdateEnabled )
        
    
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
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, service_tag_import_options: TagImportOptionsLegacy.ServiceTagImportOptions, show_downloader_options: bool = True ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._show_downloader_options = show_downloader_options
        
        name = CG.client_controller.services_manager.GetName( self._service_key )
        
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
        
        downloader_options_panel = ClientGUICommon.StaticBox( main_box, 'tag parsing' )
        
        self._get_tags_checkbox = QW.QCheckBox( 'get tags', downloader_options_panel )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            message = None
            
        else:
            
            message = 'Here you can filter which tags are applied to the files being imported in this context. This typically means those tags on a booru file page beside the file, but other contexts provide tags from different locations and quality.'
            message += '\n' * 2
            message += 'The namespace checkboxes on the left are compiled from what all your current parsers say they can do and are simply for convenience. It is worth doing some smaller tests with a new download source to make sure you know what it can provide and what you actually want.'
            message += '\n' * 2
            message += 'Once you are happy, you might want to say \'only "character:", "creator:" and "series:" tags\', or \'everything _except_ "species:" tags\'. This tag filter can get complicated if you want it to--check the help button in the top-right for more information.'
            
        
        self._get_tags_filter_button = ClientGUITagFilter.TagFilterButton( downloader_options_panel, message, get_tags_filter, label_prefix = 'adding: ' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._get_tags_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._get_tags_filter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        downloader_options_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._additional_button = ClientGUICommon.BetterButton( main_box, 'additional tags', self._DoAdditionalTags )
        
        #
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        #
        
        if not self._show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        main_box.Add( cog_button, CC.FLAGS_ON_RIGHT )
        main_box.Add( downloader_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
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
        
    
    def GetValue( self ) -> TagImportOptionsLegacy.ServiceTagImportOptions:
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        get_tags_filter = self._get_tags_filter_button.GetValue()
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = get_tags, get_tags_filter = get_tags_filter, additional_tags = self._additional_tags, to_new_files = self._to_new_files, to_already_in_inbox = self._to_already_in_inbox, to_already_in_archive = self._to_already_in_archive, only_add_existing_tags = self._only_add_existing_tags, only_add_existing_tags_filter = self._only_add_existing_tags_filter, get_tags_overwrite_deleted = self._get_tags_overwrite_deleted, additional_tags_overwrite_deleted = self._additional_tags_overwrite_deleted )
        
        return service_tag_import_options
        
    
    def SetValue( self, service_tag_import_options: TagImportOptionsLegacy.ServiceTagImportOptions ):
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted ) = service_tag_import_options.ToTuple()
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        self._get_tags_filter_button.SetValue( get_tags_filter )
        
        self._UpdateGetTags()
        
        self._UpdateAdditionalTagsButtonLabel()
        
    

class EditTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    isDefaultChanged = QC.Signal( bool )
    
    def __init__( self, parent: QW.QWidget, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy, show_downloader_options: bool, allow_default_selection: bool ):
        
        super().__init__( parent )
        
        self._show_downloader_options = show_downloader_options
        
        self._service_keys_to_service_tag_import_options_panels = {}
        
        #
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding these tag options.' ) )
        
        #
        
        default_panel = ClientGUICommon.StaticBox( self, 'default options' )
        
        self._use_default_dropdown = ClientGUICommon.BetterChoice( default_panel )
        
        self._use_default_dropdown.addItem( 'use the default tag import options at the time of import', True )
        self._use_default_dropdown.addItem( 'set custom tag import options just for this importer', False )
        
        tt = 'Normally, the client will refer to the defaults (as set under "network->downloaders->manage default import options") for the appropriate tag import options at the time of import.'
        tt += '\n' * 2
        tt += 'It is easier to work this way, since you can change a single default setting and update all current and future downloaders that refer to those defaults, whereas having specific options for every subscription or downloader means you have to update every single one just to make a little change somewhere.'
        tt += '\n' * 2
        tt += 'But if you are doing a one-time import that has some unusual tag rules, set them here.'
        
        self._use_default_dropdown.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._load_default_options = ClientGUICommon.BetterButton( self, 'load one of the default options', self._LoadDefaultOptions )
        
        #
        
        self._specific_options_panel = QW.QWidget( self )
        
        #
        
        downloader_options_panel = ClientGUICommon.StaticBox( self._specific_options_panel, 'fetch options' )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = QW.QCheckBox( downloader_options_panel )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = QW.QCheckBox( downloader_options_panel )
        
        tt = 'I strongly recommend you uncheck this for normal use. When it is on, downloaders are inefficent!'
        tt += '\n' * 2
        tt += 'This will force the client to download the metadata for a file even if it thinks it has visited its page before. Normally, hydrus will skip an URL in this case. It is useful to turn this on if you want to force a recheck of the tags in that page.'
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        tt = 'I strongly recommend you uncheck this for normal use.  When it is on, downloaders could be inefficent!'
        tt += '\n' * 2
        tt += 'This will force the client to download the metadata for a file even if the gallery step has given a hash that the client thinks it recognises. Normally, hydrus will skip an URL in this case (although the hash-from-gallery case is rare, so this option rarely matters). This is mostly a debug complement to the url check option.'
        
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        tag_blacklist = tag_import_options.GetTagBlacklist()
        
        message = 'If a file about to be downloaded has a tag on the site that this blacklist blocks, the file will not be downloaded and imported. If you want to stop \'scat\' or \'gore\', just type them into the list.'
        message += '\n' * 2
        message += 'This system tests the all tags that are parsed from the site, not any other tags the files may have in different places. Siblings of all those tags will also be tested. If none of your tag services have excellent siblings, it is worth adding multiple versions of your tag, just to catch different sites terms. Link up \'gore\', \'guro\', \'violence\', etc...'
        message += '\n' * 2
        message += 'Additionally, unnamespaced rules will apply to namespaced tags. \'metroid\' in the blacklist will catch \'series:metroid\' as parsed from a site.'
        message += '\n' * 2
        message += 'It is worth doing a small test here, just to make sure it is all set up how you want.'
        
        self._tag_blacklist_button = ClientGUITagFilter.TagFilterButton( downloader_options_panel, message, tag_blacklist, only_show_blacklist = True )
        
        self._tag_blacklist_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'A blacklist will ignore files if they have any of a certain list of tags.' ) )
        
        self._tag_whitelist = list( tag_import_options.GetTagWhitelist() )
        
        self._tag_whitelist_button = ClientGUICommon.BetterButton( downloader_options_panel, 'whitelist', self._EditWhitelist )
        
        self._tag_blacklist_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'A whitelist will ignore files if they do not have any of a certain list of tags.' ) )
        
        self._UpdateTagWhitelistLabel()
        
        self._no_tags_label = ClientGUICommon.BetterStaticText( self, label = 'THIS CURRENTLY GETS NO TAGS' )
        
        self._no_tags_label.setObjectName( 'HydrusWarning' )
        
        self._services_vbox = QP.VBoxLayout()
        
        #
        
        self._use_default_dropdown.SetValue( tag_import_options.IsDefault() )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        self._InitialiseServices( tag_import_options )
        
        self._SetValue( tag_import_options )
        
        #
        
        if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            st = ClientGUICommon.BetterStaticText( default_panel, label = 'Most of the time, you want to rely on the default tag import options!' )
            
            st.setObjectName( 'HydrusWarning' )
            
            default_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        default_panel.Add( self._use_default_dropdown, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not allow_default_selection:
            
            default_panel.hide()
            
        
        #
        
        rows = []
        
        rows.append( ( 'force page fetch even if url recognised and file already in db: ', self._fetch_tags_even_if_url_recognised_and_file_already_in_db ) )
        rows.append( ( 'force page fetch even if hash recognised and file already in db: ', self._fetch_tags_even_if_hash_recognised_and_file_already_in_db ) )
        rows.append( ( 'set file blacklist: ', self._tag_blacklist_button ) )
        rows.append( ( 'set file whitelist: ', self._tag_whitelist_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( downloader_options_panel, rows )
        
        downloader_options_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if not self._show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, downloader_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._no_tags_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._services_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._specific_options_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, default_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._load_default_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._use_default_dropdown.currentIndexChanged.connect( self._UpdateIsDefault )
        
        self._UpdateIsDefault()
        
        self._UpdateNoTagsLabel()
        
    
    def _EditWhitelist( self ):
        
        message = 'If you add tags here, then any file importing with these options must have at least one of these tags from the download source. You can mix it with a blacklist--both will apply in turn.'
        message += '\n' * 2
        message += 'This is usually easier and faster to do just by adding tags to the downloader query (e.g. "artistname desired_tag"), so reserve this for downloaders that do not work on tags or where you want to whitelist multiple tags.'
        
        with ClientGUIDialogs.DialogInputTags( self, CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, list( self._tag_whitelist ), message = message ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_whitelist = dlg.GetTags()
                
                self._UpdateTagWhitelistLabel()
                
            
        
    
    def _InitialiseServices( self, tag_import_options ):
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel = EditServiceTagImportOptionsPanel( self._specific_options_panel, service_key, service_tag_import_options, show_downloader_options = self._show_downloader_options )
            
            self._service_keys_to_service_tag_import_options_panels[ service_key ] = panel
            
            QP.AddToLayout( self._services_vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            panel.valueChanged.connect( self._UpdateNoTagsLabel )
            
        
    
    def _LoadDefaultOptions( self ):
        
        domain_manager = CG.client_controller.network_engine.domain_manager
        
        ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_default_tag_import_options ) = domain_manager.GetDefaultTagImportOptions()
        
        choice_tuples = []
        
        choice_tuples.append( ( 'file post default', file_post_default_tag_import_options ) )
        choice_tuples.append( ( 'watchable default', watchable_default_tag_import_options ) )
        
        if len( url_class_keys_to_default_tag_import_options ) > 0:
            
            choice_tuples.append( ( '----', None ) )
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in url_classes }
            
            url_class_names_and_default_tag_import_options = sorted( ( ( url_class_keys_to_url_classes[ url_class_key ].GetName(), url_class_keys_to_default_tag_import_options[ url_class_key ] ) for url_class_key in list( url_class_keys_to_default_tag_import_options.keys() ) if url_class_key in url_class_keys_to_url_classes ) )
            
            choice_tuples.extend( url_class_names_and_default_tag_import_options )
            
        
        try:
            
            default_tag_import_options = ClientGUIDialogsQuick.SelectFromList( self, 'Select which default', choice_tuples, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if default_tag_import_options is None:
            
            return
            
        
        self._SetValue( default_tag_import_options )
        
    
    def _SetValue( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        self._use_default_dropdown.SetValue( tag_import_options.IsDefault() )
        
        self._tag_blacklist_button.SetValue( tag_import_options.GetTagBlacklist() )
        
        self._tag_whitelist = list( tag_import_options.GetTagWhitelist() )
        
        self._UpdateTagWhitelistLabel()
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        for ( service_key, panel ) in self._service_keys_to_service_tag_import_options_panels.items():
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel.SetValue( service_tag_import_options )
            
        
        self._UpdateIsDefault()
        
    
    def _ShowHelp( self ):
        
        message = '''Here you can select which kinds of tags you would like applied to the files that are imported.

If this import context can fetch and parse tags from a remote location (such as a gallery downloader, which may provide 'creator' or 'series' tags, amongst others), then the namespaces it provides will be listed here with checkboxes--simply check which ones you are interested in for the tag services you want them to be applied to and it will all occur as the importer processes its files.

In these cases, if the URL has been previously downloaded and the client knows its file is already in the database, the client will usually not make a new network request to fetch the file's tags. This allows for quick reprocessing/skipping of previously seen items in large download queues and saves bandwidth. If you however wish to purposely fetch tags for files you have previously downloaded, you can also force tag fetching for these 'already in db' files.

I strongly recommend that you only ever turn this 'fetch tags even...' option for one-time jobs. It is typically only useful if you download some files and realised you forgot to set the tag parsing options you like--you can set the fetch option on and 'try again' the files to force the downloader to fetch the tags.

You can also set some fixed 'explicit' tags (like, say, 'read later' or 'from my unsorted folder' or 'pixiv subscription') to be applied to all imported files.

---

Please note that once you know what tags you like, you can (and should) set up the 'default' values for these tag import options under _network->downloaders->manage default import options_, both globally and on a per-parser basis. If you always want all the tags going to 'my tags', this is easy to set up there, and you won't have to put it in every time.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _UpdateIsDefault( self ):
        
        is_default = self._use_default_dropdown.GetValue()
        
        show_specific_options = not is_default
        
        self._load_default_options.setVisible( show_specific_options )
        
        self._specific_options_panel.setVisible( show_specific_options )
        
        if not show_specific_options:
            
            self.window().adjustSize()
            
        
        self._UpdateNoTagsLabel()
        
        self.isDefaultChanged.emit( is_default )
        
    
    def _UpdateNoTagsLabel( self ):
        
        tag_import_options = self.GetValue()
        
        we_explicitly_get_no_tags = ( not tag_import_options.IsDefault() ) and ( not tag_import_options.CanAddTags() )
        
        self._no_tags_label.setVisible( we_explicitly_get_no_tags )
        
        self.updateGeometry()
        
    
    def _UpdateTagWhitelistLabel( self ):
        
        if len( self._tag_whitelist ) == 0:
            
            label = 'no whitelist'
            
        else:
            
            label = 'whitelist of {} tags'.format( HydrusNumbers.ToHumanInt( len( self._tag_whitelist ) ) )
            
        
        self._tag_whitelist_button.setText( label )
        
    
    def GetValue( self ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        is_default = self._use_default_dropdown.GetValue()
        
        if is_default:
            
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
            
        else:
            
            fetch_tags_even_if_url_recognised_and_file_already_in_db = self._fetch_tags_even_if_url_recognised_and_file_already_in_db.isChecked()
            fetch_tags_even_if_hash_recognised_and_file_already_in_db = self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.isChecked()
            
            service_keys_to_service_tag_import_options = { service_key : panel.GetValue() for ( service_key, panel ) in list( self._service_keys_to_service_tag_import_options_panels.items() ) }
            
            tag_blacklist = self._tag_blacklist_button.GetValue()
            tag_whitelist = list( self._tag_whitelist )
            
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db, tag_blacklist = tag_blacklist, tag_whitelist = tag_whitelist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
            
        
        return tag_import_options
        
    

class EditImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, show_downloader_options: bool, allow_default_selection: bool ):
        
        super().__init__( parent )
        
        self._show_downloader_options = show_downloader_options
        self._allow_default_selection = allow_default_selection
        
        self._file_import_options_panel = None
        self._note_import_options_panel = None
        self._tag_import_options_panel = None
        
        self._notebook = QW.QTabWidget( self )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetFileImportOptions( self ) -> FileImportOptionsLegacy.FileImportOptionsLegacy:
        
        if self._file_import_options_panel is None:
            
            raise Exception( 'This Import Options Panel does not have any File Import Options set!' )
            
        
        return self._file_import_options_panel.GetValue()
        
    
    def GetNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        if self._note_import_options_panel is None:
            
            raise Exception( 'This Import Options Panel does not have any Note Import Options set!' )
            
        
        return self._note_import_options_panel.GetValue()
        
    
    def GetTagImportOptions( self ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        if self._tag_import_options_panel is None:
            
            raise Exception( 'This Import Options Panel does not have any Tag Import Options set!' )
            
        
        return self._tag_import_options_panel.GetValue()
        
    
    def GetValue( self ):
        
        # keep this even if we don't use it since checkvalid tests it
        
        if self._file_import_options_panel is None:
            
            file_import_options = None
            
        else:
            
            file_import_options = self._file_import_options_panel.GetValue()
            
        
        if self._note_import_options_panel is None:
            
            note_import_options = None
            
        else:
            
            note_import_options = self._note_import_options_panel.GetValue()
            
        
        if self._tag_import_options_panel is None:
            
            tag_import_options = None
            
        else:
            
            tag_import_options = self._tag_import_options_panel.GetValue()
            
        
        return ( file_import_options, note_import_options, tag_import_options )
        
    
    def _UpdateFileImportOptionsTabName( self, is_default ):
        
        label = 'file'
        
        if is_default:
            
            label += ' (is default)'
            
        
        index = self._notebook.indexOf( self._file_import_options_panel )
        
        self._notebook.setTabText( index, label )
        
    
    def _UpdateNoteImportOptionsTabName( self, is_default ):
        
        label = 'note'
        
        if is_default:
            
            label += ' (is default)'
            
        
        index = self._notebook.indexOf( self._note_import_options_panel )
        
        self._notebook.setTabText( index, label )
        
    
    def _UpdateTagImportOptionsTabName( self, is_default ):
        
        label = 'tag'
        
        if is_default:
            
            label += ' (is default)'
            
        
        index = self._notebook.indexOf( self._tag_import_options_panel )
        
        self._notebook.setTabText( index, label )
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        file_import_options = file_import_options.Duplicate()
        
        if self._file_import_options_panel is not None:
            
            raise Exception( 'This Import Options Panel already has File Import Options set!' )
            
        
        self._file_import_options_panel = EditFileImportOptionsPanel( self._notebook, file_import_options, self._show_downloader_options, self._allow_default_selection )
        
        self._notebook.addTab( self._file_import_options_panel, 'file' )
        
        self._UpdateFileImportOptionsTabName( file_import_options.IsDefault() )
        
        self._file_import_options_panel.isDefaultChanged.connect( self._UpdateFileImportOptionsTabName )
        
    
    def SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        note_import_options = note_import_options.Duplicate()
        
        if self._note_import_options_panel is not None:
            
            raise Exception( 'This Import Options Panel already has Note Import Options set!' )
            
        
        self._note_import_options_panel = EditNoteImportOptionsPanel( self._notebook, note_import_options, self._allow_default_selection )
        
        self._notebook.addTab( self._note_import_options_panel, 'note' )
        
        self._UpdateNoteImportOptionsTabName( note_import_options.IsDefault() )
        
        self._note_import_options_panel.isDefaultChanged.connect( self._UpdateNoteImportOptionsTabName )
        
    
    def SetTagImportOptions( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        tag_import_options = tag_import_options.Duplicate()
        
        if self._tag_import_options_panel is not None:
            
            raise Exception( 'This Import Options Panel already has File Import Options set!' )
            
        
        self._tag_import_options_panel = EditTagImportOptionsPanel( self._notebook, tag_import_options, self._show_downloader_options, self._allow_default_selection )
        
        self._notebook.addTab( self._tag_import_options_panel, 'tag' )
        
        self._UpdateTagImportOptionsTabName( tag_import_options.IsDefault() )
        
        self._tag_import_options_panel.isDefaultChanged.connect( self._UpdateTagImportOptionsTabName )
        
    

class ImportOptionsButton( ClientGUICommon.ButtonWithMenuArrow ):
    
    importOptionsChanged = QC.Signal()
    fileImportOptionsChanged = QC.Signal( FileImportOptionsLegacy.FileImportOptionsLegacy )
    noteImportOptionsChanged = QC.Signal( NoteImportOptions.NoteImportOptions )
    tagImportOptionsChanged = QC.Signal( TagImportOptionsLegacy.TagImportOptionsLegacy )
    
    def __init__( self, parent, show_downloader_options: bool, allow_default_selection: bool ):
        
        action = QW.QAction()
        
        action.setText( 'import options' )
        action.setToolTip( ClientGUIFunctions.WrapToolTip( 'edit the different options for this importer' ) )
        
        action.triggered.connect( self._EditOptions )
        
        super().__init__( parent, action )
        
        self._show_downloader_options = show_downloader_options
        self._allow_default_selection = allow_default_selection
        
        self._file_import_options = None
        self._note_import_options = None
        self._tag_import_options = None
        
        self._SetLabelAndToolTip()
        
        self.fileImportOptionsChanged.connect( self.importOptionsChanged )
        self.noteImportOptionsChanged.connect( self.importOptionsChanged )
        self.tagImportOptionsChanged.connect( self.importOptionsChanged )
        
    
    def _CopyFileImportOptions( self ):
        
        json_string = self._file_import_options.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _CopyNoteImportOptions( self ):
        
        json_string = self._note_import_options.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _CopyTagImportOptions( self ):
        
        json_string = self._tag_import_options.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = EditImportOptionsPanel( dlg, self._show_downloader_options, self._allow_default_selection )
            
            if self._file_import_options is not None:
                
                panel.SetFileImportOptions( self._file_import_options )
                
            
            if self._tag_import_options is not None:
                
                panel.SetTagImportOptions( self._tag_import_options )
                
            
            if self._note_import_options is not None:
                
                panel.SetNoteImportOptions( self._note_import_options )
                
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                if self._file_import_options is not None:
                    
                    self._SetFileImportOptions( panel.GetFileImportOptions() )
                    
                
                if self._tag_import_options is not None:
                    
                    self._SetTagImportOptions( panel.GetTagImportOptions() )
                    
                
                if self._note_import_options is not None:
                    
                    self._SetNoteImportOptions( panel.GetNoteImportOptions() )
                    
                
            
        
    
    def _PasteFileImportOptions( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            file_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( file_import_options, FileImportOptionsLegacy.FileImportOptionsLegacy ):
                
                raise Exception( 'Not a File Import Options!' )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised File Import Options', e )
            
            return
            
        
        if file_import_options.IsDefault() and not self._allow_default_selection:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, the options you pasted were set as default, but this button needs something specific!' )
            
            return
            
        
        self._SetFileImportOptions( file_import_options )
        
    
    def _PasteNoteImportOptions( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            note_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( note_import_options, NoteImportOptions.NoteImportOptions ):
                
                raise Exception( 'Not a Note Import Options!' )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Note Import Options', e )
            
            return
            
        
        if note_import_options.IsDefault() and not self._allow_default_selection:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, the options you pasted were set as default, but this button needs something specific!' )
            
            return
            
        
        self._SetNoteImportOptions( note_import_options )
        
    
    def _PasteTagImportOptions( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            tag_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( tag_import_options, TagImportOptionsLegacy.TagImportOptionsLegacy ):
                
                raise Exception( 'Not a Tag Import Options!' )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Tag Import Options', e )
            
            return
            
        
        if tag_import_options.IsDefault() and not self._allow_default_selection:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, the options you pasted were set as default, but this button needs something specific!' )
            
            return
            
        
        self._SetTagImportOptions( tag_import_options )
        
    
    def _PopulateMenu( self, menu ):
        
        num_options_we_are_managing = len( [ options for options in [ self._file_import_options, self._tag_import_options, self._note_import_options ] if options is not None ] )
        
        make_submenus = num_options_we_are_managing > 1
        
        if self._file_import_options is not None:
            
            if make_submenus:
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                label = 'file import options'
                
                if self._file_import_options.IsDefault():
                    
                    label += ' (is default)'
                    
                
                ClientGUIMenus.AppendMenu( menu, submenu, label )
                
                menu_to_use = submenu
                
            else:
                
                menu_to_use = menu
                
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'copy to clipboard', 'Serialise this file import options and copy it to clipboard.', self._CopyFileImportOptions )
            
            ClientGUIMenus.AppendSeparator( menu_to_use )
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'paste from clipboard', 'Try to import serialised file import options from the clipboard.', self._PasteFileImportOptions )
            
            if self._allow_default_selection and not self._file_import_options.IsDefault():
                
                ClientGUIMenus.AppendSeparator( menu_to_use )
                
                ClientGUIMenus.AppendMenuItem( menu_to_use, 'set to default', 'Set this file import options to defer to the defaults.', self._SetFileImportOptionsDefault )
                
            
        
        if self._note_import_options is not None:
            
            if make_submenus:
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                label = 'note import options'
                
                if self._note_import_options.IsDefault():
                    
                    label += ' (is default)'
                    
                
                ClientGUIMenus.AppendMenu( menu, submenu, label )
                
                menu_to_use = submenu
                
            else:
                
                menu_to_use = menu
                
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'copy to clipboard', 'Serialise this note import options and copy it to clipboard.', self._CopyNoteImportOptions )
            
            ClientGUIMenus.AppendSeparator( menu_to_use )
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'paste from clipboard', 'Try to import serialised note import options from the clipboard.', self._PasteNoteImportOptions )
            
            if self._allow_default_selection and not self._note_import_options.IsDefault():
                
                ClientGUIMenus.AppendSeparator( menu_to_use )
                
                ClientGUIMenus.AppendMenuItem( menu_to_use, 'set to default', 'Set this note import options to defer to the defaults.', self._SetNoteImportOptionsDefault )
                
            
        
        if self._tag_import_options is not None:
            
            if make_submenus:
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                label = 'tag import options'
                
                if self._tag_import_options.IsDefault():
                    
                    label += ' (is default)'
                    
                
                ClientGUIMenus.AppendMenu( menu, submenu, label )
                
                menu_to_use = submenu
                
            else:
                
                menu_to_use = menu
                
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'copy to clipboard', 'Serialise this tag import options and copy it to clipboard.', self._CopyTagImportOptions )
            
            ClientGUIMenus.AppendSeparator( menu_to_use )
            
            ClientGUIMenus.AppendMenuItem( menu_to_use, 'paste from clipboard', 'Try to import serialised tag import options from the clipboard.', self._PasteTagImportOptions )
            
            if self._allow_default_selection and not self._tag_import_options.IsDefault():
                
                ClientGUIMenus.AppendSeparator( menu_to_use )
                
                ClientGUIMenus.AppendMenuItem( menu_to_use, 'set to default', 'Set this tag import options to defer to the defaults.', self._SetTagImportOptionsDefault )
                
            
        
    
    def _SetFileImportOptionsDefault( self ):
        
        if self._file_import_options is None:
            
            return
            
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        self._SetFileImportOptions( file_import_options )
        
    
    def _SetNoteImportOptionsDefault( self ):
        
        if self._note_import_options is None:
            
            return
            
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        note_import_options.SetIsDefault( True )
        
        self._SetNoteImportOptions( note_import_options )
        
    
    def _SetTagImportOptionsDefault( self ):
        
        if self._tag_import_options is None:
            
            return
            
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        self._SetTagImportOptions( tag_import_options )
        
    
    def _SetLabelAndToolTip( self ):
        
        all_are_default = True
        all_are_set = False
        
        summaries = []
        
        single_label = 'initialising'
        
        if self._file_import_options is not None:
            
            if self._file_import_options.IsDefault():
                
                all_are_set = False
                
            else:
                
                all_are_default = False
                
            
            single_label = 'file import options'
            
            summaries.append( self._file_import_options.GetSummary() )
            
        
        if self._tag_import_options is not None:
            
            if self._tag_import_options.IsDefault():
                
                all_are_set = False
                
            else:
                
                all_are_default = False
                
            
            single_label = 'tag import options'
            
            summaries.append( self._tag_import_options.GetSummary( self._show_downloader_options ) )
            
        
        if self._note_import_options is not None:
            
            if self._note_import_options.IsDefault():
                
                all_are_set = False
                
            else:
                
                all_are_default = False
                
            
            single_label = 'note import options'
            
            summaries.append( self._note_import_options.GetSummary() )
            
        
        if len( summaries ) > 1:
            
            label = 'import options'
            
            if self._allow_default_selection:
                
                if all_are_default:
                    
                    label = f'{label} (all default)'
                    
                elif all_are_set:
                    
                    label = f'{label} (all set)'
                    
                else:
                    
                    label = f'{label} (some set)'
                    
                
            
        else:
            
            label = single_label
            
            if all_are_default:
                
                label = f'{label} (default)'
                
            else:
                
                label = HydrusText.ElideText( f'{label} ({summaries[0]})', 48 )
                
            
        
        my_action = self.defaultAction()
        
        my_action.setText( label )
        
        s = '\n' * 2
        
        summary = s.join( summaries )
        
        my_action.setToolTip( ClientGUIFunctions.WrapToolTip( summary ) )
        
    
    def _SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        self._file_import_options = file_import_options
        
        self._SetLabelAndToolTip()
        
        self.fileImportOptionsChanged.emit( self._file_import_options )
        
    
    def _SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._note_import_options = note_import_options
        
        self._SetLabelAndToolTip()
        
        self.noteImportOptionsChanged.emit( self._note_import_options )
        
    
    def _SetTagImportOptions( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        self._tag_import_options = tag_import_options
        
        self._SetLabelAndToolTip()
        
        self.tagImportOptionsChanged.emit( self._tag_import_options )
        
    
    def GetFileImportOptions( self ) -> FileImportOptionsLegacy.FileImportOptionsLegacy:
        
        if self._file_import_options is None:
            
            raise HydrusExceptions.DataMissing( 'This Import Options Button does not manage a File Import Options!' )
            
        
        return self._file_import_options
        
    
    def GetNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        if self._note_import_options is None:
            
            raise HydrusExceptions.DataMissing( 'This Import Options Button does not manage a Note Import Options!' )
            
        
        return self._note_import_options
        
    
    def GetTagImportOptions( self ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        if self._tag_import_options is None:
            
            raise HydrusExceptions.DataMissing( 'This Import Options Button does not manage a Tag Import Options!' )
            
        
        return self._tag_import_options
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        self._SetFileImportOptions( file_import_options )
        
    
    def SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._SetNoteImportOptions( note_import_options )
        
    
    def SetTagImportOptions( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        self._SetTagImportOptions( tag_import_options )
        
    
