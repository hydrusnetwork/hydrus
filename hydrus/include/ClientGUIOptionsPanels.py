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
import wx
import wx.lib.masked.timectrl
from . import HydrusGlobals as HG

class OptionsPanel( wx.Panel ):
    
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
                    
                
            
        
        gridbox = wx.FlexGridSizer( 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for mime_group in mime_groups:
            
            mimes = mime_groups_to_mimes[ mime_group ]
            
            mg_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime_group ] )
            mg_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeGroupCheckbox )
            
            self._mime_groups_to_checkboxes[ mime_group ] = mg_checkbox
            self._mime_groups_to_values[ mime_group ] = mg_checkbox.GetValue()
            
            gridbox.Add( mg_checkbox, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for mime in mimes:
                
                m_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime ] )
                m_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeCheckbox )
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                vbox.Add( m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            gridbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.SetSizer( gridbox )
        
    
    def _UpdateMimeGroupCheckboxes( self ):
        
        for ( mime_group, mg_checkbox ) in list(self._mime_groups_to_checkboxes.items()):
            
            respective_checkbox_values = [ m_checkbox.GetValue() for ( mime, m_checkbox ) in list(self._mimes_to_checkboxes.items()) if mime in mime_group ]
            
            all_true = False not in respective_checkbox_values
            
            mg_checkbox.SetValue( all_true )
            self._mime_groups_to_values[ mime_group ] = all_true
            
        
    
    def EventMimeCheckbox( self, event ):
        
        self._UpdateMimeGroupCheckboxes()
        
    
    def EventMimeGroupCheckbox( self, event ):
        
        # this is a commandevent, which won't give up the checkbox object, so we have to do some jiggery pokery
        
        for ( mime_group, mg_checkbox ) in list(self._mime_groups_to_checkboxes.items()):
            
            expected_value = self._mime_groups_to_values[ mime_group ]
            actual_value = mg_checkbox.GetValue()
            
            if actual_value != expected_value:
                
                for ( mime, m_checkbox ) in list(self._mimes_to_checkboxes.items()):
                    
                    if mime in mime_group:
                        
                        m_checkbox.SetValue( actual_value )
                        
                    
                
                self._mime_groups_to_values[ mime_group ] = actual_value
                
            
        
    
    def GetValue( self ):
        
        mimes = tuple( [ mime for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()) if checkbox.GetValue() == True ] )
        
        return mimes
        
    
    def SetValue( self, mimes ):
        
        for ( mime, checkbox ) in list(self._mimes_to_checkboxes.items()):
            
            if mime in mimes:
                
                checkbox.SetValue( True )
                
            else:
                
                checkbox.SetValue( False )
                
            
        
        self._UpdateMimeGroupCheckboxes()
        
    
