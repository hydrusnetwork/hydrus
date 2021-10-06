import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.networking import ClientGUINetwork
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

class NetworkJobControl( QW.QFrame ):
    
    def __init__( self, parent ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        self._network_job = None
        
        self._auto_override_bandwidth_rules = False
        
        self._left_text = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._right_text = ClientGUICommon.BetterStaticText( self )
        self._right_text.setAlignment( QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        
        self._last_right_min_width = 0
        
        self._gauge = ClientGUICommon.Gauge( self )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().cog, self._ShowCogMenu )
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, self.Cancel )
        self._error_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().dump_fail, self._ShowErrorMenu )
        
        self._error_button.setToolTip( 'Click here to see the last job\'s error.' )
        
        self._error_button.hide()
        
        self._error_text = None
        
        #
        
        self._Update()
        
        #
        
        st_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( st_hbox, self._left_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( st_hbox, self._right_text, CC.FLAGS_CENTER_PERPENDICULAR )
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, st_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._error_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def _EditBandwidthRules( self, network_context: ClientNetworkingContexts.NetworkContext ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit bandwidth rules for {}'.format( network_context.ToString() ) ) as dlg:
            
            bandwidth_rules = HG.client_controller.network_engine.bandwidth_manager.GetRules( network_context )
            
            summary = network_context.GetSummary()
            
            panel = ClientGUINetwork.EditBandwidthRulesPanel( dlg, bandwidth_rules, summary )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                bandwidth_rules = panel.GetValue()
                
                HG.client_controller.network_engine.bandwidth_manager.SetRules( network_context, bandwidth_rules )
                
            
        
    
    def _ShowCogMenu( self ):
        
        menu = QW.QMenu()
        
        if self._network_job is not None and self._network_job.engine is not None:
            
            url = self._network_job.GetURL()
            
            ClientGUIMenus.AppendMenuLabel( menu, url, description = 'copy URL to the clipboard' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            network_contexts = self._network_job.GetNetworkContexts()
            
            if len( network_contexts ) > 0:
                
                bandwidth_manager = self._network_job.engine.bandwidth_manager
                
                submenu = QW.QMenu( menu )
                
                menu_network_contexts = []
                
                network_contexts_used = set()
                
                for network_context in network_contexts:
                    
                    uses_default = False
                    
                    if bandwidth_manager.UsesDefaultRules( network_context ):
                        
                        uses_default = True
                        
                        default_network_context = network_context.GetDefault()
                        
                        if default_network_context not in network_contexts_used:
                            
                            menu_network_contexts.append( ( False, default_network_context, network_context ) )
                            
                            network_contexts_used.add( default_network_context )
                            
                        
                    
                    if not network_context.IsEphemeral():
                        
                        menu_network_contexts.append( ( uses_default, network_context, network_context ) )
                        
                    
                
                for ( uses_default, network_context_to_edit, network_context_to_test ) in menu_network_contexts:
                    
                    network_context_text = network_context_to_edit.ToString()
                    
                    if uses_default:
                        
                        network_context_text = 'set rules for {}'.format( network_context_text )
                        
                    else:
                        
                        ( waiting_estimate, gumpf ) = bandwidth_manager.GetWaitingEstimateAndContext( [ network_context_to_test ] )
                        
                        if waiting_estimate > 0:
                            
                            network_context_text = '{} ({})'.format( network_context_text, HydrusData.TimeDeltaToPrettyTimeDelta( waiting_estimate ) )
                            
                        
                    
                    ClientGUIMenus.AppendMenuItem( submenu, network_context_text, 'edit the bandwidth rules for this network context', self._EditBandwidthRules, network_context_to_edit )
                    
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'edit bandwidth rules' )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            if self._network_job.CurrentlyWaitingOnConnectionError():
                
                ClientGUIMenus.AppendMenuItem( menu, 'reattempt connection now', 'Stop waiting on a connection error and reattempt the job now.', self._network_job.OverrideConnectionErrorWait )
                
            
            if not self._network_job.DomainOK():
                
                ClientGUIMenus.AppendMenuItem( menu, 'scrub domain errors', 'Clear recent domain errors and allow this job to go now.', self._network_job.ScrubDomainErrors )
                
            
            if self._network_job.CurrentlyWaitingOnServersideBandwidth():
                
                ClientGUIMenus.AppendMenuItem( menu, 'reattempt request now (server reports low bandwidth)', 'Stop waiting on a serverside bandwidth delay and reattempt the job now.', self._network_job.OverrideServersideBandwidthWait )
                
            
            if self._network_job.ObeysBandwidth():
                
                ClientGUIMenus.AppendMenuItem( menu, 'override bandwidth rules for this job', 'Tell the current job to ignore existing bandwidth rules and go ahead anyway.', self._network_job.OverrideBandwidth )
                
            
            if not self._network_job.TokensOK():
                
                ClientGUIMenus.AppendMenuItem( menu, 'override forced gallery wait times for this job', 'Force-allow this download to proceed, ignoring the normal gallery wait times.', self._network_job.OverrideToken )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'auto-override bandwidth rules for all jobs here after five seconds', 'Ignore existing bandwidth rules for all jobs under this control, instead waiting a flat five seconds.', self._auto_override_bandwidth_rules, self.FlipAutoOverrideBandwidth )
        
        CGC.core().PopupMenu( self._cog_button, menu )
        
    
    def _ShowErrorMenu( self ):
        
        if self._error_text is None:
            
            return
            
        
        menu = QW.QMenu()
        
        ClientGUIMenus.AppendMenuItem( menu, 'show error', 'Show the recent error in a messagebox.', self.ShowError )
        ClientGUIMenus.AppendMenuItem( menu, 'copy error', 'Copy the recent error to the clipboard.', self.CopyError )
        
        CGC.core().PopupMenu( self._cog_button, menu )
        
    
    def _OverrideBandwidthIfAppropriate( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            return
            
        else:
            
            if self._auto_override_bandwidth_rules and HydrusData.TimeHasPassed( self._network_job.GetCreationTime() + 5 ):
                
                self._network_job.OverrideBandwidth()
                
            
        
    
    def _Update( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            can_cancel = False
            
            self._left_text.clear()
            self._right_text.clear()
            self._gauge.SetRange( 1 )
            self._gauge.SetValue( 0 )
            
        else:
            
            can_cancel = not self._network_job.IsDone()
            
            ( status_text, current_speed, bytes_read, bytes_to_read ) = self._network_job.GetStatus()
            
            self._left_text.setText( status_text )
            
            speed_text = ''
            
            if bytes_read is not None and bytes_read > 0 and not self._network_job.HasError():
                
                if bytes_to_read is not None and bytes_read != bytes_to_read:
                    
                    speed_text += HydrusData.ConvertValueRangeToBytes( bytes_read, bytes_to_read )
                    
                else:
                    
                    speed_text += HydrusData.ToHumanBytes( bytes_read )
                    
                
                if current_speed != bytes_to_read: # if it is a real quick download, just say its size
                    
                    speed_text += ' ' + HydrusData.ToHumanBytes( current_speed ) + '/s'
                    
                
            
            show_right_text = speed_text != ''
            
            if self._right_text.isVisible() != show_right_text:
                
                self._right_text.setVisible( show_right_text )
                
                self.updateGeometry()
                
            
            if speed_text != '':
                
                self._right_text.setText( speed_text )
                
                right_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._right_text, len( speed_text ) )
                
                right_min_width = right_width
                
                if right_min_width != self._last_right_min_width:
                    
                    self._last_right_min_width = right_min_width
                    
                    self._right_text.setMinimumWidth( right_min_width )
                    
                    self.updateGeometry()
                    
                
            
            self._gauge.SetRange( bytes_to_read )
            self._gauge.SetValue( bytes_read )
            
        
        if self._cancel_button.isEnabled() != can_cancel:
            
            self._cancel_button.setEnabled( can_cancel )
            
        
    
    def Cancel( self ):
        
        if self._network_job is not None:
            
            self._network_job.Cancel( 'Cancelled by user.' )
            
        
    
    def ClearError( self ):
        
        self._error_text = None
        
        self._error_button.hide()
        
    
    def CopyError( self ):
        
        if self._error_text is None:
            
            return
            
        
        HG.client_controller.pub( 'clipboard', 'text', self._error_text )
        
    
    def ClearNetworkJob( self ):
        
        if self._network_job is not None:
            
            self._network_job = None
            
            self._gauge.setToolTip( '' )
            
            self._Update()
            
            HG.client_controller.gui.UnregisterUIUpdateWindow( self )
            
        
    
    def FlipAutoOverrideBandwidth( self ):
        
        self._auto_override_bandwidth_rules = not self._auto_override_bandwidth_rules
        
    
    def SetNetworkJob( self, network_job: ClientNetworkingJobs.NetworkJob ):
        
        if self._network_job != network_job:
            
            self._network_job = network_job
            
            self._gauge.setToolTip( self._network_job.GetURL() )
            
            self._Update()
            
            HG.client_controller.gui.RegisterUIUpdateWindow( self )
            
        
    
    def SetError( self, error: str ):
        
        self._error_text = error
        
        self._error_button.show()
        
    
    def ShowError( self ):
        
        if self._error_text is None:
            
            return
            
        
        QW.QMessageBox.critical( self, 'network error', self._error_text )
        
    
    def TIMERUIUpdate( self ):
        
        self._OverrideBandwidthIfAppropriate()
        
        if HG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    