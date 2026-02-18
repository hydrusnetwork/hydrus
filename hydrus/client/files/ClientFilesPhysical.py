import collections
import time
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core.files import HydrusFilesPhysicalStorage

from hydrus.client import ClientThreading

# TODO: A 'FilePath' or 'FileLocation' or similar that holds the path or IO stream, and/or temp_path to use for import calcs, and hash once known, and the human description like 'this came from blah URL'
# then we spam that all over the import pipeline and when we need a nice error, we ask that guy to describe himself
# search up 'human_file_description' to see what we'd be replacing

def EstimateBaseLocationGranularity( base_location_path ) -> int | None:
    
    dir_granularity_count = collections.Counter()
    
    with os.scandir( base_location_path ) as scan:
        
        hex_chars = '0123456789abcdef'
        num_weird_gubbins_found = 0
        
        for entry in scan:
            
            if entry.is_dir( follow_symlinks = False ):
                
                if len( entry.name ) > 3:
                    
                    continue
                    
                elif len( entry.name ) == 3:
                    
                    if entry.name[1] in hex_chars and entry.name[2] in hex_chars:
                        
                        my_length = 2 # we are 'td8' kind of thing
                        
                    else:
                        
                        continue
                        
                    
                else:
                    
                    if False not in ( c in hex_chars for c in entry.name ):
                        
                        my_length = len( entry.name )
                        
                    else:
                        
                        continue
                        
                    
                
                child_length = EstimateBaseLocationGranularity( entry.path )
                
                if child_length is not None:
                    
                    my_length += child_length
                    
                
                dir_granularity_count[ my_length ] += 1
                
            else:
                
                num_weird_gubbins_found += 1
                
            
            if num_weird_gubbins_found > 16:
                
                # ok we hit a file directory probably, so break out early
                return None
                
            
        
    
    if len( dir_granularity_count ) == 0:
        
        return None
        
    else:
        
        return dir_granularity_count.most_common( 1 )[0][0]
        
    

