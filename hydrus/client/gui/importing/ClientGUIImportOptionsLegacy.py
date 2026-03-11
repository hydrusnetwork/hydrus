from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImportOptionsPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy

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
            
        
        self._file_import_options_panel = ClientGUIImportOptionsPanels.EditFileImportOptionsLegacyPanel( self._notebook, file_import_options, self._show_downloader_options, self._allow_default_selection )
        
        self._notebook.addTab( self._file_import_options_panel, 'file' )
        
        self._UpdateFileImportOptionsTabName( file_import_options.IsDefault() )
        
        self._file_import_options_panel.isDefaultChanged.connect( self._UpdateFileImportOptionsTabName )
        
    
    def SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        note_import_options = note_import_options.Duplicate()
        
        if self._note_import_options_panel is not None:
            
            raise Exception( 'This Import Options Panel already has Note Import Options set!' )
            
        
        self._note_import_options_panel = ClientGUIImportOptionsPanels.EditNoteImportOptionsPanel( self._notebook, note_import_options, self._allow_default_selection )
        
        self._notebook.addTab( self._note_import_options_panel, 'note' )
        
        self._UpdateNoteImportOptionsTabName( note_import_options.IsDefault() )
        
        self._note_import_options_panel.isDefaultChanged.connect( self._UpdateNoteImportOptionsTabName )
        
    
    def SetTagImportOptions( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        tag_import_options = tag_import_options.Duplicate()
        
        if self._tag_import_options_panel is not None:
            
            raise Exception( 'This Import Options Panel already has File Import Options set!' )
            
        
        self._tag_import_options_panel = ClientGUIImportOptionsPanels.EditTagImportOptionsLegacyPanel( self._notebook, tag_import_options, self._show_downloader_options, self._allow_default_selection )
        
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
        
    
