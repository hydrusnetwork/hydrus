from . import ClientConstants as CC
from . import ClientGUICommon
from . import ClientGUITopLevelWindows
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
import os
import wx

class ShowKeys( ClientGUITopLevelWindows.Frame ):
    
    def __init__( self, key_type, keys ):
        
        if key_type == 'registration': title = 'Registration Keys'
        elif key_type == 'access': title = 'Access Keys'
        
        # give it no parent, so this doesn't close when the dialog is closed!
        ClientGUITopLevelWindows.Frame.__init__( self, None, HG.client_controller.PrepStringForDisplay( title ), float_on_parent = False )
        
        self._key_type = key_type
        self._keys = keys
        
        #
        
        self._text_ctrl = ClientGUICommon.SaneMultilineTextCtrl( self, style = wx.TE_READONLY | wx.TE_DONTWRAP )
        
        self._save_to_file = wx.Button( self, label = 'save to file' )
        self._save_to_file.Bind( wx.EVT_BUTTON, self.EventSaveToFile )
        
        self._done = wx.Button( self, label = 'done' )
        self._done.Bind( wx.EVT_BUTTON, self.EventDone )
        
        #
        
        if key_type == 'registration': prepend = 'r'
        else: prepend = ''
        
        self._text = os.linesep.join( [ prepend + key.hex() for key in self._keys ] )
        
        self._text_ctrl.SetValue( self._text )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._text_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._save_to_file, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._done, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 500: x = 500
        if y < 200: y = 200
        
        self.SetInitialSize( ( x, y ) )
        
        self.Show( True )
        
    
    def EventDone( self, event ):
        
        self.Close()
        
    
    def EventSaveToFile( self, event ):
        
        filename = 'keys.txt'
        
        with wx.FileDialog( self, style=wx.FD_SAVE, defaultFile = filename ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                with open( path, 'w', encoding = 'utf-8' ) as f:
                    
                    f.write( self._text )
                    
                
            
        
    
