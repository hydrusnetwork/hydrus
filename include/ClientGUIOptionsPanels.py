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
        
        self._selectable_mimes = set( selectable_mimes )
        
        self._mimes_to_checkboxes = {}
        self._mime_groups_to_checkboxes = {}
        self._mime_groups_to_values = {}
        
        mime_groups = []
        
        mime_groups.append( ( HC.APPLICATIONS, HC.GENERAL_APPLICATION ) )
        mime_groups.append( ( HC.AUDIO, HC.GENERAL_AUDIO ) )
        mime_groups.append( ( HC.IMAGES, HC.GENERAL_IMAGE ) )
        mime_groups.append( ( HC.VIDEO, HC.GENERAL_VIDEO ) )
        
        mime_groups_to_mimes = collections.defaultdict( list )
        
        for mime in self._selectable_mimes:
            
            for ( mime_group, mime_group_type ) in mime_groups:
                
                if mime in mime_group:
                    
                    mime_groups_to_mimes[ mime_group ].append( mime )
                    
                    break
                    
                
            
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        for ( mime_group, mime_group_type ) in mime_groups:
            
            mimes = mime_groups_to_mimes[ mime_group ]
            
            mg_checkbox = QW.QCheckBox( HC.mime_string_lookup[ mime_group_type ], self )
            mg_checkbox.clicked.connect( self.EventMimeGroupCheckbox )
            
            self._mime_groups_to_checkboxes[ mime_group ] = mg_checkbox
            self._mime_groups_to_values[ mime_group ] = mg_checkbox.isChecked()
            
            QP.AddToLayout( gridbox, mg_checkbox, CC.FLAGS_VCENTER )
            
            vbox = QP.VBoxLayout()
            
            for mime in mimes:
                
                m_checkbox = QW.QCheckBox( HC.mime_string_lookup[ mime ], self )
                m_checkbox.clicked.connect( self.EventMimeCheckbox )
                
                #m_checkbox.hide()
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                QP.AddToLayout( vbox, m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( gridbox, vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.setLayout( gridbox )
        
        self._HideShowSubCheckboxes()
        
    
    def _HideShowSubCheckboxes( self ):
        
        pass
        
        # this is insufficient. we need to have mime groups done by three-state checkboxes or something.
        # and it'd be nice to have a border around groups or something.
        
        '''
        for ( mime_group, all_true ) in self._mime_groups_to_values.items():
            
            should_show = not all_true
            
            for mime in mime_group:
                
                if mime not in self._selectable_mimes:
                    
                    continue
                    
                
                self._mimes_to_checkboxes[ mime ].setVisible( should_show )
                
            
        '''
    
    def _UpdateMimeGroupCheckboxes( self ):
        
        for ( mime_group, mg_checkbox ) in self._mime_groups_to_checkboxes.items():
            
            respective_checkbox_values = [ m_checkbox.isChecked() for ( mime, m_checkbox ) in list( self._mimes_to_checkboxes.items() ) if mime in mime_group ]
            
            all_true = False not in respective_checkbox_values
            
            mg_checkbox.setChecked( all_true )
            self._mime_groups_to_values[ mime_group ] = all_true
            
        
        self._HideShowSubCheckboxes()
        
    
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
                
            
        
        self._HideShowSubCheckboxes()
        
    
    def GetValue( self ):
        
        mimes = tuple( [ mime for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()) if checkbox.isChecked() == True ] )
        
        return mimes
        
    
    def SetValue( self, mimes ):
        
        for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()):
            
            if mime in mimes:
                
                checkbox.setChecked( True )
                
            else:
                
                checkbox.setChecked( False )
                
            
        
        self._UpdateMimeGroupCheckboxes()
        
    
