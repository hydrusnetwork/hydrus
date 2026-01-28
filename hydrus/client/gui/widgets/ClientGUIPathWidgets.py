
import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP

class DirPickerCtrl( QW.QWidget ):
    
    dirPickerChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        layout = QP.HBoxLayout( spacing = 2 )
        
        self._path_edit = QW.QLineEdit( self )
        
        self._button = QW.QPushButton( 'browse', self )
        
        self._button.clicked.connect( self._Browse )
        
        self._path_edit.textEdited.connect( self._TextEdited )
        
        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )
        
        self.setLayout( layout )
        
    
    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        
    
    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        try:
            
            path = ClientGUIDialogsQuick.PickDirectory( self, 'Select directory', existing_path )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if os.path.exists( path ):
            
            self.dirPickerChanged.emit()
            
        
    
    def _TextEdited( self, text ):
        
        if os.path.exists( text ):
            
            self.dirPickerChanged.emit()
            
        
    

class FilePickerCtrl( QW.QWidget ):
    
    filePickerChanged = QC.Signal()

    def __init__( self, parent = None, wildcard = None, starting_directory = None ):
        
        super().__init__( parent )

        layout = QP.HBoxLayout( spacing = 2 )

        self._path_edit = QW.QLineEdit( self )

        self._button = QW.QPushButton( 'browse', self )

        self._button.clicked.connect( self._Browse )

        self._path_edit.textEdited.connect( self._TextEdited )

        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )

        self.setLayout( layout )
        
        self._save_mode = False
        
        self._wildcard = wildcard
        
        self._starting_directory = starting_directory
        

    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        

    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def SetSaveMode( self, save_mode ):
        
        self._save_mode = save_mode
        

    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        if existing_path == '' and self._starting_directory is not None:
            
            existing_path = self._starting_directory
            
        
        # TODO: Merge ClientGUIDialogsFiles and what this guy does into a DialogsQuick call
        
        options = QW.QFileDialog.Option.DontResolveSymlinks
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            # careful here, QW.QFileDialog.Options doesn't exist on PyQt6
            options |= QW.QFileDialog.Option.DontUseNativeDialog
            
        
        if self._save_mode:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, options = options )[0]
                
            else:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, options = options )[0]
                
            
        else:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, options = options )[0]
                
            else:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, options = options )[0]
                
            
        
        if path == '':
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if self._save_mode or os.path.exists( path ):
            
            self.filePickerChanged.emit()
            
        

    def _TextEdited( self, text ):
        
        if self._save_mode or os.path.exists( text ):
            
            self.filePickerChanged.emit()
            
        
    
