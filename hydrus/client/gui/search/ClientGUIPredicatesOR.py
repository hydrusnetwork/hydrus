import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.search import ClientSearch

# ultimately, rewrite acread to be two classes, acread and acreadthatsupportsor
# and then this guy only imports the base class, and only the supportsor will know about this
# otherwise we have jank imports, and also nested OR lmao
# also this should take file and tag domain

class ORPredicateControl( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, predicate: ClientSearch.Predicate, empty_file_search_context: typing.Optional[ ClientSearch.FileSearchContext ] = None ):
        
        QW.QWidget.__init__( self, parent )
        
        from hydrus.client.gui.search import ClientGUIACDropdown
        
        if predicate.GetType() != ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
            
            raise Exception( 'Launched an ORPredicateControl without an OR Pred!' )
            
        
        page_key = HydrusData.GenerateKey()
        
        predicates = predicate.GetValue()
        
        if empty_file_search_context is None:
            
            location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            file_search_context = ClientSearch.FileSearchContext( location_context = location_context, predicates = predicates )
            
        else:
            
            empty_file_search_context = empty_file_search_context.Duplicate()
            
            empty_file_search_context.SetPredicates( predicates )
            
            file_search_context = empty_file_search_context
            
        
        self._search_control = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context, hide_favourites_edit_actions = True )
        
        self._search_control.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._search_control, 64 ) )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._search_control, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        ClientGUIFunctions.SetFocusLater( self._search_control )
        
    
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
        
    