def RegranulariseBaseLocation( base_location_paths: list[ str ], prefix_types: list[ str ], starting_prefix_length: int, target_prefix_length: int, job_status: ClientThreading.JobStatus ):
    
    base_location_paths_to_granular_folder_prefixes_deleted = collections.defaultdict( list )
    
    try:
        
        num_files_moved = 0
        num_weird_dirs = 0
        num_weird_files = 0
        
        if starting_prefix_length == target_prefix_length:
            
            raise Exception( f'Called to granularise a file storage folder, but the starting and ending granularisation was the same ({starting_prefix_length})!!' )
            
        
        starting_prefixes_potential = set()
        ending_prefixes_potential = set()
        
        for prefix_type in prefix_types:
            
            starting_prefixes_potential.update( HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, starting_prefix_length ) )
            ending_prefixes_potential.update( HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, target_prefix_length ) )
            
        
        source_subfolders_we_are_doing: list[ FilesStorageSubfolder ] = []
        
        for base_location_path in base_location_paths:
            
            base_location = FilesStorageBaseLocation( base_location_path, 1 )
            
            for starting_prefix in sorted( starting_prefixes_potential ):
                
                source_subfolder = FilesStorageSubfolder( starting_prefix, base_location )
                
                if not source_subfolder.PathExists():
                    
                    continue
                    
                
                source_subfolders_we_are_doing.append( source_subfolder )
                
            
        
        num_source_subfolders_to_do = len( source_subfolders_we_are_doing )
        
        for ( num_source_subfolders_done, source_subfolder ) in enumerate( source_subfolders_we_are_doing ):
            
            starting_prefix = source_subfolder.prefix
            
            job_status.SetStatusText( f'Working "{starting_prefix}" ({HydrusNumbers.ValueRangeToPrettyString( num_source_subfolders_done, num_source_subfolders_to_do )})' + HC.UNICODE_ELLIPSIS )
            job_status.SetGauge( num_source_subfolders_done, num_source_subfolders_to_do )
            
            if starting_prefix_length < target_prefix_length:
                
                ending_subfolders = [ FilesStorageSubfolder( ending_prefix, source_subfolder.base_location ) for ending_prefix in ending_prefixes_potential if ending_prefix.startswith( starting_prefix ) ]
                
                for ending_viable_subfolder in ending_subfolders:
                    
                    ending_viable_subfolder.MakeSureExists()
                    
                
            else:
                
                ending_prefix = starting_prefix[ : target_prefix_length + 1 ]
                
                ending_subfolders = [ FilesStorageSubfolder( ending_prefix, source_subfolder.base_location ) ]
                
            
            hex_prefixes_to_ending_subfolders = { ending_subfolder.hex_prefix : ending_subfolder for ending_subfolder in ending_subfolders }
            
            all_filenames_to_move = []
            
            # this returns isdir results very quickly!
            with os.scandir( source_subfolder.path ) as scan:
                
                for entry in scan:
                    
                    if entry.is_dir():
                        
                        expected_dir = True in ( ending_subfolder.path.startswith( entry.path ) for ending_subfolder in ending_subfolders )
                        
                        if not expected_dir:
                            
                            num_weird_dirs += 1
                            
                            HydrusData.Print( f'When granularising folders, I saw a weird directory, "{entry.path}"! How did this thing sneak into Hydrus File Storage? Maybe it is an old prefix stub--a fragment of a previous maintenance job?' )
                            
                        
                    else:
                        
                        all_filenames_to_move.append( entry.name )
                        
                    
                
            
            num_filenames_to_do = len( all_filenames_to_move )
            
            for ( num_filenames_done, filename ) in enumerate( all_filenames_to_move ):
                
                if num_filenames_done % 100 == 0:
                    
                    job_status.SetStatusText( f'File {HydrusNumbers.ValueRangeToPrettyString( num_filenames_done, num_filenames_to_do )}', level = 2 )
                    job_status.SetGauge( num_filenames_done, num_filenames_to_do, level = 2 )
                    
                    while job_status.IsPaused() or job_status.IsCancelled():
                        
                        time.sleep( 0.1 )
                        
                        if job_status.IsCancelled():
                            
                            raise HydrusExceptions.CancelledException( 'Cancelled by user' )
                            
                        
                    
                
                source_path = source_subfolder.GetFilePath( filename )
                
                filename_prefix = filename[ : target_prefix_length ]
                
                if filename_prefix in hex_prefixes_to_ending_subfolders:
                    
                    destination_subfolder = hex_prefixes_to_ending_subfolders[ filename_prefix ]
                    
                    destination_path = destination_subfolder.GetFilePath( filename )
                    
                    # very low overhead primitive that works well in this context. we are moving many small things across the same partition
                    os.replace( source_path, destination_path )
                    
                    num_files_moved += 1
                    
                else:
                    
                    num_weird_files += 1
                    
                    HydrusData.Print( f'When regranularising folders, I failed to find a destination for the file with path "{source_path}"! I imagine it does not have a nice normal hex name and snuck into Hydrus File Storage by accident. You probably want to clean it up.')
                    
                
            
            if starting_prefix_length > target_prefix_length and len( os.listdir( str( source_subfolder.path ) ) ) == 0:
                
                base_location_paths_to_granular_folder_prefixes_deleted[ source_subfolder.base_location.path ].append( source_subfolder.prefix )
                
                # not recycle
                HydrusPaths.DeletePath( source_subfolder.path )
                
            
        
        return ( num_files_moved, num_weird_dirs, num_weird_files )
        
    finally:
        
        if len( base_location_paths_to_granular_folder_prefixes_deleted ) > 0:
            
            for migrated_path in sorted( base_location_paths_to_granular_folder_prefixes_deleted.keys() ):
                
                sorted_prefixes = sorted( base_location_paths_to_granular_folder_prefixes_deleted[ migrated_path ] )
                
                HydrusData.Print( f'When regranularising folders, I finished migrating prefixes completely out of the path "{migrated_path}". Since the folders were empty, I deleted them. The prefixes deleted were:' )
                HydrusData.Print( ', '.join( sorted_prefixes ) )
                
            
        
        job_status.SetStatusText( 'done!' )
        
        job_status.FinishAndDismiss()
        
    

