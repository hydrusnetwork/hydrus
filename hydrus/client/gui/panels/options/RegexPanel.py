from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEditRegexFavourites
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase

class RegexPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        regex_favourites = HC.options[ 'regex_favourites' ]
        
        self._regex_panel = ClientGUIScrolledPanelsEditRegexFavourites.EditRegexFavourites( self, regex_favourites )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._regex_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        regex_favourites = self._regex_panel.GetValue()
        
        HC.options[ 'regex_favourites' ] = regex_favourites
        
    
