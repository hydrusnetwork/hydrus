import itertools

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC

RESERVED_SESSION_NAMES = { '', 'just a blank page', CC.LAST_SESSION_SESSION_NAME, CC.EXIT_SESSION_SESSION_NAME }

class GUISessionContainer( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER
    SERIALISABLE_NAME = 'GUI Session Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, top_notebook_container = None, hashes_to_page_data = None, skipped_unchanged_page_hashes = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if top_notebook_container is None:
            
            top_notebook_container = GUISessionContainerPageNotebook( 'initialised top' )
            
        
        if hashes_to_page_data is None:
            
            hashes_to_page_data = {}
            
        
        if skipped_unchanged_page_hashes is None:
            
            skipped_unchanged_page_hashes = set()
            
        
        self._top_notebook_container = top_notebook_container
        self._hashes_to_page_data = hashes_to_page_data
        self._skipped_unchanged_page_hashes = skipped_unchanged_page_hashes
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_top_notebook = self._top_notebook_container.GetSerialisableTuple()
        
        return serialisable_top_notebook
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_top_notebook = serialisable_info
        
        self._top_notebook_container = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_top_notebook )
        
    
    def GetHashesToPageData( self ):
        
        return self._hashes_to_page_data
        
    
    def GetPageData( self, hash ) -> "GUISessionPageData":
        
        if hash not in self._hashes_to_page_data:
            
            raise HydrusExceptions.DataMissing( 'The page hash "{}" was not found!'.format( hash.hex() ) )
            
        
        return self._hashes_to_page_data[ hash ]
        
    
    def GetPageDataHashes( self ) -> set:
        
        return self._top_notebook_container.GetPageDataHashes()
        
    
    def GetTopNotebook( self ):
        
        return self._top_notebook_container
        
    
    def GetUnchangedPageDataHashes( self ):
        
        return set( self._skipped_unchanged_page_hashes )
        
    
    def HasAllDirtyPageData( self ):
        
        expected_hashes = self.GetPageDataHashes().difference( self._skipped_unchanged_page_hashes )
        actual_hashes = set( self._hashes_to_page_data.keys() )
        
        return expected_hashes.issubset( actual_hashes )
        
    
    def HasAllPageData( self ):
        
        expected_hashes = self.GetPageDataHashes()
        actual_hashes = set( self._hashes_to_page_data.keys() )
        
        return expected_hashes == actual_hashes
        
    
    def SetHashesToPageData( self, hashes_to_page_data ):
        
        self._hashes_to_page_data = hashes_to_page_data
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER ] = GUISessionContainer

class GUISessionContainerPage( HydrusSerialisable.SerialisableBaseNamed ):
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def GetPageDataHashes( self ):
        
        raise NotImplementedError()
        
    
class GUISessionContainerPageNotebook( GUISessionContainerPage ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_NOTEBOOK
    SERIALISABLE_NAME = 'GUI Session Container Notebook Page'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, page_containers = None ):
        
        GUISessionContainerPage.__init__( self, name )
        
        if page_containers is None:
            
            page_containers = []
            
        
        self._page_containers = HydrusSerialisable.SerialisableList( page_containers )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = self._page_containers.GetSerialisableTuple()
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_pages = serialisable_info
        
        self._page_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_pages )
        
    
    def GetPageDataHashes( self ) -> set:
        
        return set( itertools.chain.from_iterable( ( page.GetPageDataHashes() for page in self._page_containers ) ) )
        
    
    def GetPageContainers( self ):
        
        return self._page_containers
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_NOTEBOOK ] = GUISessionContainerPageNotebook

class GUISessionContainerPageSingle( GUISessionContainerPage ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_SINGLE
    SERIALISABLE_NAME = 'GUI Session Container Media Page'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, page_data_hash = None ):
        
        GUISessionContainerPage.__init__( self, name )
        
        if page_data_hash is None:
            
            page_data_hash = ''
            
        
        self._page_data_hash = page_data_hash
        
    
    def _GetSerialisableInfo( self ):
        
        return self._page_data_hash.hex()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        page_data_hash_hex = serialisable_info
        
        self._page_data_hash = bytes.fromhex( page_data_hash_hex )
        
    
    def GetPageDataHash( self ) -> bytes:
        
        return self._page_data_hash
        
    
    def GetPageDataHashes( self ) -> set:
        
        return { self._page_data_hash }
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_SINGLE ] = GUISessionContainerPageSingle

class GUISessionPageData( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_PAGE_DATA
    SERIALISABLE_NAME = 'GUI Session Page Data'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, management_controller = None, hashes = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if management_controller is None:
            
            self._management_controller = None
            self._hashes = None
            
        else:
            
            self._management_controller = management_controller.Duplicate() # duplicate, which _should_ freeze downloaders etc.. inside the MC
            self._hashes = list( hashes )
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_management_controller = self._management_controller.GetSerialisableTuple()
        serialisable_hashes = [ hash.hex() for hash in self._hashes ]
        
        return ( serialisable_management_controller, serialisable_hashes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_management_controller, serialisable_hashes ) = serialisable_info
        
        self._management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
        self._hashes = [ bytes.fromhex( hash_hex ) for hash_hex in serialisable_hashes ]
        
    
    def GetHashes( self ):
        
        return self._hashes
        
    
    def GetManagementController( self ):
        
        return self._management_controller
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_PAGE_DATA ] = GUISessionPageData
