import os

from qtpy import QtWidgets as QW

from hydrus.client import ClientGlobals as CG

class FileDialog( QW.QFileDialog ):
    
    def __init__( self, parent = None, message = None, acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFile, default_filename = None, default_directory = None, wildcard = None, defaultSuffix = None ):
        
        super().__init__( parent )
        
        if message is not None:
            
            self.setWindowTitle( message )
            
        
        self.setAcceptMode( acceptMode )
        
        self.setFileMode( fileMode )
        
        if default_directory is not None:
            
            self.setDirectory( default_directory )
            
        
        if defaultSuffix is not None:
            
            self.setDefaultSuffix( defaultSuffix )
            
        
        if default_filename is not None:
            
            self.selectFile( default_filename )
            
        
        if wildcard:
            
            self.setNameFilters( [ wildcard, 'Any files (*)' ] )
            
        
        self.setOption( QW.QFileDialog.Option.DontResolveSymlinks, True )
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.Option.DontUseNativeDialog, True )
            
        
    
    def __enter__( self ):
        
        return self
        

    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self.deleteLater()
        

    def _GetSelectedFiles( self ):
        
        return [ os.path.normpath( path ) for path in self.selectedFiles() ]
        
    
    def GetPath( self ):
        
        sel = self._GetSelectedFiles()

        if len( sel ) > 0:
            
            return sel[ 0 ]
            

        return None
        
    
    def GetPaths( self ):
        
        return self._GetSelectedFiles()
        
    
