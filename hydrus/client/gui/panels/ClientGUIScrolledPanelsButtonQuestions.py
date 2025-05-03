from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class QuestionYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        super().__init__( parent )
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.parentWidget().done, QW.QDialog.DialogCode.Accepted )
        self._yes.setObjectName( 'HydrusAccept' )
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.DialogCode.Rejected )
        self._no.setObjectName( 'HydrusCancel' )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._yes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._no, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        text = ClientGUICommon.BetterStaticText( self, message )
        text.setWordWrap( True )
        
        QP.AddToLayout( vbox, text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._yes )
        
    

class QuestionYesNoNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_tuples = None, disable_yes_initially = False ):
        
        super().__init__( parent )
        
        if no_tuples is None:
            
            no_tuples = [ ( 'no', 'no' ) ]
            
        
        self._value = no_tuples[0][1]
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.parentWidget().done, QW.QDialog.DialogCode.Accepted )
        self._yes.setObjectName( 'HydrusAccept' )
        
        no_buttons = []
        
        for ( label, data ) in no_tuples:
            
            no_button = ClientGUICommon.BetterButton( self, label, self._DoNo, data )
            no_button.setObjectName( 'HydrusCancel' )
            
            no_buttons.append( no_button )
            
        
        #
        
        text = ClientGUICommon.BetterStaticText( self, message )
        text.setWordWrap( True )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._yes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        for no_button in no_buttons:
            
            QP.AddToLayout( hbox, no_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._yes )
        
        if disable_yes_initially:
            
            def do_it():
                
                self._yes.setEnabled( True )
                
            
            CG.client_controller.CallLaterQtSafe( self, 1.2, 'delayed button enable', do_it )
            
            self._yes.setEnabled( False )
            
        
    
    def _DoNo( self, value ):
        
        self._value = value
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self.parentWidget().done( QW.QDialog.DialogCode.Rejected )
        
    
    def GetValue( self ):
        
        return self._value
        
    

class QuestionYesYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_tuples = None, no_label = 'no' ):
        
        super().__init__( parent )
        
        if yes_tuples is None:
            
            yes_tuples = [ ( 'yes', 'yes' ) ]
            
        
        self._value = yes_tuples[0][1]
        
        yes_buttons = []
        
        for ( label, data ) in yes_tuples:
            
            yes_button = ClientGUICommon.BetterButton( self, label, self._DoYes, data )
            yes_button.setObjectName( 'HydrusAccept' )
            
            yes_buttons.append( yes_button )
            
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.DialogCode.Rejected )
        self._no.setObjectName( 'HydrusCancel' )
        
        #
        
        text = ClientGUICommon.BetterStaticText( self, message )
        text.setWordWrap( True )
        
        hbox = QP.HBoxLayout()
        
        for yes_button in yes_buttons:
            
            QP.AddToLayout( hbox, yes_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._no, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( yes_buttons[0] )
        
    
    def _DoYes( self, value ):
        
        self._value = value
        
        # TODO: Replace this with signals bro
        # noinspection PyUnresolvedReferences
        self.parentWidget().done( QW.QDialog.DialogCode.Accepted )
        
    
    def GetValue( self ):
        
        return self._value
        
    
