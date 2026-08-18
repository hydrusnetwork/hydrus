from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class NotesPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._start_note_editing_at_end = QW.QCheckBox( self )
        self._start_note_editing_at_end.setToolTip( ClientGUIFunctions.WrapToolTip( 'Otherwise, start the text cursor at the start of the document.' ) )
        
        self._copy_notes_quick_click_only_copies_text = QW.QCheckBox( self )
        self._copy_notes_quick_click_only_copies_text.setToolTip( ClientGUIFunctions.WrapToolTip( 'Otherwise, copy title and text.' ) )
        
        #
        
        self._start_note_editing_at_end.setChecked( self._new_options.GetBoolean( 'start_note_editing_at_end' ) )
        self._copy_notes_quick_click_only_copies_text.setChecked( self._new_options.GetBoolean( 'copy_notes_quick_click_only_copies_text' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Start editing notes with the text cursor at the end of the document: ', self._start_note_editing_at_end ) )
        rows.append( ( 'When middle-clicking a note hover, only copy the text: ', self._copy_notes_quick_click_only_copies_text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'start_note_editing_at_end', self._start_note_editing_at_end.isChecked() )
        self._new_options.SetBoolean( 'copy_notes_quick_click_only_copies_text', self._copy_notes_quick_click_only_copies_text.isChecked() )
        
    
