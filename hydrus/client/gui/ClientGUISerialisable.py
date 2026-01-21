import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPathWidgets

class PNGExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_obj, title = None, description = None, payload_description = None ):
        
        super().__init__( parent )
        
        self._payload_obj = payload_obj
        
        self._filepicker = ClientGUIPathWidgets.FilePickerCtrl( self, wildcard = 'PNG (*.png)' )
        self._filepicker.SetSaveMode( True )
        
        flp_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._filepicker, 64 )
        
        self._filepicker.setMinimumWidth( flp_width )
        
        self._title = QW.QLineEdit( self )
        
        self._payload_description = QW.QLineEdit( self )
        
        self._text = QW.QLineEdit( self )
        
        self._width = ClientGUICommon.BetterSpinBox( self, min=100, max=4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        if payload_description is None:
            
            ( payload_description, payload_bytes ) = ClientSerialisable.GetPayloadDescriptionAndBytes( self._payload_obj )
            
        else:
            
            ( payload_bytes, payload_length ) = ClientSerialisable.GetPayloadBytesAndLength( self._payload_obj )
            
            payload_description += ' - {}'.format( HydrusData.ToHumanBytes( payload_length ) )
            
        
        self._payload_description.setText( payload_description )
        
        self._payload_description.setEnabled( False )
        
        self._width.setValue( 512 )
        
        last_png_export_dir = CG.client_controller.new_options.GetNoneableString( 'last_png_export_dir' )
        
        if title is not None:
            
            name = title
            
        elif isinstance( self._payload_obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            name = self._payload_obj.GetName()
            
        else:
            
            name = payload_description
            
        
        self._title.setText( name )
        
        if description is not None:
            
            self._text.setText( description )
            
        
        if last_png_export_dir is not None:
            
            filename = name + '.png'
            
            filename = HydrusPaths.SanitizeFilename( filename, True )
            
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
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._filepicker.filePickerChanged.connect( self._Update )
        self._title.textChanged.connect( self._Update )
        
    
    def _Update( self ):
        
        problems = []
        
        path = self._filepicker.GetPath()
        
        if path == '' or path is None:
            
            problems.append( 'select a path' )
            
        
        if path is not None and not os.path.exists( os.path.dirname( path ) ):
            
            problems.append( 'please select a directory that exists' )
            
        
        if self._title.text() == '':
            
            problems.append( 'set a title' )
            
        
        if len( problems ) == 0:
            
            self._export.setText( 'export' )
            
            self._export.setEnabled( True )
            
        else:
            
            self._export.setText( ' and '.join(problems) )
            
            self._export.setEnabled( False )
            
        
    
    def Export( self ):
        
        width = self._width.value()
        
        payload_description = self._payload_description.text()
        ( payload_bytes, payload_length ) = ClientSerialisable.GetPayloadBytesAndLength( self._payload_obj )
        
        title = self._title.text()
        text = self._text.text()
        path = self._filepicker.GetPath()
        
        if path is not None and path != '':
            
            base_dir = os.path.dirname( path )
            
            CG.client_controller.new_options.SetNoneableString( 'last_png_export_dir', base_dir )
            
        
        if not path.endswith( '.png' ):
            
            path += '.png'
            
        
        ClientSerialisable.DumpToPNG( width, payload_bytes, title, payload_description, text, path )
        
        self._export.setText( 'done!' )
        
        CG.client_controller.CallLaterQtSafe( self._export, 2.0, 'png export set text', self._export.setText, 'export' )
        
    

class PNGsExportPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, payload_objs ):
        
        super().__init__( parent )
        
        self._payload_objs = payload_objs
        
        self._directory_picker = ClientGUIPathWidgets.DirPickerCtrl( self )
        
        dp_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._directory_picker, 52 )
        
        self._directory_picker.setMinimumWidth( dp_width )
        
        self._width = ClientGUICommon.BetterSpinBox( self, min=100, max=4096 )
        
        self._export = ClientGUICommon.BetterButton( self, 'export', self.Export )
        
        #
        
        last_png_export_dir = CG.client_controller.new_options.GetNoneableString( 'last_png_export_dir' )
        
        if last_png_export_dir is not None:
            
            self._directory_picker.SetPath( last_png_export_dir )
            
        
        self._width.setValue( 512 )
        
        self._Update()
        
        #
        
        rows = []
        
        rows.append( ( 'export path: ', self._directory_picker ) )
        rows.append( ( 'png width: ', self._width ) )
        rows.append( ( '', self._export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._directory_picker.dirPickerChanged.connect( self._Update )
        
    
    def _Update( self ):
        
        problems = []
        
        path = self._directory_picker.GetPath()
        
        if path is None or path == '':
            
            problems.append( 'select a path' )
            
        
        if len( problems ) == 0:
            
            self._export.setText( 'export' )
            
            self._export.setEnabled( True )
            
        else:
            
            self._export.setText( ' and '.join(problems) )
            
            self._export.setEnabled( False )
            
        
    
    def Export( self ):
        
        width = self._width.value()
        
        directory = self._directory_picker.GetPath()
        
        last_png_export_dir = directory
        
        if last_png_export_dir is not None and last_png_export_dir != '':
            
            CG.client_controller.new_options.SetNoneableString( 'last_png_export_dir', last_png_export_dir )
            
        
        for obj in self._payload_objs:
            
            ( payload_description, payload_bytes ) = ClientSerialisable.GetPayloadDescriptionAndBytes( obj )
            
            title = obj.GetName()
            text = ''
            path = os.path.join( directory, title )
            
            if not path.endswith( '.png' ):
                
                path += '.png'
                
            
            ClientSerialisable.DumpToPNG( width, payload_bytes, title, payload_description, text, path )
            
        
        self._export.setText( 'done!' )
        
        CG.client_controller.CallLaterQtSafe( self._export, 2.0, 'png export set text', self._export.setText, 'export' )
        
    
