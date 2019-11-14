from . import ClientConstants as CC
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import ClientGUIScrolledPanels
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

class QuestionCommitInterstitialFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.parentWidget().done, QW.QDialog.Accepted )
        QP.SetForegroundColour( self._commit, (0,128,0) )
        
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.parentWidget().done, QW.QDialog.Rejected )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( label, self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( '-or-', self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        QP.CallAfter( self._commit.setFocus, QC.Qt.OtherFocusReason )
        
    
class QuestionFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.parentWidget().done, QW.QDialog.Accepted )
        QP.SetForegroundColour( self._commit, (0,128,0) )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.parentWidget().done, QW.QDialog.Rejected )
        QP.SetForegroundColour( self._forget, (128,0,0) )
        
        def cancel_callback( parent ):
            
            parent.SetCancelled( True )
            parent.done( QW.QDialog.Rejected )
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', cancel_callback, parent )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( label, self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( '-or-', self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        QP.CallAfter( self._commit.setFocus, QC.Qt.OtherFocusReason )
        
    
class QuestionYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.parentWidget().done, QW.QDialog.Accepted )
        QP.SetForegroundColour( self._yes, ( 0, 128, 0 ) )
        self._yes.setText( yes_label )
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.Rejected )
        QP.SetForegroundColour( self._no, ( 128, 0, 0 ) )
        self._no.setText( no_label )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._yes )
        QP.AddToLayout( hbox, self._no )
        
        vbox = QP.VBoxLayout()
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.SetWrapWidth( 480 )
        
        QP.AddToLayout( vbox, text )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.widget().setLayout( vbox )
        
        QP.CallAfter( self._yes.setFocus, QC.Qt.OtherFocusReason )
        
    