class FilesStorageBaseLocation( object ):
    
    def __init__( self, path: str, ideal_weight: int, max_num_bytes = None ):
        
        self.creation_path = path
        
        # it may seem silly to wash these like this, but it is nice and certain about slashes and so on, which we like
        path = HydrusPaths.ConvertPortablePathToAbsPath( path )
        portable_path = HydrusPaths.ConvertAbsPathToPortablePath( path )
        
        try:
            
            real_path = HydrusPaths.ConvertAbsPathToRealPath( path )
            
        except Exception as e:
            
            HydrusData.Print( f'While trying to realise your file location storage path {path} to determine symlinks and such, the following error occured. Please forward to hydev.' )
            
            HydrusData.PrintException( e, do_wait = False )
            
            real_path = 'Could not determine real path--check log!'
            
        
        self.path = path
        self.portable_path = portable_path
        self.real_path = real_path
        self.ideal_weight = ideal_weight
        self.max_num_bytes = max_num_bytes
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FilesStorageBaseLocation ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self.path.__hash__()
        
    
    def __repr__( self ):
        
        pretty_path = self.path
        
        if self.real_path != self.path:
            
            pretty_path = f'{pretty_path} (Real path: {self.real_path})'
            
        
        if self.max_num_bytes is None:
            
            return f'{pretty_path} ({self.ideal_weight}, unlimited)'
            
        else:
            
            return f'{pretty_path} ({self.ideal_weight}, {HydrusData.ToHumanBytes( self.max_num_bytes )})'
            
        
    
    def AbleToAcceptSubfolders( self, current_num_bytes: int, num_bytes_of_subfolder: int ):
        
        if self.max_num_bytes is not None:
            
            if current_num_bytes + num_bytes_of_subfolder > self.max_num_bytes:
                
                return False
                
            
        
        if self.ideal_weight == 0:
            
            return False
            
        
        return True
        
    
    def EagerToAcceptSubfolders( self, current_normalised_weight: float, total_ideal_weight: int, weight_of_subfolder: float, current_num_bytes: int, num_bytes_of_subfolder: int ):
        
        if self.max_num_bytes is not None:
            
            if current_num_bytes + num_bytes_of_subfolder > self.max_num_bytes:
                
                return False
                
            
        
        if self.ideal_weight == 0:
            
            return False
            
        
        ideal_normalised_weight = self.ideal_weight / total_ideal_weight
        
        if current_normalised_weight + weight_of_subfolder > ideal_normalised_weight:
            
            return False
            
        
        return True
        
    
    def HasNoUpperLimit( self ):
        
        return self.max_num_bytes is None
        
    
    def MakeSureExists( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self.path )
        
    
    def NeedsToRemoveSubfolders( self, current_num_bytes: int ):
        
        if self.ideal_weight == 0:
            
            return True
            
        
        if self.max_num_bytes is not None and current_num_bytes > self.max_num_bytes:
            
            return True
            
        
        return False
        
    
    def PathExists( self ):
        
        return os.path.exists( self.path ) and os.path.isdir( self.path )
        
    
    def WouldLikeToRemoveSubfolders( self, current_normalised_weight: float, total_ideal_weight: int, weight_of_subfolder: float ):
        
        if self.ideal_weight == 0:
            
            return True
            
        
        ideal_normalised_weight = self.ideal_weight / total_ideal_weight
        
        # the weight_of_subfolder here is a bit of padding to make sure things stay a bit more bistable
        return current_normalised_weight - weight_of_subfolder > ideal_normalised_weight
        
    
    @staticmethod
    def STATICGetIdealWeights( total_num_bytes_to_hold: int, base_locations: list[ "FilesStorageBaseLocation" ] ) -> dict[ "FilesStorageBaseLocation", float ]:
        
        # This is kind of tacked on logic versus the eager/able/needs/would stuff, but I'm collecting it here so at least the logic, pseudo-doubled, is in one place
        # EDIT: I like this logic now, after some fixes and simplification, so perhaps it can be used elsewhere
        
        if total_num_bytes_to_hold == 0:
            
            total_num_bytes_to_hold = 1048576
            
        
        result = {}
        
        total_ideal_weight = sum( ( base_location.ideal_weight for base_location in base_locations ) )
        
        limited_locations: list[ FilesStorageBaseLocation ] = sorted( [ base_location for base_location in base_locations if base_location.max_num_bytes is not None ], key = lambda b_l: b_l.max_num_bytes )
        unlimited_locations: list[ FilesStorageBaseLocation ] = [ base_location for base_location in base_locations if base_location.max_num_bytes is None ]
        
        # ok we are first playing a game of elimination. eliminate limited locations that are overweight and distribute the extra for the next round
        next_round_of_limited_locations = []
        players_eliminated = False
        
        remaining_total_ideal_weight = total_ideal_weight
        remaining_normalised_weight = 1.0
        
        while len( limited_locations ) > 0:
            
            limited_location_under_examination = limited_locations.pop( 0 )
            
            max_num_bytes = limited_location_under_examination.max_num_bytes
            
            if max_num_bytes is None:
                
                raise Exception( f'Problem calculating ideal storage weights, particularly with location "{limited_location_under_examination.path}"! Please tell hydev.' )
                
            
            # of the remaining pot (remaining normalised weight), how much is our share vs remaining players (ideal weight over remaining total ideal weight)
            normalised_weight_we_want_to_have = ( limited_location_under_examination.ideal_weight / remaining_total_ideal_weight ) * remaining_normalised_weight
            normalised_weight_with_max_bytes = max_num_bytes / total_num_bytes_to_hold
            
            if normalised_weight_with_max_bytes < normalised_weight_we_want_to_have:
                
                # we can't hold all we want to, so we'll hold what we can and eliminate our part of the pot from the other players
                
                result[ limited_location_under_examination ] = normalised_weight_with_max_bytes
                
                remaining_normalised_weight -= normalised_weight_with_max_bytes
                remaining_total_ideal_weight -= limited_location_under_examination.ideal_weight
                
                players_eliminated = True
                
            else:
                
                next_round_of_limited_locations.append( limited_location_under_examination )
                
            
            if len( limited_locations ) == 0:
                
                if players_eliminated:
                    
                    # the pot just got bigger, so let's play another round and see if anyone else is bust
                    
                    limited_locations = next_round_of_limited_locations
                    
                    next_round_of_limited_locations = []
                    players_eliminated = False
                    
                else:
                    
                    # no one was eliminated (maybe there are no players left!), so it is time to distribute weight unfettered
                    unlimited_locations.extend( next_round_of_limited_locations )
                    
                
            
        
        # ok, all the bust players have been eliminated. the remaining pot is distributed according to relative weights as normal
        
        for base_location in unlimited_locations:
            
            result[ base_location ] = ( base_location.ideal_weight / remaining_total_ideal_weight ) * remaining_normalised_weight
            
        
        return result
        
    

