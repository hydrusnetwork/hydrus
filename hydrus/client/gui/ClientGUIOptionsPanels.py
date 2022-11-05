from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class OptionsPanel( QW.QWidget ):
    
    def GetValue( self ): raise NotImplementedError()
    
    def SetValue( self, info ): raise NotImplementedError()
    
class OptionsPanelMimes( OptionsPanel ):
    
    BUTTON_CURRENTLY_HIDDEN = '\u25B6'
    BUTTON_CURRENTLY_SHOWING = '\u25BC'
    
    def __init__( self, parent, selectable_mimes ):
        
        OptionsPanel.__init__( self, parent )
        
        self._selectable_mimes = set( selectable_mimes )
        
        self._mimes_to_checkboxes = {}
        self._general_mime_types_to_checkboxes = {}
        self._general_mime_types_to_buttons = {}
        
        general_mime_types = []
        
        general_mime_types.append( HC.GENERAL_IMAGE )
        general_mime_types.append( HC.GENERAL_ANIMATION )
        general_mime_types.append( HC.GENERAL_VIDEO )
        general_mime_types.append( HC.GENERAL_AUDIO )
        general_mime_types.append( HC.GENERAL_APPLICATION )
        
        gridbox = QP.GridLayout( cols = 3 )
        
        gridbox.setColumnStretch( 2, 1 )
        
        for general_mime_type in general_mime_types:
            
            mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
            
            if len( mimes_in_type ) == 0:
                
                continue
                
            
            general_mime_checkbox = QW.QCheckBox( HC.mime_string_lookup[ general_mime_type ], self )
            general_mime_checkbox.clicked.connect( self.EventMimeGroupCheckbox )
            
            self._general_mime_types_to_checkboxes[ general_mime_type ] = general_mime_checkbox
            
            QP.AddToLayout( gridbox, general_mime_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            
            show_hide_button = ClientGUICommon.BetterButton( self, self.BUTTON_CURRENTLY_HIDDEN, self._ButtonShowHide, general_mime_type )
            
            max_width = ClientGUIFunctions.ConvertTextToPixelWidth( show_hide_button, 5 )
            
            show_hide_button.setMaximumWidth( max_width )
            
            self._general_mime_types_to_buttons[ general_mime_type ] = show_hide_button
            
            QP.AddToLayout( gridbox, show_hide_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            for mime in mimes_in_type:
                
                m_checkbox = QW.QCheckBox( HC.mime_string_lookup[ mime ], self )
                m_checkbox.clicked.connect( self.EventMimeCheckbox )
                
                m_checkbox.setVisible( False )
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                QP.AddToLayout( vbox, m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( gridbox, vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.setLayout( gridbox )
        
    
    def _DoInitialHideShow( self ):
        
        for ( general_mime_type, general_mime_checkbox ) in list( self._general_mime_types_to_checkboxes.items() ):
            
            mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
            
            should_show = general_mime_checkbox.checkState() == QC.Qt.PartiallyChecked
            
            if not should_show:
                
                self._ButtonShowHide( general_mime_type )
                
            
        
    
    def _GetMimesForGeneralMimeType( self, general_mime_type ):
        
        mimes_in_type = HC.general_mimetypes_to_mime_groups[ general_mime_type ]
        
        mimes_in_type = [ mime for mime in mimes_in_type if mime in self._selectable_mimes ]
        
        return mimes_in_type
        
    
    def _ButtonShowHide( self, general_mime_type ):
        
        button = self._general_mime_types_to_buttons[ general_mime_type ]
        
        mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
        
        should_show = button.text() == self.BUTTON_CURRENTLY_HIDDEN
        
        for mime in mimes_in_type:
            
            self._mimes_to_checkboxes[ mime ].setVisible( should_show )
            
        
        if should_show:
            
            button.setText( self.BUTTON_CURRENTLY_SHOWING )
            
        else:
            
            button.setText( self.BUTTON_CURRENTLY_HIDDEN )
            
        
    
    def _UpdateMimeGroupCheckboxes( self ):
        
        for ( general_mime_type, general_mime_checkbox ) in self._general_mime_types_to_checkboxes.items():
            
            mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
            
            all_checkbox_values = { self._mimes_to_checkboxes[ mime ].isChecked() for mime in mimes_in_type }
            
            all_false = True not in all_checkbox_values
            all_true = False not in all_checkbox_values
            
            if all_false:
                
                check_state = QC.Qt.Unchecked
                
            elif all_true:
                
                check_state = QC.Qt.Checked
                
            else:
                
                check_state = QC.Qt.PartiallyChecked
                
            
            if check_state == QC.Qt.PartiallyChecked:
                
                general_mime_checkbox.setTristate( True )
                
            
            general_mime_checkbox.setCheckState( check_state )
            
            if check_state != QC.Qt.PartiallyChecked:
                
                general_mime_checkbox.setTristate( False )
                
            
        
    
    def EventMimeCheckbox( self ):
        
        self._UpdateMimeGroupCheckboxes()
        
    
    def EventMimeGroupCheckbox( self ):
        
        for ( general_mime_type, general_mime_checkbox ) in list( self._general_mime_types_to_checkboxes.items() ):
            
            check_state = general_mime_checkbox.checkState()
            
            mime_check_state = None
            
            if check_state == QC.Qt.Unchecked:
                
                mime_check_state = False
                
            elif check_state == QC.Qt.Checked:
                
                mime_check_state = True
                
            
            if mime_check_state is not None:
                
                general_mime_checkbox.setTristate( False )
                
                mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
                
                for mime in mimes_in_type:
                    
                    self._mimes_to_checkboxes[ mime ].setChecked( mime_check_state )
                    
                
            
        
    
    def GetValue( self ):
        
        mimes = tuple( [ mime for ( mime, checkbox ) in list( self._mimes_to_checkboxes.items() ) if checkbox.isChecked() ] )
        
        return mimes
        
    
    def SetValue( self, checked_mimes ):
        
        checked_mimes = ClientSearch.ConvertSummaryFiletypesToSpecific( checked_mimes, only_searchable = False )
        
        for ( mime, checkbox ) in self._mimes_to_checkboxes.items():
            
            if mime in checked_mimes:
                
                checkbox.setChecked( True )
                
            else:
                
                checkbox.setChecked( False )
                
            
        
        self._UpdateMimeGroupCheckboxes()
        
        #self._DoInitialHideShow()
        
    
