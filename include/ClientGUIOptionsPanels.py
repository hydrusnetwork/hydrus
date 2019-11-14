from . import ClientConstants as CC
from . import ClientCaches
from . import ClientDefaults
from . import ClientGUIDialogs
from . import ClientImporting
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
import os
from . import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

class OptionsPanel( QW.QWidget ):
    
    def GetOptions( self ): raise NotImplementedError()
    
    def SetOptions( self, options ): raise NotImplementedError()
    
    def GetValue( self ): raise NotImplementedError()
    
    def SetValue( self, info ): raise NotImplementedError()
    
class OptionsPanelMimes( OptionsPanel ):
    
    def __init__( self, parent, selectable_mimes ):
        
        OptionsPanel.__init__( self, parent )
        
        self._mimes_to_checkboxes = {}
        self._mime_groups_to_checkboxes = {}
        self._mime_groups_to_values = {}
        
        mime_groups = [ HC.APPLICATIONS, HC.AUDIO, HC.IMAGES, HC.VIDEO ]
        
        mime_groups_to_mimes = collections.defaultdict( list )
        
        for mime in selectable_mimes:
            
            for mime_group in mime_groups:
                
                if mime in mime_group:
                    
                    mime_groups_to_mimes[ mime_group ].append( mime )
                    
                    break
                    
                
            
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        for mime_group in mime_groups:
            
            mimes = mime_groups_to_mimes[ mime_group ]
            
            mg_checkbox = QW.QCheckBox( HC.mime_string_lookup[mime_group], self )
            mg_checkbox.clicked.connect( self.EventMimeGroupCheckbox )
            
            self._mime_groups_to_checkboxes[ mime_group ] = mg_checkbox
            self._mime_groups_to_values[ mime_group ] = mg_checkbox.isChecked()
            
            QP.AddToLayout( gridbox, mg_checkbox, CC.FLAGS_VCENTER )
            
            vbox = QP.VBoxLayout()
            
            for mime in mimes:
                
                m_checkbox = QW.QCheckBox( HC.mime_string_lookup[mime], self )
                m_checkbox.clicked.connect( self.EventMimeCheckbox )
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                QP.AddToLayout( vbox, m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( gridbox, vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.setLayout( gridbox )
        
    
    def _UpdateMimeGroupCheckboxes( self ):
        
        for ( mime_group, mg_checkbox ) in list(self._mime_groups_to_checkboxes.items()):
            
            respective_checkbox_values = [m_checkbox.isChecked() for (mime, m_checkbox) in list( self._mimes_to_checkboxes.items() ) if mime in mime_group]
            
            all_true = False not in respective_checkbox_values
            
            mg_checkbox.setChecked( all_true )
            self._mime_groups_to_values[ mime_group ] = all_true
            
        
    
    def EventMimeCheckbox( self ):
        
        self._UpdateMimeGroupCheckboxes()
        
    
    def EventMimeGroupCheckbox( self ):
        
        # Obsolote comment from before the Qt port:
        # this is a commandevent, which won't give up the checkbox object, so we have to do some jiggery pokery
        
        for ( mime_group, mg_checkbox ) in list(self._mime_groups_to_checkboxes.items()):
            
            expected_value = self._mime_groups_to_values[ mime_group ]
            actual_value = mg_checkbox.isChecked()
            
            if actual_value != expected_value:
                
                for ( mime, m_checkbox ) in list(self._mimes_to_checkboxes.items()):
                    
                    if mime in mime_group:
                        
                        m_checkbox.setChecked( actual_value )
                        
                    
                
                self._mime_groups_to_values[ mime_group ] = actual_value
                
            
        
    
    def GetValue( self ):
        
        mimes = tuple( [mime for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()) if checkbox.isChecked() == True] )
        
        return mimes
        
    
    def SetValue( self, mimes ):
        
        for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()):
            
            if mime in mimes:
                
                checkbox.setChecked( True )
                
            else:
                
                checkbox.setChecked( False )
                
            
        
        self._UpdateMimeGroupCheckboxes()
        
    
