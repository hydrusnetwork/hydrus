from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class IPFSDaemonStatusAndInteractionPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_callable ):
        
        super().__init__( parent, 'ipfs daemon' )
        
        self._is_running = False
        
        self._service_callable = service_callable
        
        self._running_status = ClientGUICommon.BetterStaticText( self )
        self._check_running_button = ClientGUICommon.BetterButton( self, 'check daemon', self._CheckRunning )
        
        self._check_running_button.setEnabled( False )
        
        #
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        QP.AddToLayout( gridbox, self._check_running_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._running_status, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._CheckRunning()
        
    
    def _CheckRunning( self ):
        
        def qt_clean_up( result, is_running ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._running_status.setText( result )
            
            self._is_running = is_running
            
            self._check_running_button.setEnabled( True )
            
        
        def do_it( service ):
            
            result = ''
            is_running = False
            
            try:
                
                version = service.GetDaemonVersion()
                
                result = 'Running version {}.'.format( version )
                
                is_running = True
                
            except Exception as e:
                
                result = 'Problem: {}'.format( str( e ) )
                
                is_running = False
                
            finally:
                
                CG.client_controller.CallAfter( self, qt_clean_up, result, is_running )
                
            
        
        self._check_running_button.setEnabled( False )
        
        self._running_status.setText( 'checking' + HC.UNICODE_ELLIPSIS )
        
        service = self._service_callable()
        
        CG.client_controller.CallToThread( do_it, service )
        
    
