from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

def GetFinishArchiveDeleteFilteringAnswer( win, kept_label, deletion_options ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, 'filtering done?' ) as dlg:
        
        panel = QuestionArchiveDeleteFinishFilteringPanel( dlg, kept_label, deletion_options )
        
        dlg.SetPanel( panel )
        
        result = dlg.exec()
        location_context = panel.GetLocationContext()
        was_cancelled = dlg.WasCancelled()
        
        return ( result, location_context, was_cancelled )
        
    

def GetFinishFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = QuestionFinishFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        result = ( dlg.exec(), dlg.WasCancelled() )
        
        return result
        
    

def GetInterstitialFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = QuestionCommitInterstitialFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        result = dlg.exec()
        
        return result
        
    

class QuestionCommitInterstitialFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        super().__init__( parent )
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.parentWidget().done, QW.QDialog.DialogCode.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.parentWidget().done, QW.QDialog.DialogCode.Rejected )
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._commit )
        
    

class QuestionArchiveDeleteFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, kept_label: str | None, deletion_options ):
        
        super().__init__( parent )
        
        self._location_context = ClientLocation.LocationContext() # empty
        
        vbox = QP.VBoxLayout()
        
        first_commit = None
        
        if len( deletion_options ) == 0:
            
            if kept_label is None:
                
                kept_label = 'ERROR: do not seem to have any actions at all!'
                
            
            label = '{}?'.format( kept_label )
            
            st = ClientGUICommon.BetterStaticText( self, label )
            
            st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            first_commit = ClientGUICommon.BetterButton( self, 'commit', self.DoCommit, ClientLocation.LocationContext() )
            first_commit.setObjectName( 'HydrusAccept' )
            
            QP.AddToLayout( vbox, first_commit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        elif len( deletion_options ) == 1:
            
            ( location_context, delete_label ) = deletion_options[0]
            
            if kept_label is None:
                
                label = '{}?'.format( delete_label )
                
            else:
                
                label = '{} and {}?'.format( kept_label, delete_label )
                
            
            st = ClientGUICommon.BetterStaticText( self, label )
            
            st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            first_commit = ClientGUICommon.BetterButton( self, 'commit', self.DoCommit, location_context )
            first_commit.setObjectName( 'HydrusAccept' )
            
            QP.AddToLayout( vbox, first_commit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        else:
            
            if kept_label is not None:
                
                label = f'{kept_label}\n-and-'
                
                st = ClientGUICommon.BetterStaticText( self, label )
                
                st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
                
                QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            delay_delete_buttons = len( deletion_options ) > 0 and CG.client_controller.new_options.GetBoolean( 'archive_delete_commit_panel_delays_multiple_delete_choices' )
            delayed_delete_buttons = []
            
            for ( location_context, delete_label ) in deletion_options:
                
                label = '{}?'.format( delete_label )
                
                st = ClientGUICommon.BetterStaticText( self, label )
                
                st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
                
                QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                commit = ClientGUICommon.BetterButton( self, 'commit', self.DoCommit, location_context )
                commit.setObjectName( 'HydrusAccept' )
                
                QP.AddToLayout( vbox, commit, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                if first_commit is None:
                    
                    first_commit = commit
                    
                
                if delay_delete_buttons:
                    
                    delayed_delete_buttons.append( commit )
                    commit.setEnabled( False )
                    
                
            
            def do_it():
                
                for b in delayed_delete_buttons:
                    
                    b.setEnabled( True )
                    
                
            
            if len( delayed_delete_buttons ) > 0:
                
                CG.client_controller.CallLaterQtSafe( self, 1.2, 'delayed button enable', do_it )
                
            
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.DoForget )
        self._forget.setObjectName( 'HydrusCancel' )
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', self.DoGoBack )
        
        QP.AddToLayout( vbox, self._forget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( first_commit )
        
    
    def DoForget( self ):
        
        message = 'Quit filtering now and forget your work?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
            self.parentWidget().done( QW.QDialog.DialogCode.Rejected )
            
        
    
    def DoGoBack( self ):
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self.parentWidget().SetCancelled( True )
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self.parentWidget().done( QW.QDialog.DialogCode.Rejected )
        
    
    def DoCommit( self, location_context ):
        
        self._location_context = location_context
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self.parentWidget().done( QW.QDialog.DialogCode.Accepted )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._location_context
        
    

class QuestionFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        super().__init__( parent )
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.parentWidget().done, QW.QDialog.DialogCode.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.DoForget )
        self._forget.setObjectName( 'HydrusCancel' )
        
        def cancel_callback( parent ):
            
            parent.SetCancelled( True )
            parent.done( QW.QDialog.DialogCode.Rejected )
            
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', cancel_callback, parent )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._commit )
        
    
    def DoForget( self ):
        
        message = 'Quit filtering now and forget your work?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            # TODO: Replace this with signals bro
            # noinspection PyUnresolvedReferences
            self.parentWidget().done( QW.QDialog.DialogCode.Rejected )
            
        
    
