import ClientConstants as CC
import ClientGUICommon
import ClientGUIScrolledPanels
import ClientParsing
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusSerialisable
import os
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
        
        if isinstance( self._payload_obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            self._title.SetValue( self._payload_obj.GetName() )
            
        
        self._Update()
        
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
        
    
    def _Update( self ):
        
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
            
        
    
    def EventChanged( self, event ):
        
        self._Update()
        
    
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
        
        HG.client_controller.CallLaterWXSafe( self._export, 2.0, self._export.SetLabelText, 'export' )
        
    
class PngsExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_objs ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._payload_objs = payload_objs
        
        self._directory_picker = wx.DirPickerCtrl( self )
        self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventChanged )
        
        self._width = wx.SpinCtrl( self, min = 100, max = 4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        self._width.SetValue( 512 )
        
        self._Update()
        
        #
        
        rows = []
        
        rows.append( ( 'export path: ', self._directory_picker ) )
        rows.append( ( 'png width: ', self._width ) )
        rows.append( ( '', self._export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
    
    def _Update( self ):
        
        problems = []
        
        path = self._directory_picker.GetPath()
        
        if path == '' or path is None:
            
            problems.append( 'select a path' )
            
        
        if len( problems ) == 0:
            
            self._export.SetLabelText( 'export' )
            
            self._export.Enable()
            
        else:
            
            self._export.SetLabelText( ' and '.join( problems ) )
            
            self._export.Disable()
            
        
    
    def EventChanged( self, event ):
        
        self._Update()
        
    
    def Export( self ):
        
        width = self._width.GetValue()
        
        directory = HydrusData.ToUnicode( self._directory_picker.GetPath() )
        
        for obj in self._payload_objs:
            
            ( payload_description, payload_string ) = ClientSerialisable.GetPayloadDescriptionAndString( obj )
            
            title = obj.GetName()
            text = ''
            path = os.path.join( directory, title )
            
            if not path.endswith( '.png' ):
                
                path += '.png'
                
            
            ClientSerialisable.DumpToPng( width, payload_string, title, payload_description, text, path )
            
        
        self._export.SetLabelText( 'done!' )
        
        HG.client_controller.CallLaterWXSafe( self._export, 2.0, self._export.SetLabelText, 'export' )
        
    
