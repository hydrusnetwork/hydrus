from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsFiles
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP

class ShowKeys( ClientGUITopLevelWindows.Frame ):
    
    def __init__( self, key_type, keys ):
        
        if key_type == 'registration': title = 'Registration Tokens'
        elif key_type == 'access': title = 'Access Keys'
        
        tlw = CG.client_controller.GetMainTLW()
        
        super().__init__( tlw, CG.client_controller.PrepStringForDisplay( title ) )
        
        self._key_type = key_type
        self._keys = keys
        
        #
        
        self._text_ctrl = QW.QPlainTextEdit( self )
        self._text_ctrl.setLineWrapMode( QW.QPlainTextEdit.LineWrapMode.NoWrap )
        self._text_ctrl.setReadOnly( True )
        
        self._save_to_file = QW.QPushButton( 'save to file', self )
        self._save_to_file.clicked.connect( self.EventSaveToFile )
        
        self._done = QW.QPushButton( 'done', self )
        self._done.clicked.connect( self.close )
        
        #
        
        if key_type == 'registration': prepend = 'r'
        else: prepend = ''
        
        self._text = '\n'.join( [ prepend + key.hex() for key in self._keys ] )
        
        self._text_ctrl.setPlainText( self._text )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._text_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._save_to_file, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._done, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 500 ) )
        size_hint.setHeight( max( size_hint.height(), 200 ) )
        
        QP.SetInitialSize( self, size_hint )
        
        self.show()
        
    
    def EventSaveToFile( self ):
        
        filename = 'keys.txt'
        
        with ClientGUIDialogsFiles.FileDialog( self, acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile, default_filename = filename ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = dlg.GetPath()
                
                with open( path, 'w', encoding = 'utf-8' ) as f:
                    
                    f.write( self._text )
                    
                
            
        
    