class FilesStorageSubfolder( object ):
    
    def __init__( self, prefix: str, base_location: FilesStorageBaseLocation ):
        
        self.prefix = prefix
        self.base_location = base_location
        
        #
        
        self.hex_prefix = self.prefix[1:]
        
        our_subfolders = self._GetOurSubfolders()
        
        self.path = str( os.path.join( self.base_location.path, *our_subfolders ) )
        self.rwlock = ClientThreading.FileRWLock()
        
    
    def __repr__( self ):
        
        if self.prefix[0] == 'f':
            
            t = 'file'
            
        elif self.prefix[0] == 't':
            
            t = 'thumbnail'
            
        else:
            
            t = 'unknown'
            
        
        return f'{t} {self.prefix[1:]} at {self.path}'
        
    
    def _GetOurSubfolders( self ):
        
        first_char = self.prefix[0]
        
        # convert 'b' to ['b'], 'ba' to ['ba'], 'bad' to ['ba', 'd'], and so on  
        our_subfolders = [ self.hex_prefix[ i : i + 2 ] for i in range( 0, len( self.hex_prefix ), 2 ) ]
        
        # restore the f/t char
        our_subfolders[0] = first_char + our_subfolders[0]
        
        return our_subfolders
        
    
    def GetNormalisedWeight( self ):
        
        num_hex = len( self.prefix ) - 1
        
        return 1 / ( 16 ** num_hex )
        
    
    def GetFilePath( self, filename: str ) -> str:
        
        return os.path.join( self.path, filename )
        
    
    def GetPrefixDirectoriesLongestFirst( self ):
        
        our_subfolders = self._GetOurSubfolders()
        
        results = []
        
        path = self.base_location.path
        
        for our_subfolder in our_subfolders:
            
            path = os.path.join( path, our_subfolder )
            
            results.append( path )
            
        
        results.reverse()
        
        return results
        
    
    def IsForFiles( self ):
        
        return self.prefix[0] == 'f'
        
    
    def IterateAllFiles( self ):
        
        filenames = list( os.listdir( self.path ) )
        
        for filename in filenames:
            
            yield os.path.join( self.path, filename )
            
        
    
    def MakeSureExists( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self.path )
        
    
    def PathExists( self ):
        
        return os.path.exists( self.path ) and os.path.isdir( self.path )
        
    
