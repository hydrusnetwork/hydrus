import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client.gui import QtPorting as QP

# ultimately, rewrite acread to be two classes, acread and acreadthatsupportsor
# and then this guy only imports the base class, and only the supportsor will know about this
# otherwise we have jank imports, and also nested OR lmao
# also this should take file and tag domain

class ORPredicateControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearch.Predicate ):
        
        QW.QWidget.__init__( self, parent )
        
        from hydrus.client.gui.search import ClientGUIACDropdown
        
        if predicate.GetType() != ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
            
            raise Exception( 'Launched an ORPredicateControl without an OR Pred!' )
            
        
        predicates = predicate.GetValue()
        
        page_key = HydrusData.GenerateKey()
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        file_search_context = ClientSearch.FileSearchContext( location_context = location_context, predicates = predicates )
        
        self._search_control = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context, hide_favourites_edit_actions = True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._search_control, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def CheckValid( self ):
        
        try:
            
            predicates = self.GetPredicates()
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( str( e ) )
            
        
    
    def GetPredicates( self ):
        
        or_sub_predicates = self._search_control.GetPredicates()
        
        if len( or_sub_predicates ) == 0:
            
            return []
            
        elif len( or_sub_predicates ) == 1:
            
            return or_sub_predicates
            
        
        or_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, or_sub_predicates )
        
        return [ or_predicate ]
        
