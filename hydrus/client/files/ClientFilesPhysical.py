import os

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core.files import HydrusFilesPhysicalStorage

from hydrus.client import ClientThreading

# TODO: A 'FilePath' or 'FileLocation' or similar that holds the path or IO stream, and/or temp_path to use for import calcs, and hash once known, and the human description like 'this came from blah URL'
# then we spam that all over the import pipeline and when we need a nice error, we ask that guy to describe himself
# search up 'human_file_description' to see what we'd be replacing

def GranulariseStorageFolder( base_location_path: str, prefix_type, starting_prefix_length, target_prefix_length ):
    
    base_location = FilesStorageBaseLocation( base_location_path, 1 )
    
    starting_viable_prefixes = set( HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, prefix_length = starting_prefix_length ) )
    ending_viable_prefixes = set( HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, prefix_length = target_prefix_length ) )
    
    for starting_viable_prefix in starting_viable_prefixes:
        
        source_subfolder = FilesStorageSubfolder( starting_viable_prefix, base_location )
        
        if not source_subfolder.PathExists():
            
            continue
            
        
        all_filenames_to_move = list( os.listdir( source_subfolder.path ) )
        
        ending_viable_subfolders = [ FilesStorageSubfolder( ending_viable_prefix, base_location ) for ending_viable_prefix in ending_viable_prefixes if ending_viable_prefix.startswith( starting_viable_prefix ) ]
        
        for ending_viable_subfolder in ending_viable_subfolders:
            
            ending_viable_subfolder.MakeSureExists()
            
        
        hex_prefixes_to_ending_viable_subfolders = { subfolder.hex_prefix : subfolder for subfolder in ending_viable_subfolders }
        
        for filename in all_filenames_to_move:
            
            source_path = source_subfolder.GetFilePath( filename )
            
            if os.path.isdir( source_path ):
                
                if filename in ending_viable_prefixes:
                    
                    # no worries, we are probably continuing a previous job that stopped early
                    pass
                    
                else:
                    
                    HydrusData.Print( f'When granularising folders, I saw a weird directory, "{source_path}"! How did this thing sneak into Hydrus File Storage? Maybe it is an old prefix stub--an fragment of a previous maintenance job? You probably want to check it out and clean it up (if it is called like "file_storage/f23/3" and is empty, just delete it).' )
                    
                
                continue
                
            
            filename_prefix = filename[ : target_prefix_length ]
            
            if filename_prefix in hex_prefixes_to_ending_viable_subfolders:
                
                destination_subfolder = hex_prefixes_to_ending_viable_subfolders[ filename_prefix ]
                
                destination_path = destination_subfolder.GetFilePath( filename )
                
                HydrusPaths.MergeFile( source_path, destination_path )
                
            else:
                
                HydrusData.Print( f'When granularising folders, I failed to find a destination for the file with path "{source_path}"! I imagine it does not have a nice normal hex name and snuck into Hydrus File Storage by accident. You probably want to clean it up.')
                
            
        
        if len( os.listdir( source_subfolder.path ) ) == 0:
            
            HydrusData.Print( f'When granularising folders, I finished migrating out of the path "{source_subfolder.path}", and since it was empty when I was done, I deleted it!' )
            
            HydrusPaths.RecyclePath( source_subfolder.path )
            
        
    

class FilesStorageBaseLocation( object ):
    
    def __init__( self, path: str, ideal_weight: int, max_num_bytes = None ):
        
        self.creation_path = path
        
        # it may seem silly to wash these like this, but it is nice and certain about slashes and so on, which we like
        path = HydrusPaths.ConvertPortablePathToAbsPath( path )
        portable_path = HydrusPaths.ConvertAbsPathToPortablePath( path )
        
        self.path = path
        self.portable_path = portable_path
        self.ideal_weight = ideal_weight
        self.max_num_bytes = max_num_bytes
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FilesStorageBaseLocation ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self.path.__hash__()
        
    
    def __repr__( self ):
        
        if self.max_num_bytes is None:
            
            return f'{self.path} ({self.ideal_weight}, unlimited)'
            
        else:
            
            return f'{self.path} ({self.ideal_weight}, {HydrusData.ToHumanBytes( self.max_num_bytes )})'
            
        
    
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
        
        limited_locations = sorted( [ base_location for base_location in base_locations if base_location.max_num_bytes is not None ], key = lambda b_l: b_l.max_num_bytes )
        unlimited_locations = [ base_location for base_location in base_locations if base_location.max_num_bytes is None ]
        
        # ok we are first playing a game of elimination. eliminate limited locations that are overweight and distribute the extra for the next round
        next_round_of_limited_locations = []
        players_eliminated = False
        
        remaining_total_ideal_weight = total_ideal_weight
        remaining_normalised_weight = 1.0
        
        while len( limited_locations ) > 0:
            
            limited_location_under_examination = limited_locations.pop( 0 )
            
            # of the remaining pot (remaining normalised weight), how much is our share vs remaining players (ideal weight over remaining total ideal weight)
            normalised_weight_we_want_to_have = ( limited_location_under_examination.ideal_weight / remaining_total_ideal_weight ) * remaining_normalised_weight
            normalised_weight_with_max_bytes = limited_location_under_examination.max_num_bytes / total_num_bytes_to_hold
            
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
    
    def __init__( self, prefix: str, base_location: FilesStorageBaseLocation, purge: bool = False ):
        
        self.prefix = prefix
        self.base_location = base_location
        self.purge = purge
        
        #
        
        first_char = self.prefix[0]
        self.hex_prefix = self.prefix[1:]
        
        # convert 'b' to ['b'], 'ba' to ['ba'], 'bad' to ['ba', 'd'], and so on  
        our_subfolders = [ self.hex_prefix[ i : i + 2 ] for i in range( 0, len( self.hex_prefix ), 2 ) ]
        
        # restore the f/t char
        our_subfolders[0] = first_char + our_subfolders[0]
        
        self.path = os.path.join( self.base_location.path, *our_subfolders )
        self.rwlock = ClientThreading.FileRWLock()
        
    
    def __repr__( self ):
        
        if self.prefix[0] == 'f':
            
            t = 'file'
            
        elif self.prefix[0] == 't':
            
            t = 'thumbnail'
            
        else:
            
            t = 'unknown'
            
        
        return f'{t} {self.prefix[1:]} at {self.path}'
        
    
    def GetNormalisedWeight( self ):
        
        num_hex = len( self.prefix ) - 1
        
        return 1 / ( 16 ** num_hex )
        
    
    def GetFilePath( self, filename: str ) -> str:
        
        return os.path.join( self.path, filename )
        
    
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
        
    
