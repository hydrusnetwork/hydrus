from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class QuestionCommitInterstitialFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.parentWidget().done, QW.QDialog.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.parentWidget().done, QW.QDialog.Rejected )
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setAlignment( QC.Qt.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._commit )
        
    
class QuestionFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.parentWidget().done, QW.QDialog.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.parentWidget().done, QW.QDialog.Rejected )
        self._forget.setObjectName( 'HydrusCancel' )
        
        def cancel_callback( parent ):
            
            parent.SetCancelled( True )
            parent.done( QW.QDialog.Rejected )
            
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', cancel_callback, parent )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setAlignment( QC.Qt.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._commit )
        
    
class QuestionYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.parentWidget().done, QW.QDialog.Accepted )
        self._yes.setObjectName( 'HydrusAccept' )
        self._yes.setText( yes_label )
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.Rejected )
        self._no.setObjectName( 'HydrusCancel' )
        self._no.setText( no_label )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._yes )
        QP.AddToLayout( hbox, self._no )
        
        vbox = QP.VBoxLayout()
        
        text = ClientGUICommon.BetterStaticText( self, message )
        text.setWordWrap( True )
        
        QP.AddToLayout( vbox, text )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._yes )
        
    

