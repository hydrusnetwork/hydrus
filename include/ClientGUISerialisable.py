import ClientConstants as CC
import ClientGUICommon
import ClientGUIScrolledPanels
import ClientParsing
import ClientSerialisable
import HydrusConstants as HC
import HydrusData
import wx

class PngExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_obj ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._payload_obj = payload_obj
        
        self._filepicker = wx.FilePickerCtrl( self, style = wx.FLP_SAVE, wildcard = 'PNG (*.png)|*.png' )
        self._filepicker.Bind( wx.EVT_FILEPICKER_CHANGED, self.EventChanged )
        
        self._title = wx.TextCtrl( self )
        self._title.Bind( wx.EVT_TEXT, self.EventChanged )
        
        self._payload_description = wx.TextCtrl( self )
        
        self._text = wx.TextCtrl( self )
        
        self._width = wx.SpinCtrl( self, min = 100, max = 4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        ( payload_description, payload_string ) = ClientSerialisable.GetPayloadDescriptionAndString( self._payload_obj )
        
        self._payload_description.SetValue( payload_description )
        
        self._payload_description.Disable()
        
        self._width.SetValue( 512 )
        
        self.EventChanged( None )
        
        #
        
        rows = []
        
        rows.append( ( 'export path: ', self._filepicker ) )
        rows.append( ( 'title: ', self._title ) )
        rows.append( ( 'payload description: ', self._payload_description ) )
        rows.append( ( 'your description (optional): ', self._text ) )
        rows.append( ( 'png width: ', self._width ) )
        rows.append( ( '', self._export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
    
    def EventChanged( self, event ):
        
        problems = []
        
        path = self._filepicker.GetPath()
        
        if path == '' or path is None:
            
            problems.append( 'select a path' )
            
        
        if self._title.GetValue() == '':
            
            problems.append( 'set a title' )
            
        
        if len( problems ) == 0:
            
            self._export.SetLabelText( 'export' )
            
            self._export.Enable()
            
        else:
            
            self._export.SetLabelText( ' and '.join( problems ) )
            
            self._export.Disable()
            
        
    
    def Export( self ):
        
        width = self._width.GetValue()
        
        ( payload_description, payload_string ) = ClientSerialisable.GetPayloadDescriptionAndString( self._payload_obj )
        
        title = self._title.GetValue()
        text = self._text.GetValue()
        path = HydrusData.ToUnicode( self._filepicker.GetPath() )
        
        if not path.endswith( '.png' ):
            
            path += '.png'
            
        
        ClientSerialisable.DumpToPng( width, payload_string, title, payload_description, text, path )
        
        self._export.SetLabelText( 'done!' )
        
        wx.CallLater( 2000, self._export.SetLabelText, 'export' )
        
    
