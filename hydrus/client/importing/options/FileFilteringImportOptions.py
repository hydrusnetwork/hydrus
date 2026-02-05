import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientData
from hydrus.client.search import ClientSearchPredicate

class FileFilteringImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_FILTERING_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'File Filtering Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._exclude_deleted = True
        self._allow_decompression_bombs = True
        self._filetype_filter_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = set( HC.GENERAL_FILETYPES ) )
        self._min_size = None
        self._max_size = None
        self._max_gif_size = None
        self._min_resolution = None
        self._max_resolution = None
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_filetype_filter_predicate = self._filetype_filter_predicate.GetSerialisableTuple()
        
        return ( 
            self._exclude_deleted,
            self._allow_decompression_bombs,
            serialisable_filetype_filter_predicate,
            self._min_size,
            self._max_size,
            self._max_gif_size,
            self._min_resolution,
            self._max_resolution,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( 
            self._exclude_deleted,
            self._allow_decompression_bombs,
            serialisable_filetype_filter_predicate,
            self._min_size,
            self._max_size,
            self._max_gif_size,
            self._min_resolution,
            self._max_resolution,
        ) = serialisable_info
        
        self._filetype_filter_predicate = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filetype_filter_predicate )
        
    
    def AllowsDecompressionBombs( self ):
        
        return self._allow_decompression_bombs
        
    
    def CheckFileIsValid( self, size, mime, width, height ):
        
        allowed_mimes = self.GetAllowedSpecificFiletypes()
        
        if mime not in allowed_mimes:
            
            raise HydrusExceptions.FileImportRulesException( 'File was a {}, which is not allowed by the File Import Options.'.format( HC.mime_string_lookup[ mime ] ) )
            
        
        if self._min_size is not None and size < self._min_size:
            
            raise HydrusExceptions.FileImportRulesException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the lower limit is ' + HydrusData.ToHumanBytes( self._min_size ) + '.' )
            
        
        if self._max_size is not None and size > self._max_size:
            
            raise HydrusExceptions.FileImportRulesException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the upper limit is ' + HydrusData.ToHumanBytes( self._max_size ) + '.' )
            
        
        if mime == HC.ANIMATION_GIF and self._max_gif_size is not None and size > self._max_gif_size:
            
            raise HydrusExceptions.FileImportRulesException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the upper limit for gifs is ' + HydrusData.ToHumanBytes( self._max_gif_size ) + '.' )
            
        
        if self._min_resolution is not None:
            
            ( min_width, min_height ) = self._min_resolution
            
            too_thin = width is not None and width < min_width
            too_short = height is not None and height < min_height
            
            if too_thin or too_short:
                
                raise HydrusExceptions.FileImportRulesException( 'File had resolution ' + ClientData.ResolutionToPrettyString( ( width, height ) ) + ' but the lower limit is ' + ClientData.ResolutionToPrettyString( self._min_resolution ) )
                
            
        
        if self._max_resolution is not None:
            
            ( max_width, max_height ) = self._max_resolution
            
            too_wide = width is not None and width > max_width
            too_tall = height is not None and height > max_height
            
            if too_wide or too_tall:
                
                raise HydrusExceptions.FileImportRulesException( 'File had resolution ' + ClientData.ResolutionToPrettyString( ( width, height ) ) + ' but the upper limit is ' + ClientData.ResolutionToPrettyString( self._max_resolution ) )
                
            
        
    
    def CheckNetworkDownload( self, possible_mime, num_bytes, is_complete_file_size ):
        
        if is_complete_file_size:
            
            error_prefix = 'Download was apparently '
            
        else:
            
            error_prefix = 'Download was at least '
            
        
        if possible_mime is not None:
            
            # this should always be animation_gif, but let's allow for future confusion
            if possible_mime in ( HC.ANIMATION_GIF, HC.IMAGE_GIF, HC.UNDETERMINED_GIF ) and self._max_gif_size is not None and num_bytes > self._max_gif_size:
                
                raise HydrusExceptions.FileImportRulesException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the upper limit for gifs is ' + HydrusData.ToHumanBytes( self._max_gif_size ) + '.' )
                
            
        
        if self._max_size is not None and num_bytes > self._max_size:
            
            raise HydrusExceptions.FileImportRulesException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the upper limit is ' + HydrusData.ToHumanBytes( self._max_size ) + '.' )
            
        
        if is_complete_file_size:
            
            if self._min_size is not None and num_bytes < self._min_size:
                
                raise HydrusExceptions.FileImportRulesException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the lower limit is ' + HydrusData.ToHumanBytes( self._min_size ) + '.' )
                
            
        
    
    def ExcludesDeleted( self ):
        
        return self._exclude_deleted
        
    
    def GetAllowedSpecificFiletypes( self ) -> collections.abc.Collection[ int ]:
        
        return ClientSearchPredicate.ConvertSummaryFiletypesToSpecific( self._filetype_filter_predicate.GetValue(), only_searchable = False )
        
    
    def GetMaxGifSize( self ):
        
        return self._max_gif_size
        
    
    def GetMaxResolution( self ):
        
        return self._max_resolution
        
    
    def GetMaxSize( self ):
        
        return self._max_size
        
    
    def GetMinResolution( self ):
        
        return self._min_resolution
        
    
    def GetMinSize( self ):
        
        return self._min_size
        
    
    def GetSummary( self ):
        
        statements = []
        
        statements.append( 'allowing {}'.format( ClientSearchPredicate.ConvertSummaryFiletypesToString( self._filetype_filter_predicate.GetValue() ) ) )
        
        if self._exclude_deleted:
            
            statements.append( 'excluding previously deleted' )
            
        
        if not self._allow_decompression_bombs:
            
            statements.append( 'excluding decompression bombs' )
            
        
        if self._min_size is not None:
            
            statements.append( 'excluding < ' + HydrusData.ToHumanBytes( self._min_size ) )
            
        
        if self._max_size is not None:
            
            statements.append( 'excluding > ' + HydrusData.ToHumanBytes( self._max_size ) )
            
        
        if self._max_gif_size is not None:
            
            statements.append( 'excluding gifs > ' + HydrusData.ToHumanBytes( self._max_gif_size ) )
            
        
        if self._min_resolution is not None:
            
            ( width, height ) = self._min_resolution
            
            statements.append( 'excluding < ( ' + HydrusNumbers.ToHumanInt( width ) + ' x ' + HydrusNumbers.ToHumanInt( height ) + ' )' )
            
        
        if self._max_resolution is not None:
            
            ( width, height ) = self._max_resolution
            
            statements.append( 'excluding > ( ' + HydrusNumbers.ToHumanInt( width ) + ' x ' + HydrusNumbers.ToHumanInt( height ) + ' )' )
            
        
        #
        
        summary = '\n'.join( statements )
        
        return summary
        
    
    def SetAllowedSpecificFiletypes( self, mimes ) -> None:
        
        mimes = ClientSearchPredicate.ConvertSpecificFiletypesToSummary( mimes, only_searchable = False )
        
        self._filetype_filter_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = mimes )
        
    
    def SetAllowsDecompressionBombs( self, value: bool ):
        
        self._allow_decompression_bombs = value
        
    
    def SetExcludesDeleted( self, value: bool ):
        
        self._exclude_deleted = value
        
    
    def SetMaxGifSize( self, value: int | None ):
        
        self._max_gif_size = value
        
    
    def SetMaxResolution( self, value: tuple[ int, int ] | None ):
        
        self._max_resolution = value
        
    
    def SetMaxSize( self, value: int | None ):
        
        self._max_size = value
        
    
    def SetMinResolution( self, value: tuple[ int, int ] | None ):
        
        self._min_resolution = value
        
    
    def SetMinSize( self, value: int | None ):
        
        self._min_size = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_FILTERING_IMPORT_OPTIONS ] = FileFilteringImportOptions
