import ClientConstants as CC
import ClientGUICommon
import ClientGUIScrolledPanelsEdit
import ClientGUITopLevelWindows
import HydrusConstants as HC
import wx

class ImportOptionsFilesButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, file_import_options, update_callable = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'file import options', self._EditOptions )
        
        self._file_import_options = file_import_options
        self._update_callable = update_callable
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit file import options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditImportOptionsFiles( dlg, self._file_import_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                file_import_options = panel.GetValue()
                
                self._SetValue( file_import_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.SetToolTipString( self._file_import_options.GetSummary() )
        
    
    def _SetValue( self, file_import_options ):
        
        self._file_import_options = file_import_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._file_import_options )
            
        
    
    def GetValue( self ):
        
        return self._file_import_options
        
    
    def SetValue( self, file_import_options ):
        
        self._SetValue( file_import_options )
        
    
