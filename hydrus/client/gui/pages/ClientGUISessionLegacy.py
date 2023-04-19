from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client.gui.pages import ClientGUISession

class GUISessionLegacy( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_LEGACY
    SERIALISABLE_NAME = 'Legacy GUI Session'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._page_tuples = []
        
    
    def _GetSerialisableInfo( self ):
        
        def handle_e( page_tuple, e ):
            
            HydrusData.ShowText( 'Attempting to save a page to the session failed! Its data tuple and error follows! Please close it or see if you can clear any potentially invalid data from it!' )
            
            HydrusData.ShowText( page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetSerialisablePageTuple( page_tuple ):
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, page_tuples ) = page_data
                
                serialisable_page_tuples = []
                
                for pt in page_tuples:
                    
                    try:
                        
                        serialisable_page_tuples.append( GetSerialisablePageTuple( pt ) )
                        
                    except Exception as e:
                        
                        handle_e( page_tuple, e )
                        
                    
                
                serialisable_page_data = ( name, serialisable_page_tuples )
                
            elif page_type == 'page':
                
                ( management_controller, hashes ) = page_data
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                serialisable_hashes = [ hash.hex() for hash in hashes ]
                
                serialisable_page_data = ( serialisable_management_controller, serialisable_hashes )
                
            
            serialisable_tuple = ( page_type, serialisable_page_data )
            
            return serialisable_tuple
            
        
        serialisable_info = []
        
        for page_tuple in self._page_tuples:
            
            try:
                
                serialisable_page_tuple = GetSerialisablePageTuple( page_tuple )
                
                serialisable_info.append( serialisable_page_tuple )
                
            except Exception as e:
                
                handle_e( page_tuple, e )
                
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def handle_e( serialisable_page_tuple, e ):
            
            HydrusData.ShowText( 'A page failed to load! Its serialised data and error follows!' )
            
            HydrusData.ShowText( serialisable_page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetPageTuple( serialisable_page_tuple ):
            
            ( page_type, serialisable_page_data ) = serialisable_page_tuple
            
            if page_type == 'pages':
                
                ( name, serialisable_page_tuples ) = serialisable_page_data
                
                page_tuples = []
                
                for spt in serialisable_page_tuples:
                    
                    try:
                        
                        page_tuples.append( GetPageTuple( spt ) )
                        
                    except Exception as e:
                        
                        handle_e( spt, e )
                        
                    
                
                page_data = ( name, page_tuples )
                
            elif page_type == 'page':
                
                ( serialisable_management_controller, serialisable_hashes ) = serialisable_page_data
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                hashes = [ bytes.fromhex( hash ) for hash in serialisable_hashes ]
                
                page_data = ( management_controller, hashes )
                
            
            page_tuple = ( page_type, page_data )
            
            return page_tuple
            
        
        for serialisable_page_tuple in serialisable_info:
            
            try:
                
                page_tuple = GetPageTuple( serialisable_page_tuple )
                
                self._page_tuples.append( page_tuple )
                
            except Exception as e:
                
                handle_e( serialisable_page_tuple, e )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( page_name, serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                management_controller.SetPageName( page_name )
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                new_serialisable_info.append( ( serialisable_management_controller, serialisable_hashes ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            new_serialisable_info = []
            
            for ( serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                new_serialisable_info.append( ( 'page', ( serialisable_management_controller, serialisable_hashes ) ) )
                
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            def clean_tuple( spt ):
                
                ( page_type, serialisable_page_data ) = spt
                
                if page_type == 'pages':
                    
                    ( name, pages_serialisable_page_tuples ) = serialisable_page_data
                    
                    if name.startswith( '[USER]' ) and len( name ) > 6:
                        
                        name = name[6:]
                        
                    
                    pages_serialisable_page_tuples = [ clean_tuple( pages_spt ) for pages_spt in pages_serialisable_page_tuples ]
                    
                    return ( 'pages', ( name, pages_serialisable_page_tuples ) )
                    
                else:
                    
                    return spt
                    
                
            
            new_serialisable_info = []
            
            serialisable_page_tuples = old_serialisable_info
            
            for serialisable_page_tuple in serialisable_page_tuples:
                
                serialisable_page_tuple = clean_tuple( serialisable_page_tuple )
                
                new_serialisable_info.append( serialisable_page_tuple )
                
            
            return ( 4, new_serialisable_info )
            
        
    
    def GetPageTuples( self ):
        
        return self._page_tuples
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_LEGACY ] = GUISessionLegacy

def ConvertPageTuplesToNotebookContainer( name, page_tuples ):
    
    page_containers = []
    hashes_to_page_data = {}
    
    for page_tuple in page_tuples:
        
        ( page_type, old_page_data ) = page_tuple
        
        if page_type == 'pages':
            
            ( sub_name, sub_page_tuples ) = old_page_data
            
            ( page_container, some_hashes_to_page_data ) = ConvertPageTuplesToNotebookContainer( sub_name, sub_page_tuples )
            
            hashes_to_page_data.update( some_hashes_to_page_data )
            
        else:
            
            ( management_controller, hashes ) = old_page_data
            
            page_data = ClientGUISession.GUISessionPageData( management_controller = management_controller, hashes = hashes )
            
            page_data_hash = page_data.GetSerialisedHash()
            
            page_container = ClientGUISession.GUISessionContainerPageSingle( management_controller.GetPageName(), page_data_hash = page_data_hash )
            
            hashes_to_page_data[ page_data_hash ] = page_data
            
        
        page_containers.append( page_container )
        
    
    notebook_page_container = ClientGUISession.GUISessionContainerPageNotebook( name, page_containers = page_containers )
    
    return ( notebook_page_container, hashes_to_page_data )
    
def ConvertLegacyToNew( legacy_session: GUISessionLegacy ):
    
    page_tuples = legacy_session.GetPageTuples()
    
    ( top_notebook_container, hashes_to_page_data ) = ConvertPageTuplesToNotebookContainer( 'top notebook', page_tuples )
    
    session = ClientGUISession.GUISessionContainer( legacy_session.GetName(), top_notebook_container = top_notebook_container, hashes_to_page_data = hashes_to_page_data )
    
    return session
    
