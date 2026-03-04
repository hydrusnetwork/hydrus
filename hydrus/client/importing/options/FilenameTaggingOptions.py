import os
import re

from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientGlobals as CG
from hydrus.client.metadata import ClientTags

class FilenameTaggingOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS
    SERIALISABLE_NAME = 'Filename Tagging Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._tags_for_all = set()
        
        # Note we are leaving this here for a bit, even though it is no longer used, to leave a window so ImportFolder can rip existing values
        # it can be nuked in due time
        self._load_from_neighbouring_txt_files = False
        
        self._add_filename = ( False, 'filename' )
        
        self._directories_dict = {}
        
        for index in ( 0, 1, 2, -3, -2, -1 ):
            
            self._directories_dict[ index ] = ( False, '' )
            
        
        self._quick_namespaces = []
        self._regexes = []
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_directories_dict = list(self._directories_dict.items())
        
        return ( list( self._tags_for_all ), self._load_from_neighbouring_txt_files, self._add_filename, serialisable_directories_dict, self._quick_namespaces, self._regexes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( tags_for_all_list, self._load_from_neighbouring_txt_files, self._add_filename, serialisable_directories_dict, self._quick_namespaces, self._regexes ) = serialisable_info
        
        self._directories_dict = dict( serialisable_directories_dict )
        
        # converting [ namespace, regex ] to ( namespace, regex ) for listctrl et al to handle better
        self._quick_namespaces = [ tuple( item ) for item in self._quick_namespaces ]
        self._tags_for_all = set( tags_for_all_list )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( tags_for_all_list, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory, quick_namespaces, regexes ) = old_serialisable_info
            
            directories_dict = {}
            
            directories_dict[ 0 ] = add_first_directory
            directories_dict[ 1 ] = add_second_directory
            directories_dict[ 2 ] = add_third_directory
            
            for index in ( -3, -2, -1 ):
                
                directories_dict[ index ] = ( False, '' )
                
            
            serialisable_directories_dict = list(directories_dict.items())
            
            new_serialisable_info = ( tags_for_all_list, load_from_neighbouring_txt_files, add_filename, serialisable_directories_dict, quick_namespaces, regexes )
            
            return ( 2, new_serialisable_info )
            
        
    
    def AdvancedSetTuple( self, quick_namespaces, regexes ):
        
        self._quick_namespaces = quick_namespaces
        self._regexes = regexes
        
    
    def AdvancedToTuple( self ):
        
        return ( self._quick_namespaces, self._regexes )
        
    
    def GetTags( self, service_key, path ):
        
        tags = set()
        
        tags.update( self._tags_for_all )
        
        ( base, filename ) = os.path.split( path )
        
        ( filename, any_ext_gumpf ) = os.path.splitext( filename )
        
        ( filename_boolean, filename_namespace ) = self._add_filename
        
        if filename_boolean:
            
            if filename_namespace != '':
                
                tag = filename_namespace + ':' + filename
                
            else:
                
                tag = filename
                
            
            tags.add( tag )
            
        
        ( drive, directories ) = os.path.splitdrive( base )
        
        while directories.startswith( os.path.sep ):
            
            directories = directories[1:]
            
        
        directories = directories.split( os.path.sep )
        
        for ( index, ( dir_boolean, dir_namespace ) ) in list(self._directories_dict.items()):
            
            # we are talking -3 through 2 here
            
            if not dir_boolean:
                
                continue
                
            
            try:
                
                directory = directories[ index ]
                
            except IndexError:
                
                continue
                
            
            if dir_namespace != '':
                
                tag = dir_namespace + ':' + directory
                
            else:
                
                tag = directory
                
            
            tags.add( tag )
            
        
        #
        
        for regex in self._regexes:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( submatch )
                            
                        
                    else:
                        
                        tags.add( match )
                        
                    
                
            except Exception as e:
                
                pass
                
            
        
        for ( namespace, regex ) in self._quick_namespaces:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( namespace + ':' + submatch )
                            
                        
                    else:
                        
                        tags.add( namespace + ':' + match )
                        
                    
                
            except Exception as e:
                
                pass
                
            
        
        #
        
        tags = HydrusTags.CleanTags( tags )
        
        tags = CG.client_controller.tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_STORAGE, service_key, tags )
        
        return tags
        
    
    def SimpleSetTuple( self, tags_for_all, add_filename, directories_dict ):
        
        self._tags_for_all = tags_for_all
        self._add_filename = add_filename
        self._directories_dict = directories_dict
        
    
    def SimpleToTuple( self ):
        
        return ( self._tags_for_all, self._add_filename, self._directories_dict )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS ] = FilenameTaggingOptions    
