import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
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
        
    
class QuestionArchiveDeleteFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, kept_label: typing.Optional[ str ], deletion_options ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._location_context = ClientLocation.LocationContext() # empty
        
        vbox = QP.VBoxLayout()
        
        first_commit = None
        
        if len( deletion_options ) == 0:
            
            if kept_label is None:
                
                kept_label = 'ERROR: do not seem to have any actions at all!'
                
            
            label = '{}?'.format( kept_label )
            
            st = ClientGUICommon.BetterStaticText( self, label )
            
            st.setAlignment( QC.Qt.AlignCenter )
            
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
            
            st.setAlignment( QC.Qt.AlignCenter )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            first_commit = ClientGUICommon.BetterButton( self, 'commit', self.DoCommit, location_context )
            first_commit.setObjectName( 'HydrusAccept' )
            
            QP.AddToLayout( vbox, first_commit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        else:
            
            if kept_label is not None:
                
                label = '{}{}-and-'.format( kept_label, os.linesep )
                
                st = ClientGUICommon.BetterStaticText( self, label )
                
                st.setAlignment( QC.Qt.AlignCenter )
                
                QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            for ( location_context, delete_label ) in deletion_options:
                
                label = '{}?'.format( delete_label )
                
                st = ClientGUICommon.BetterStaticText( self, label )
                
                st.setAlignment( QC.Qt.AlignCenter )
                
                QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                commit = ClientGUICommon.BetterButton( self, 'commit', self.DoCommit, location_context )
                commit.setObjectName( 'HydrusAccept' )
                
                QP.AddToLayout( vbox, commit, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                if first_commit is None:
                    
                    first_commit = commit
                    
                
            
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.parentWidget().done, QW.QDialog.Rejected )
        self._forget.setObjectName( 'HydrusCancel' )
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', self.DoGoBack )
        
        QP.AddToLayout( vbox, self._forget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( first_commit )
        
    
    def DoGoBack( self ):
        
        self.parentWidget().SetCancelled( True )
        self.parentWidget().done( QW.QDialog.Rejected )
        
    
    def DoCommit( self, location_context ):
        
        self._location_context = location_context
        self.parentWidget().done( QW.QDialog.Accepted )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._location_context
        
    
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
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.Rejected )
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
        
    

class QuestionYesYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_tuples = None, no_label = 'no' ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        if yes_tuples is None:
            
            yes_tuples = [ ( 'yes', 'yes' ) ]
            
        
        self._value = yes_tuples[0][1]
        
        yes_buttons = []
        
        for ( label, data ) in yes_tuples:
            
            yes_button = ClientGUICommon.BetterButton( self, label, self._DoYes, data )
            yes_button.setObjectName( 'HydrusAccept' )
            
            yes_buttons.append( yes_button )
            
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.Rejected )
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
        
        self.parentWidget().done( QW.QDialog.Accepted )
        
    
    def GetValue( self ):
        
        return self._value
        
    
