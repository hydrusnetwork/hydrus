import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.importing.options import ImportOptionsContainer
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImportOptionsPanels
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options.FileFilteringImportOptions import FileFilteringImportOptions
from hydrus.client.importing.options.LocationImportOptions import LocationImportOptions
from hydrus.client.importing.options.NoteImportOptions import NoteImportOptions
from hydrus.client.importing.options.PrefetchImportOptions import PrefetchImportOptions
from hydrus.client.importing.options.PresentationImportOptions import PresentationImportOptions
from hydrus.client.importing.options.TagFilteringImportOptions import TagFilteringImportOptions
from hydrus.client.importing.options.TagImportOptions import TagImportOptions

class EditImportOptionsContainerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, import_options_container_manager: ImportOptionsContainer.ImportOptionsManager, import_options_container: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, url_class_key: bytes | None = None ):
        
        super().__init__( parent )
        
        self._import_options_container_manager = import_options_container_manager
        self._import_options_caller_type = import_options_caller_type
        self._url_class_key = url_class_key
        
        # TODO: a help button that either spams out a little help in a dialog or points to a proper html document
        # TODO: that help should say, given our caller_type, what the currend default cascade is! perhaps 'preference stack' can be pulled out of the manager to help with this
        # TODO: a favourites thing that can overwrite what we have and do save too
        
        self._listbook = ClientGUIListBook.ListBook( self, list_chars_height = 7, orientation = QC.Qt.Orientation.Vertical )
        
        #
        
        default_import_options_container = import_options_container_manager.GenerateFullImportOptionsContainer( ImportOptionsContainer.ImportOptionsContainer(), self._import_options_caller_type, url_class_key = self._url_class_key )
        
        for import_options_type in ImportOptionsContainer.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
            
            panel = DefaultableImportOptionsPanel(
                self._listbook,
                self._import_options_container_manager,
                import_options_type,
                import_options_container,
                default_import_options_container,
                self._import_options_caller_type,
                url_class_key = self._url_class_key
            )
            
            panel.valueChanged.connect( self._UpdateLabels )
            
            self._listbook.addTab( panel, ImportOptionsContainer.import_options_type_str_lookup[ import_options_type ] )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _UpdateLabels( self ):
        
        for ( i, page ) in enumerate( self._listbook.GetPages() ):
            
            page = typing.cast( DefaultableImportOptionsPanel, page )
            
            label = page.GetLabel()
            
            self._listbook.setTabText( i, label )
            
        
    
    def GetValue( self ) -> ImportOptionsContainer.ImportOptionsContainer:
        
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        for page in self._listbook.GetPages():
            
            page = typing.cast( DefaultableImportOptionsPanel, page )
            
            if not page.IsDefault():
                
                import_options_container.SetImportOptions( page.GetImportOptionsType(), page.GetValue() )
                
            
        
        return import_options_container
        
    

class DefaultableImportOptionsPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, import_options_container_manager: ImportOptionsContainer.ImportOptionsManager, import_options_type: int, import_options_container: ImportOptionsContainer.ImportOptionsContainer, default_import_options_container: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, url_class_key: bytes | None = None ):
        
        super().__init__( parent )
        
        self._import_options_container_manager = import_options_container_manager
        self._import_options_type = import_options_type
        self._default_import_options_container = default_import_options_container
        self._import_options_caller_type = import_options_caller_type
        self._url_class_key = url_class_key
        
        if import_options_container.HasImportOptions( self._import_options_type ):
            
            self._is_default = False
            
            import_options = import_options_container.GetImportOptions( self._import_options_type )
            
        else:
            
            self._is_default = True
            
            import_options = self._default_import_options_container.GetImportOptions( self._import_options_type )
            
        
        #
        
        self._use_default_dropdown = ClientGUICommon.BetterChoice( self )
        
        self._use_default_dropdown.addItem( f'use the default import options ({self._default_import_options_container.GetSourceLabel( self._import_options_type )})', True )
        self._use_default_dropdown.addItem( 'set import options here', False )
        
        tt = 'Normally, the client will refer to the defaults (as set under "network->downloaders->manage default import options") for the appropriate tag import options at the time of import.'
        tt += '\n' * 2
        tt += 'It is easier to work this way, since you can change a single default setting and update all current and future downloaders that refer to those defaults, whereas having specific options for every subscription or downloader means you have to update every single one just to make a little change somewhere.'
        tt += '\n' * 2
        tt += 'But if you are doing a one-time import that has some unusual tag rules, set them here.'
        
        self._use_default_dropdown.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        # TODO: favourites button to overwrite from a favourites that has this specific type
        
        if import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL and not self._is_default:
            
            self._use_default_dropdown.setVisible( False )
            
        
        # TODO: it would be nice if all these had a valueChanged that we could pipe up for nice label updates
        
        if self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PREFETCH:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditPrefetchImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_FILE_FILTERING:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditFileFilteringImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAG_FILTERING:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditTagFilteringImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_LOCATION_IMPORT_OPTIONS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditLocationImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAG_IMPORT_OPTIONS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditTagImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_NOTE_IMPORT_OPTIONS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditNoteImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PRESENTATION_IMPORT_OPTIONS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditPresentationImportOptions( self, import_options )
            
        else:
            
            raise Exception( 'Unknown import options type!' )
            
        
        self._use_default_dropdown.currentIndexChanged.connect( self.valueChanged )
        
    
    def GetImportOptionsType( self ) -> int:
        
        return self._import_options_type
        
    
    def GetLabel( self ) -> str:
        
        label = ImportOptionsContainer.import_options_type_str_lookup[ self._import_options_type ] + ': '
        
        if self._is_default:
            
            default_label = self._default_import_options_container.GetSourceLabel( self._import_options_type )
            
            label += f'default ({default_label})'
            
        else:
            
            import_options = self.GetValue()
            
            label = import_options.GetSummary()
            
        
        return label
        
    
    def GetValue( self ) -> PrefetchImportOptions | FileFilteringImportOptions | TagFilteringImportOptions | LocationImportOptions | TagImportOptions | NoteImportOptions | PresentationImportOptions:
        
        return self._options_panel.GetValue()
        
    
    def SetValue( self, import_options: PrefetchImportOptions | FileFilteringImportOptions | TagFilteringImportOptions | LocationImportOptions | TagImportOptions | NoteImportOptions | PresentationImportOptions ):
        
        self._options_panel.SetValue( import_options )
        
    
    def IsDefault( self ) -> bool:
        
        return self._is_default
        
    
