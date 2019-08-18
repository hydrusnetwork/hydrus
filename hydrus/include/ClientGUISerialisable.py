from . import ClientConstants as CC
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import ClientGUIScrolledPanels
from . import ClientParsing
from . import ClientSerialisable
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
import os
import wx

class PngExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_obj, title = None, description = None, payload_description = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._payload_obj = payload_obj
        
        self._filepicker = wx.FilePickerCtrl( self, style = wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL, wildcard = 'PNG (*.png)|*.png' )
        
        flp_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._filepicker, 64 )
        
        self._filepicker.SetMinSize( ( flp_width, -1 ) )
        
        self._title = wx.TextCtrl( self )
        
        self._payload_description = wx.TextCtrl( self )
        
        self._text = wx.TextCtrl( self )
        
        self._width = wx.SpinCtrl( self, min = 100, max = 4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        if payload_description is None:
            
            ( payload_description, payload_bytes ) = ClientSerialisable.GetPayloadDescriptionAndBytes( self._payload_obj )
            
        else:
            
            payload_bytes = ClientSerialisable.GetPayloadBytes( self._payload_obj )
            
            payload_description += ' - ' + HydrusData.ToHumanBytes( len( payload_bytes ) )
            
        
        self._payload_description.SetValue( payload_description )
        
        self._payload_description.Disable()
        
        self._width.SetValue( 512 )
        
        last_png_export_dir = HG.client_controller.new_options.GetNoneableString( 'last_png_export_dir' )
        
        if title is not None:
            
            name = title
            
        elif isinstance( self._payload_obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            name = self._payload_obj.GetName()
            
        else:
            
            name = payload_description
            
        
        self._title.SetValue( name )
        
        if description is not None:
            
            self._text.SetValue( description )
            
        
        if last_png_export_dir is not None:
            
            filename = name + '.png'
            
            filename = HydrusPaths.SanitizeFilename( filename )
            
            path = os.path.join( last_png_export_dir, filename )
            
            self._filepicker.SetPath( path )
            
        
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
        
        self._filepicker.Bind( wx.EVT_FILEPICKER_CHANGED, self.EventChanged )
        self._title.Bind( wx.EVT_TEXT, self.EventChanged )
        
    
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
        
        payload_description = self._payload_description.GetValue()
        payload_bytes = ClientSerialisable.GetPayloadBytes( self._payload_obj )
        
        title = self._title.GetValue()
        text = self._text.GetValue()
        path = self._filepicker.GetPath()
        
        if path is not None and path != '':
            
            base_dir = os.path.dirname( path )
            
            HG.client_controller.new_options.SetNoneableString( 'last_png_export_dir', base_dir )
            
        
        if not path.endswith( '.png' ):
            
            path += '.png'
            
        
        ClientSerialisable.DumpToPng( width, payload_bytes, title, payload_description, text, path )
        
        self._export.SetLabelText( 'done!' )
        
        HG.client_controller.CallLaterWXSafe( self._export, 2.0, self._export.SetLabelText, 'export' )
        
    
class PngsExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_objs ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._payload_objs = payload_objs
        
        self._directory_picker = wx.DirPickerCtrl( self )
        
        dp_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._directory_picker, 52 )
        
        self._directory_picker.SetMinSize( ( dp_width, -1 ) )
        
        self._width = wx.SpinCtrl( self, min = 100, max = 4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        last_png_export_dir = HG.client_controller.new_options.GetNoneableString( 'last_png_export_dir' )
        
        if last_png_export_dir is not None:
            
            self._directory_picker.SetPath( last_png_export_dir )
            
        
        self._width.SetValue( 512 )
        
        self._Update()
        
        #
        
        rows = []
        
        rows.append( ( 'export path: ', self._directory_picker ) )
        rows.append( ( 'png width: ', self._width ) )
        rows.append( ( '', self._export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.SetSizer( gridbox )
        
        self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventChanged )
        
    
    def _Update( self ):
        
        problems = []
        
        path = self._directory_picker.GetPath()
        
        if path is None or path == '':
            
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
        
        directory = self._directory_picker.GetPath()
        
        last_png_export_dir = directory
        
        if last_png_export_dir is not None and last_png_export_dir != '':
            
            HG.client_controller.new_options.SetNoneableString( 'last_png_export_dir', last_png_export_dir )
            
        
        for obj in self._payload_objs:
            
            ( payload_description, payload_bytes ) = ClientSerialisable.GetPayloadDescriptionAndBytes( obj )
            
            title = obj.GetName()
            text = ''
            path = os.path.join( directory, title )
            
            if not path.endswith( '.png' ):
                
                path += '.png'
                
            
            ClientSerialisable.DumpToPng( width, payload_bytes, title, payload_description, text, path )
            
        
        self._export.SetLabelText( 'done!' )
        
        HG.client_controller.CallLaterWXSafe( self._export, 2.0, self._export.SetLabelText, 'export' )
        
    
