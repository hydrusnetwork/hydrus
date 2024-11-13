import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

class FavouriteSearchManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER
    SERIALISABLE_NAME = 'Favourite Search Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._favourite_search_rows = []
        
        self._lock = threading.Lock()
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        # TODO: overhaul this whole thing, and the edit dialog, to not use None but '' for 'base folder path'
        # just needs a serialisable update on this end
        
        serialisable_favourite_search_info = []
        
        for row in self._favourite_search_rows:
            
            ( folder, name, file_search_context, synchronised, media_sort, media_collect ) = row
            
            serialisable_file_search_context = file_search_context.GetSerialisableTuple()
            
            if media_sort is None:
                
                serialisable_media_sort = None
                
            else:
                
                serialisable_media_sort = media_sort.GetSerialisableTuple()
                
            
            if media_collect is None:
                
                serialisable_media_collect = None
                
            else:
                
                serialisable_media_collect = media_collect.GetSerialisableTuple()
                
            
            serialisable_row = ( folder, name, serialisable_file_search_context, synchronised, serialisable_media_sort, serialisable_media_collect )
            
            serialisable_favourite_search_info.append( serialisable_row )
            
        
        return serialisable_favourite_search_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._favourite_search_rows = []
        
        for serialisable_row in serialisable_info:
            
            ( folder, name, serialisable_file_search_context, synchronised, serialisable_media_sort, serialisable_media_collect ) = serialisable_row
            
            file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
            
            if serialisable_media_sort is None:
                
                media_sort = None
                
            else:
                
                media_sort = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_media_sort )
                
            
            if serialisable_media_collect is None:
                
                media_collect = None
                
            else:
                
                media_collect = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_media_collect )
                
            
            row = ( folder, name, file_search_context, synchronised, media_sort, media_collect )
            
            self._favourite_search_rows.append( row )
            
        
    
    def GetFavouriteSearch( self, desired_folder_name, desired_name ):
        
        with self._lock:
            
            for ( folder, name, file_search_context, synchronised, media_sort, media_collect ) in self._favourite_search_rows:
                
                if folder == desired_folder_name and name == desired_name:
                    
                    return ( file_search_context, synchronised, media_sort, media_collect )
                    
                
            
        
        raise HydrusExceptions.DataMissing( 'Could not find a favourite search named "{}"!'.format( desired_name ) )
        
    
    def GetFavouriteSearchRows( self ):
        
        return list( self._favourite_search_rows )
        
    
    def GetNestedFoldersToNames( self ):
        
        with self._lock:
            
            nested_folders_to_names = {}
            
            for ( folder, name, file_search_context, synchronised, media_sort, media_collect ) in self._favourite_search_rows:
                
                current_dict = nested_folders_to_names
                
                if folder is not None:
                    
                    folder_parts = folder.split( '/' )
                    
                    for folder_part in folder_parts:
                        
                        if folder_part == '':
                            
                            continue
                            
                        
                        if folder_part not in current_dict:
                            
                            current_dict[ folder_part ] = {}
                            
                        
                        current_dict = current_dict[ folder_part ]
                        
                    
                
                if None not in current_dict:
                    
                    current_dict[ None ] = []
                    
                
                current_dict[ None ].append( ( folder, name ) )
                
            
            return nested_folders_to_names
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._dirty = True
            
        
    
    def SetFavouriteSearchRows( self, favourite_search_rows ):
        
        with self._lock:
            
            self._favourite_search_rows = list( favourite_search_rows )
            
            self._dirty = True
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER ] = FavouriteSearchManager
