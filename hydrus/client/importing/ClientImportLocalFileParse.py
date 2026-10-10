import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core.files import HydrusFileTypeDetermination

from hydrus.client.files import ClientFiles

RESULT_NOT_PARSED = 0
RESULT_GOOD = 1
RESULT_EMPTY = 2
RESULT_MISSING = 3
RESULT_UNIMPORTABLE = 4
RESULT_OCCUPIED = 5
RESULT_SIDECAR = 6
RESULT_DIRECTORY = 7

result_str_lookup = {    
    RESULT_NOT_PARSED : 'not yet parsed',
    RESULT_GOOD : 'good (you should not see this)',
    RESULT_EMPTY : 'PROBLEM: file empty',
    RESULT_MISSING : 'PROBLEM: file missing',
    RESULT_UNIMPORTABLE : 'PROBLEM: filetype unsupported',
    RESULT_OCCUPIED : 'PROBLEM: file in use by other program',
    RESULT_SIDECAR : 'sidecar',
    RESULT_DIRECTORY : 'directory (you should not see this)'
}

class LocalFileParse( object ):
    
    def __init__( self, path: str ):
        
        self._have_done_stat_check = False
        self._stat_result: os.stat_result | None = None
        
        self.path = path
        self.result = RESULT_NOT_PARSED
        self.index = 0
        self.mime = HC.APPLICATION_UNKNOWN
        self.size = 0
        
    
    def __eq__( self, other ):
        
        if isinstance( other, LocalFileParse ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self.path.__hash__()
        
    
    def _DoStat( self ):
        
        if self._have_done_stat_check and self._stat_result is None:
            
            return
            
        
        try:
            
            self._stat_result = os.stat( self.path )
            
        except FileNotFoundError:
            
            pass
            
        except OSError as e:
            
            if HydrusPaths.oserror_is_device_access_trouble( e ):
                
                pass
                
            else:
                
                raise
                
            
        
        self._have_done_stat_check = True
        
    
    def DoFileParse( self, comparable_sidecar_prefixes ):
        
        path = self.path
        
        ClientFiles.PopulateComparableSidecarPrefixes( [ path ], comparable_sidecar_prefixes )
        
        if not self._have_done_stat_check:
            
            self._DoStat()
            
        
        if not self.Exists():
            
            HydrusData.Print( f'Missing file: {path}' )
            
            self.result = RESULT_MISSING
            
        elif self.IsDir():
            
            HydrusData.Print( f'A directory somehow got into the file parsing pipeline: {path}')
            
            self.result = RESULT_DIRECTORY
            
        elif ClientFiles.LooksLikeSidecarPath( path, comparable_sidecar_prefixes ):
            
            self.result = RESULT_SIDECAR
            
        elif not HydrusPaths.PathIsFree( path ):
            
            HydrusData.Print( 'File currently in use: ' + path )
            
            self.result = RESULT_OCCUPIED
            
        else:
            
            self.size = self.GetSize()
            
            if self.size == 0:
                
                HydrusData.Print( 'Empty file: ' + path )
                
                self.result = RESULT_EMPTY
                
            elif path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                
                HydrusData.Print( 'In import parse, skipping Thumbs.db: ' + path )
                
                self.result = RESULT_UNIMPORTABLE
                
            else:
                
                # looks good, let's burn some CPU
                
                try:
                    
                    mime = HydrusFileTypeDetermination.GetMime( path )
                    
                except Exception as e:
                    
                    HydrusData.Print( 'Problem parsing mime for: ' + path )
                    HydrusData.PrintException( e )
                    
                    mime = HC.APPLICATION_UNKNOWN
                    
                
                self.mime = mime
                
                if mime in HC.ALLOWED_MIMES:
                    
                    self.result = RESULT_GOOD
                    
                else:
                    
                    HydrusData.Print( 'During file import scan, unparsable file: ' + path )
                    
                    self.result = RESULT_UNIMPORTABLE
                    
                
            
        
    
    def Exists( self ):
        
        if not self._have_done_stat_check:
            
            self._DoStat()
            
        
        return self._stat_result is not None
        
    
    def GetPrettyMime( self ):
        
        if self.result == RESULT_GOOD:
            
            return HC.mime_string_lookup[ self.mime ]
            
        else:
            
            return result_str_lookup[ self.result ]
            
        
    
    def GetSize( self ):
        
        if not self._have_done_stat_check:
            
            self._DoStat()
            
        
        if self._stat_result is None:
            
            return 0
            
        else:
            
            return self._stat_result.st_size
            
        
    
    def IsDir( self ):
        
        if not self._have_done_stat_check:
            
            self._DoStat()
            
        
        if self._stat_result is None:
            
            return False
            
        else:
            
            return HydrusPaths.stat_is_dir( self._stat_result )
            
        
    
