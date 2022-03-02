from qtpy import QtWidgets as QW

from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class IPFSDaemonStatusAndInteractionPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_callable ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs daemon' )
        
        self._is_running = False
        self._nocopy_enabled = False
        
        self._service_callable = service_callable
        
        self._running_status = ClientGUICommon.BetterStaticText( self )
        self._check_running_button = ClientGUICommon.BetterButton( self, 'check daemon', self._CheckRunning )
        self._nocopy_status = ClientGUICommon.BetterStaticText( self )
        self._check_nocopy = ClientGUICommon.BetterButton( self, 'check nocopy', self._CheckNoCopy )
        self._enable_nocopy = ClientGUICommon.BetterButton( self, 'enable nocopy', self._EnableNoCopy )
        
        self._check_running_button.setEnabled( False )
        self._check_nocopy.setEnabled( False )
        
        #
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        QP.AddToLayout( gridbox, self._check_running_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._running_status, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._check_nocopy, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._nocopy_status, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._enable_nocopy, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, ( 20, 20 ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._CheckRunning()
        
    
    def _CheckNoCopy( self ):
        
        def qt_clean_up( result, nocopy_available ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._nocopy_status.setText( result )
            
            self._check_nocopy.setEnabled( True )
            
            self._nocopy_enabled = nocopy_available
            
            if self._nocopy_enabled:
                
                self._enable_nocopy.setEnabled( False )
                
            else:
                
                self._enable_nocopy.setEnabled( True )
                
            
        
        def do_it( service ):
            
            try:
                
                nocopy_available = service.GetNoCopyAvailable()
                
                if nocopy_available:
                    
                    result = 'Nocopy is available.'
                    
                else:
                    
                    result = 'Nocopy is not available.'
                    
                
            except Exception as e:
                
                result = 'Problem: {}'.format( str( e ) )
                
                nocopy_available = False
                
            finally:
                
                QP.CallAfter( qt_clean_up, result, nocopy_available )
                
            
        
        self._check_nocopy.setEnabled( False )
        
        self._nocopy_status.setText( 'checking\u2026' )
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
    def _CheckRunning( self ):
        
        def qt_clean_up( result, is_running ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._running_status.setText( result )
            
            self._is_running = is_running
            
            self._check_running_button.setEnabled( True )
            
            if self._is_running:
                
                self._check_nocopy.setEnabled( True )
                
                self._CheckNoCopy()
                
            
        
        def do_it( service ):
            
            try:
                
                version = service.GetDaemonVersion()
                
                result = 'Running version {}.'.format( version )
                
                is_running = True
                
            except Exception as e:
                
                result = 'Problem: {}'.format( str( e ) )
                
                is_running = False
                
            finally:
                
                QP.CallAfter( qt_clean_up, result, is_running )
                
            
        
        self._check_running_button.setEnabled( False )
        self._check_nocopy.setEnabled( False )
        self._enable_nocopy.setEnabled( False )
        
        self._running_status.setText( 'checking\u2026' )
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
    def _EnableNoCopy( self ):
        
        def qt_clean_up( success ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            if success:
                
                self._CheckNoCopy()
                
            else:
                
                QW.QMessageBox.critical( self, 'Error', 'Unfortunately, was unable to set nocopy configuration.' )
                
                self._enable_nocopy.setEnabled( True )
                
            
        
        def do_it( service ):
            
            try:
                
                success = service.EnableNoCopy( True )
                
            except Exception as e:
                
                message = 'Problem: {}'.format( str( e ) )
                
                QP.CallAfter( QW.QMessageBox.critical, None, 'Error', message )
                
                success = False
                
            finally:
                
                QP.CallAfter( qt_clean_up, success )
                
            
        
        self._enable_nocopy.setEnabled( False )
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
