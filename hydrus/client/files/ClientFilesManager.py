import collections
import collections.abc
import os
import random
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files import HydrusFilesPhysicalStorage
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.files import ClientFilesPhysical

class ClientFilesManager( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        # the lock for any file access and for altering the list of locations
        self._master_locations_rwlock = ClientThreading.FileRWLock()
        
        # the locks for the sub-locations
        self._prefixes_to_rwlocks = collections.defaultdict( ClientThreading.FileRWLock )
        
        self._prefixes_to_client_files_subfolders: collections.defaultdict[ str, list[ ClientFilesPhysical.FilesStorageSubfolder ] ] = collections.defaultdict( list )
        
        self._physical_file_delete_wait = threading.Event()
        
        self._locations_to_free_space = {}
        
        self._bad_error_occurred = False
        self._missing_subfolders = set()
        
        self._Reinit()
        
        self._controller.sub( self, 'Reinit', 'new_ideal_client_files_locations' )
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def _AddFile( self, hash, mime, source_path ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode or HG.file_import_report_mode:
            
            HydrusData.ShowText( 'Adding file to client file structure: from {} to {}'.format( source_path, dest_path ) )
            
        
        file_size = os.path.getsize( source_path )
        
        dest_free_space = self._GetFileStorageFreeSpaceForHash( hash )
        
        if dest_free_space < 100 * 1048576 or dest_free_space < file_size:
            
            message = 'The disk for path "{}" is almost full and cannot take the file "{}", which is {}! Shut the client down now and fix this!'.format( dest_path, hash.hex(), HydrusData.ToHumanBytes( file_size ) )
            
            HydrusData.ShowText( message )
            
            self._HandleCriticalDriveError()
            
            raise Exception( message )
            
        
        try:
            
            HydrusPaths.MirrorFile( source_path, dest_path )
            
        except Exception as e:
            
            message = f'Copying the file from "{source_path}" to "{dest_path}" failed! Details should be shown and other import queues should be paused. You should shut the client down now and fix this!'
            
            HydrusData.ShowText( message )
            
            HydrusData.ShowException( e )
            
            self._HandleCriticalDriveError()
            
            raise Exception( message ) from e
            
        
    
    def _AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        dest_path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding thumbnail: ' + str( ( len( thumbnail_bytes ), dest_path ) ) )
            
        
        try:
            
            HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
            
            with open( dest_path, 'wb' ) as f:
                
                f.write( thumbnail_bytes )
                
            
        except Exception as e:
            
            subfolder = self._GetSubfolderForFile( hash, 't' )
            
            if not subfolder.PathExists():
                
                raise HydrusExceptions.DirectoryMissingException( f'The directory {subfolder} was not found! Reconnect the missing location or shut down the client immediately!' )
                
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file "{}" failed to write to path "{}". This event suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.'.format( hash.hex(), dest_path ) )
            
        
        if not silent:
            
            self._controller.pub( 'clear_thumbnails', { hash } )
            self._controller.pub( 'new_thumbnails', { hash } )
            
        
    
    def _AttemptToHealMissingLocations( self ):
        
        # if a missing prefix folder seems to be in another location, lets update to that other location
        
        correct_rows = []
        some_are_unhealable = False
        
        fixes_counter = collections.Counter()
        
        known_base_locations = self._GetCurrentSubfolderBaseLocations()
        
        ( media_base_locations, thumbnail_override_base_location ) = self._controller.Read( 'ideal_client_files_locations' )
        
        known_base_locations.update( media_base_locations )
        
        if thumbnail_override_base_location is not None:
            
            known_base_locations.add( thumbnail_override_base_location )
            
        
        for missing_subfolder in self._missing_subfolders:
            
            missing_base_location = missing_subfolder.base_location
            prefix = missing_subfolder.prefix
            
            potential_correct_base_locations = []
            
            for known_base_location in known_base_locations:
                
                if known_base_location == missing_base_location:
                    
                    continue
                    
                
                potential_location_subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, known_base_location )
                
                if potential_location_subfolder.PathExists():
                    
                    potential_correct_base_locations.append( known_base_location )
                    
                
            
            if len( potential_correct_base_locations ) == 1:
                
                correct_base_location = potential_correct_base_locations[0]
                
                correct_subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, correct_base_location )
                
                correct_rows.append( ( missing_subfolder, correct_subfolder ) )
                
                fixes_counter[ ( missing_base_location, correct_base_location ) ] += 1
                
            else:
                
                some_are_unhealable = True
                
            
        
        if len( correct_rows ) > 0 and some_are_unhealable:
            
            message = 'Hydrus found multiple missing locations in your file storage. Some of these locations seemed to be fixable, others did not. The client will now inform you about both problems.'
            
            self._controller.BlockingSafeShowCriticalMessage( 'Multiple file location problems.', message )
            
        
        if len( correct_rows ) > 0:
            
            summaries = sorted( ( '{} folders seem to have moved from {} to {}'.format( HydrusNumbers.ToHumanInt( count ), missing_base_location, correct_base_location ) for ( ( missing_base_location, correct_base_location ), count ) in fixes_counter.items() ) )
            
            summary_message = 'Some client file folders were missing, but they appear to be in other known locations! The folders are:'
            summary_message += '\n' * 2
            summary_message += '\n'.join( summaries )
            summary_message += '\n' * 2
            summary_message += 'Assuming you did this on purpose, or hydrus recently inserted stub values after database corruption, Hydrus is ready to update its internal knowledge to reflect these new mappings as soon as this dialog closes. If you know these proposed fixes are incorrect, terminate the program now.'
            
            HydrusData.Print( summary_message )
            
            self._controller.BlockingSafeShowCriticalMessage( 'About to auto-heal client file folders.', summary_message )
            
            CG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
            
        
    
    def _ChangeFileExt( self, hash, old_mime, mime ):
        
        old_path = self._GenerateExpectedFilePath( hash, old_mime )
        new_path = self._GenerateExpectedFilePath( hash, mime )
        
        if old_path == new_path:
            
            # some diff mimes have the same ext
            
            return
            
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Changing file ext: ' + str( ( old_path, new_path ) ) )
            
        
        if HydrusPaths.PathIsFree( old_path ):
            
            try:
                
                HydrusPaths.MergeFile( old_path, new_path )
                
                needed_to_copy_file = False
                
            except:
                
                HydrusPaths.MirrorFile( old_path, new_path )
                
                needed_to_copy_file = True
                
            
        else:
            
            HydrusPaths.MirrorFile( old_path, new_path )
            
            needed_to_copy_file = True
            
        
        return needed_to_copy_file
        
    
    def _GenerateExpectedFilePath( self, hash, mime ):
        
        # TODO: this guy is presumably nuked or altered when we move to overlapping locations. there is no 'expected' to check, but there might be multiple, or a 'preferred' for imports
        
        self._WaitOnWakeup()
        
        subfolder = self._GetSubfolderForFile( hash, 'f' )
        
        hash_encoded = hash.hex()
        
        return subfolder.GetFilePath( f'{hash_encoded}{HC.mime_ext_lookup[ mime ]}' )
        
    
    def _GenerateExpectedThumbnailPath( self, hash ):
        
        self._WaitOnWakeup()
        
        subfolder = self._GetSubfolderForFile( hash, 't' )
        
        hash_encoded = hash.hex()
        
        return subfolder.GetFilePath( f'{hash_encoded}.thumbnail' )
        
    
    def _GenerateThumbnailBytes( self, file_path, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        ( width, height ) = media_result.GetResolution()
        duration_ms = media_result.GetDurationMS()
        num_frames = media_result.GetNumFrames()
        
        bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
        thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
        
        target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
        
        percentage_in = self._controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
        
        try:
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( file_path, target_resolution, mime, duration_ms, num_frames, percentage_in = percentage_in )
            
        except Exception as e:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file for the above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
            
        
        return thumbnail_bytes
        
    
    def _GetAllSubfolders( self ) -> list[ ClientFilesPhysical.FilesStorageSubfolder ]:
        
        result = []
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            result.extend( subfolders )
            
        
        return result
        
    
    def _GetCurrentSubfolderBaseLocations( self, only_files = False ):
        
        known_base_locations = set()
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            if only_files and not prefix.startswith( 'f' ):
                
                continue
                
            
            for subfolder in subfolders:
                
                known_base_locations.add( subfolder.base_location )
                
            
        
        return known_base_locations
        
    
    def _GetFileStorageFreeSpace( self, base_location: ClientFilesPhysical.FilesStorageBaseLocation ):
        
        if base_location in self._locations_to_free_space:
            
            ( free_space, time_fetched ) = self._locations_to_free_space[ base_location ]
            
            if free_space > 100 * ( 1024 ** 3 ):
                
                check_period = 3600
                
            elif free_space > 15 * ( 1024 ** 3 ):
                
                check_period = 600
                
            else:
                
                check_period = 60
                
            
            if HydrusTime.TimeHasPassed( time_fetched + check_period ):
                
                free_space = HydrusPaths.GetFreeSpace( base_location.path )
                
                if free_space is None:
                    
                    free_space = 0
                    
                
                self._locations_to_free_space[ base_location ] = ( free_space, HydrusTime.GetNow() )
                
            
        else:
            
            free_space = HydrusPaths.GetFreeSpace( base_location.path )
            
            if free_space is None:
                
                free_space = 0
                
            
            self._locations_to_free_space[ base_location ] = ( free_space, HydrusTime.GetNow() )
            
        
        return free_space
        
    
    def _GetFileStorageFreeSpaceForHash( self, hash: bytes ) -> int:
        
        subfolder = self._GetSubfolderForFile( hash, 'f' )
        
        base_location = subfolder.base_location
        
        return self._GetFileStorageFreeSpace( base_location )
        
    
    def _GetPossibleSubfoldersForFile( self, hash: bytes, prefix_type: str ) -> list[ ClientFilesPhysical.FilesStorageSubfolder ]:
        
        prefix = HydrusFilesPhysicalStorage.GetPrefix( hash, prefix_type )
        
        if prefix in self._prefixes_to_client_files_subfolders:
            
            return self._prefixes_to_client_files_subfolders[ prefix ]
            
        
        return []
        
    
    def _GetPrefixRWLock( self, hash: bytes, prefix_type: str ) -> ClientThreading.FileRWLock:
        """
        You can only call this guy if you have the total lock already!
        """
        
        prefix = HydrusFilesPhysicalStorage.GetPrefix( hash, prefix_type )
        
        return self._prefixes_to_rwlocks[ prefix ]
        
    
    def _GetRebalanceTuple( self ):
        
        try:
            
            # TODO: obviously this will change radically when we move to multiple folders for real and background migration. hacks for now
            # In general, I think this thing is going to determine the next migration destination and purge flag
            # the background file migrator will work on current purge flags and not talk to this guy until the current flags are clear 
            
            ( ideal_media_base_locations, ideal_thumbnail_override_base_location ) = self._controller.Read( 'ideal_client_files_locations' )
            
            if False in ( base_location.PathExists() for base_location in ideal_media_base_locations ) or ( ideal_thumbnail_override_base_location is not None and not ideal_thumbnail_override_base_location.PathExists() ):
                
                return None
                
            
            service_info = CG.client_controller.Read( 'service_info', CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
            
            hydrus_local_file_storage_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
            
            total_ideal_weight = sum( ( base_location.ideal_weight for base_location in ideal_media_base_locations ) )
            
            smallest_subfolder_normalised_weight = 1
            largest_subfolder_normalised_weight = 0
            
            current_base_locations_to_normalised_weights = collections.Counter()
            current_base_locations_to_size_estimate = collections.Counter()
            
            file_prefixes = [ prefix for prefix in self._prefixes_to_client_files_subfolders.keys() if prefix.startswith( 'f' ) ]
            
            all_media_base_locations = set( ideal_media_base_locations )
            
            for file_prefix in file_prefixes:
                
                subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
                
                subfolder = subfolders[0]
                
                base_location = subfolder.base_location
                
                all_media_base_locations.add( base_location )
                
                normalised_weight = subfolder.GetNormalisedWeight()
                
                current_base_locations_to_normalised_weights[ base_location ] += normalised_weight
                current_base_locations_to_size_estimate[ base_location ] += normalised_weight * hydrus_local_file_storage_total_size
                
                if normalised_weight < smallest_subfolder_normalised_weight:
                    
                    smallest_subfolder_normalised_weight = normalised_weight
                    
                
                if normalised_weight > largest_subfolder_normalised_weight:
                    
                    largest_subfolder_normalised_weight = normalised_weight
                    
                
            
            smallest_subfolder_num_bytes = smallest_subfolder_normalised_weight * hydrus_local_file_storage_total_size
            
            #
            
            # ok so the problem here is that when a location blocks new subfolders because of max num bytes rules, the other guys have to take the slack and end up overweight
            # we want these overweight guys to nonetheless distribute their stuff according to relative weights
            # so, what we'll do is we'll play a game with a split-pot, where bust players can't get dosh from later rounds
            
            second_round_base_locations = []
            
            desperately_overweight_locations = []
            overweight_locations = []
            available_locations = []
            starving_locations = []
            
            # first round, we need to sort out who is bust
            
            total_normalised_weight_lost_in_first_round = 0
            
            for base_location in all_media_base_locations:
                
                current_num_bytes = current_base_locations_to_size_estimate[ base_location ]
                
                if not base_location.AbleToAcceptSubfolders( current_num_bytes, smallest_subfolder_num_bytes ):
                    
                    if base_location.max_num_bytes is None:
                        
                        total_normalised_weight_lost_in_first_round = base_location.ideal_weight / total_ideal_weight
                        
                    else:
                        
                        total_normalised_weight_lost_in_first_round += base_location.max_num_bytes / hydrus_local_file_storage_total_size
                        
                    
                    if base_location.NeedsToRemoveSubfolders( current_num_bytes ):
                        
                        desperately_overweight_locations.append( base_location )
                        
                    
                else:
                    
                    second_round_base_locations.append( base_location )
                    
                
            
            # second round, let's distribute the remainder
            # I fixed some logic and it seems like everything here is now AbleToAccept, so maybe we want another quick pass on this
            # or just wait until I do the slow migration and we'll figure something out with the staticmethod on BaseLocation that just gets ideal weights
            # I also added this jank regarding / ( 1 - first_round_weight ), which makes sure we are distributing the remaining weight correctly
            
            second_round_total_ideal_weight = sum( ( base_location.ideal_weight for base_location in second_round_base_locations ) )
            
            for base_location in second_round_base_locations:
                
                current_normalised_weight = current_base_locations_to_normalised_weights[ base_location ]
                current_num_bytes = current_base_locations_to_size_estimate[ base_location ]
                
                # can be both overweight and able to eat more
                
                if base_location.WouldLikeToRemoveSubfolders( current_normalised_weight / ( 1 - total_normalised_weight_lost_in_first_round ), second_round_total_ideal_weight, largest_subfolder_normalised_weight ):
                    
                    overweight_locations.append( base_location )
                    
                
                if base_location.EagerToAcceptSubfolders( current_normalised_weight / ( 1 - total_normalised_weight_lost_in_first_round ), second_round_total_ideal_weight, smallest_subfolder_normalised_weight, current_num_bytes, smallest_subfolder_num_bytes ):
                    
                    starving_locations.append( base_location )
                    
                elif base_location.AbleToAcceptSubfolders( current_num_bytes, smallest_subfolder_num_bytes ):
                    
                    available_locations.append( base_location )
                    
                
            
            #
            
            desperately_overweight_locations.sort( key = lambda bl: self._GetFileStorageFreeSpace( bl ) )
            overweight_locations.sort( key = lambda bl: self._GetFileStorageFreeSpace( bl ) )
            available_locations.sort( key = lambda bl: - self._GetFileStorageFreeSpace( bl ) )
            starving_locations.sort( key = lambda bl: - self._GetFileStorageFreeSpace( bl ) )
            
            if len( desperately_overweight_locations ) > 0:
                
                potential_sources = desperately_overweight_locations
                potential_destinations = starving_locations + available_locations
                
            elif len( overweight_locations ) > 0:
                
                potential_sources = overweight_locations
                potential_destinations = starving_locations
                
            else:
                
                potential_sources = []
                potential_destinations = []
                
            
            if len( potential_sources ) > 0 and len( potential_destinations ) > 0:
                
                source_base_location = potential_sources.pop( 0 )
                destination_base_location = potential_destinations.pop( 0 )
                
                random.shuffle( file_prefixes )
                
                for file_prefix in file_prefixes:
                    
                    subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
                    
                    subfolder = subfolders[0]
                    
                    base_location = subfolder.base_location
                    
                    if base_location == source_base_location:
                        
                        overweight_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, source_base_location )
                        underweight_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, destination_base_location )
                        
                        return ( overweight_subfolder, underweight_subfolder )
                        
                    
                
            else:
                
                thumbnail_prefixes = [ prefix for prefix in self._prefixes_to_client_files_subfolders.keys() if prefix.startswith( 't' ) ]
                
                for thumbnail_prefix in thumbnail_prefixes:
                    
                    if ideal_thumbnail_override_base_location is None:
                        
                        file_prefix = 'f' + thumbnail_prefix[1:]
                        
                        if file_prefix in self._prefixes_to_client_files_subfolders:
                            
                            file_subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
                            
                        else:
                            
                            # TODO: Consider better that thumbs might not be split but files would.
                            # We need to better deal with t43 trying to find its place in f431, and t431 to f43, which means triggering splits or whatever (when we get to that code)
                            # Update: Yeah I've now moved to prefixes, and this looks even crazier
                            
                            file_subfolders = None
                            
                            for ( possible_file_prefix, possible_subfolders ) in self._prefixes_to_client_files_subfolders.items():
                                
                                if possible_file_prefix.startswith( file_prefix ) or file_prefix.startswith( possible_file_prefix ):
                                    
                                    file_subfolders = possible_subfolders
                                    
                                    break
                                    
                                
                            
                            if file_subfolders is None:
                                
                                # this shouldn't ever fire, and by the time I expect to split subfolders, all this code will work different anyway
                                # no way it could possibly go wrong
                                raise Exception( 'Had a problem trying to find a thumbnail migration location due to split subfolders! Let hydev know!' )
                                
                            
                        
                        file_subfolder = typing.cast( ClientFilesPhysical.FilesStorageSubfolder, file_subfolders[0] )
                        
                        correct_base_location = file_subfolder.base_location
                        
                    else:
                        
                        correct_base_location = ideal_thumbnail_override_base_location
                        
                    
                    subfolders = self._prefixes_to_client_files_subfolders[ thumbnail_prefix ]
                    
                    subfolder = subfolders[0]
                    
                    current_thumbnails_base_location = subfolder.base_location
                    
                    if current_thumbnails_base_location != correct_base_location:
                        
                        current_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, current_thumbnails_base_location )
                        correct_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, correct_base_location )
                        
                        return ( current_subfolder, correct_subfolder )
                        
                    
                
            
            return None
            
        except Exception as e:
            
            HydrusData.ShowText( 'Hey while calculating a potential rebalance job for the file migration system, I encountered this error. Please forward to hydev! Anonymising paths is fine, I just need to see the code.' )
            
            HydrusData.ShowException( e, do_wait = False )
            
            return None
            
        
    
    def _GetSubfolderForFile( self, hash: bytes, prefix_type: str ) -> ClientFilesPhysical.FilesStorageSubfolder:
        
        # TODO: So this will be a crux of the more complicated system
        # might even want a media result eventually, for various 'ah, because it is archived, it should go here'
        # for now it is a patch to navigate multiples into our currently mutually exclusive storage dataset
        
        # we probably need to break this guy into variants of 'getpossiblepaths' vs 'getidealpath' for different callers
        # getideal would be testing purge states and client files locations max num bytes stuff
        # there should, in all circumstances, be a place to put a file, so there should always be at least one non-num_bytes'd location with weight to handle 100% coverage of the spillover
        # if we are over the limit on the place the directory is supposed to be, I think we are creating a stub subfolder in the spillover place and writing there, but that'll mean saving a new subfolder, so be careful
        # maybe the spillover should always have 100% coverage no matter what, and num_bytes'd locations should always just have extensions. something to think about
        
        return self._GetPossibleSubfoldersForFile( hash, prefix_type )[0]
        
    
    def _HandleCriticalDriveError( self ):
        
        self._controller.new_options.SetBoolean( 'pause_import_folders_sync', True )
        self._controller.new_options.SetBoolean( 'pause_subs_sync', True )
        self._controller.new_options.SetBoolean( 'pause_all_file_queues', True )
        
        HydrusData.ShowText( 'A critical drive error has occurred. All importers--subscriptions, import folders, and paged file import queues--have been paused. Once the issue is clear, restart the client and resume your imports under the file and network menus!' )
        
        self._controller.pub( 'notify_refresh_network_menu' )
        self._controller.pub( 'notify_new_import_folders' )
        
    
    def _LookForFilePath( self, hash ):
        
        for potential_mime in HC.ALLOWED_MIMES:
            
            potential_path = self._GenerateExpectedFilePath( hash, potential_mime )
            
            if os.path.exists( potential_path ):
                
                return ( potential_path, potential_mime )
                
            
        
        subfolders = self._GetPossibleSubfoldersForFile( hash, 'f' )
        
        for subfolder in subfolders:
            
            if not subfolder.PathExists():
                
                raise HydrusExceptions.DirectoryMissingException( f'The directory {subfolder.path} was not found! Reconnect the missing location or shut down the client immediately!' )
                
            
        
        raise HydrusExceptions.FileMissingException( 'File for ' + hash.hex() + ' not found!' )
        
    
    def _Reinit( self ):
        
        self._ReinitSubfolders()
        
        if CG.client_controller.IsFirstStart():
            
            try:
                
                dirs_to_test = set()
                
                for subfolder in self._GetAllSubfolders():
                    
                    dirs_to_test.add( subfolder.base_location.path )
                    dirs_to_test.add( subfolder.path )
                    
                
                for dir_to_test in dirs_to_test:
                    
                    try:
                        
                        HydrusPaths.MakeSureDirectoryExists( dir_to_test )
                        
                    except:
                        
                        text = 'Attempting to create the database\'s client_files folder structure in {} failed!'.format( dir_to_test )
                        
                        self._controller.BlockingSafeShowCriticalMessage( 'unable to create file structure', text )
                        
                        raise
                        
                    
                
            except:
                
                text = 'Attempting to create the database\'s client_files folder structure failed!'
                
                self._controller.BlockingSafeShowCriticalMessage( 'unable to create file structure', text )
                
                raise
                
            
        else:
            
            self._ReinitMissingLocations()
            
            if len( self._missing_subfolders ) > 0:
                
                self._AttemptToHealMissingLocations()
                
                self._ReinitSubfolders()
                
                self._ReinitMissingLocations()
                
            
            if len( self._missing_subfolders ) > 0:
                
                self._bad_error_occurred = True
                
                #
                
                missing_dict = HydrusData.BuildKeyToListDict( [ ( subfolder.base_location, subfolder.prefix ) for subfolder in self._missing_subfolders ] )
                
                missing_base_locations = sorted( missing_dict.keys(), key = lambda b_l: b_l.path )
                
                missing_string = ''
                
                for missing_base_location in missing_base_locations:
                    
                    missing_prefixes = sorted( missing_dict[ missing_base_location ] )
                    
                    missing_prefixes_string = '    ' + '\n'.join( ( ', '.join( block ) for block in HydrusLists.SplitListIntoChunks( missing_prefixes, 32 ) ) )
                    
                    missing_string += '\n'
                    missing_string += str( missing_base_location )
                    missing_string += '\n'
                    missing_string += missing_prefixes_string
                    
                
                #
                
                if len( self._missing_subfolders ) > 4:
                    
                    HydrusData.DebugPrint( 'Missing locations follow:' )
                    HydrusData.DebugPrint( missing_string )
                    
                    text = 'When initialising the client files manager, some file locations did not exist! They have all been written to the log!'
                    text += '\n' * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'missing locations', text )
                    
                else:
                    
                    text = 'When initialising the client files manager, these file locations did not exist:'
                    text += '\n' * 2
                    text += missing_string
                    text += '\n' * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'missing locations', text )
                    
                
            
        
    
    def _ReinitSubfolders( self ):
        
        subfolders = self._controller.Read( 'client_files_subfolders' )
        
        self._prefixes_to_client_files_subfolders = collections.defaultdict( list )
        
        for subfolder in subfolders:
            
            self._prefixes_to_client_files_subfolders[ subfolder.prefix ].append( subfolder )
            
        
        all_subfolders = []
        
        for subfolders in self._prefixes_to_client_files_subfolders.values():
            
            all_subfolders.extend( subfolders )
            
        
        self._prefixes_to_rwlocks.clear()
        
    
    def _ReinitMissingLocations( self ):
        
        self._missing_subfolders = set()
        
        for subfolders in self._prefixes_to_client_files_subfolders.values():
            
            for subfolder in subfolders:
                
                if not subfolder.PathExists():
                    
                    self._missing_subfolders.add( subfolder )
                    
                
            
        
    
    def _WaitOnWakeup( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'file_system_waits_on_wakeup' ):
            
            while CG.client_controller.JustWokeFromSleep():
                
                HydrusThreading.CheckIfThreadShuttingDown()
                
                time.sleep( 1.0 )
                
            
        
    
    def AllLocationsAreDefault( self ):
        
        with self._master_locations_rwlock.read:
            
            db_dir = self._controller.GetDBDir()
            
            client_files_default = os.path.join( db_dir, 'client_files' )
            
            all_base_locations = self._GetCurrentSubfolderBaseLocations()
            
            return False not in ( location.path.startswith( client_files_default ) for location in all_base_locations )
            
        
    
    def LocklessAddFileFromBytes( self, hash, mime, file_bytes ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding file from string: ' + str( ( len( file_bytes ), dest_path ) ) )
            
        
        HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( file_bytes )
            
        
    
    def AddFile( self, hash, mime, source_path, thumbnail_bytes = None ):
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 'f' ).write:
                
                self._AddFile( hash, mime, source_path )
                
            
            if thumbnail_bytes is not None:
                
                with self._GetPrefixRWLock( hash, 't' ).write:
                    
                    self._AddThumbnailFromBytes( hash, thumbnail_bytes )
                    
                
            
        
    
    def AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 't' ).write:
                
                self._AddThumbnailFromBytes( hash, thumbnail_bytes, silent = silent )
                
            
        
    
    def ChangeFileExt( self, hash, old_mime, mime ):
        
        if old_mime == mime:
            
            return False
            
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 'f' ).write:
                
                return self._ChangeFileExt( hash, old_mime, mime )
                
            
        
    
    def ClearOrphans( self, move_location = None ):
        
        files_move_location = move_location
        thumbnails_move_location = None
        
        if move_location is not None:
            
            thumbnails_move_location = os.path.join( move_location, 'thumbnails' )
            
            HydrusPaths.MakeSureDirectoryExists( thumbnails_move_location )
            
        
        with self._master_locations_rwlock.read:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'clearing orphans' )
            job_status.SetStatusText( 'preparing' )
            
            self._controller.pub( 'message', job_status )
            
            orphan_paths = []
            orphan_thumbnails = []
            
            num_files_reviewed = 0
            num_thumbnails_reviewed = 0
            
            all_subfolders_in_order = sorted( self._prefixes_to_client_files_subfolders.items() )
            
            for ( prefix, subfolders ) in all_subfolders_in_order:
                
                with self._prefixes_to_rwlocks[ prefix ].write:
                    
                    job_status.SetStatusText( f'checking {prefix}' )
                    
                    for subfolder in subfolders:
                        
                        for path in subfolder.IterateAllFiles():
                            
                            ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                            
                            if should_quit:
                                
                                return
                                
                            
                            if subfolder.IsForFiles():
                                
                                if num_files_reviewed % 100 == 0:
                                    
                                    status = 'reviewed ' + HydrusNumbers.ToHumanInt( num_files_reviewed ) + ' files, found ' + HydrusNumbers.ToHumanInt( len( orphan_paths ) ) + ' orphans'
                                    
                                    job_status.SetStatusText( status, level = 2 )
                                    
                                
                            else:
                                
                                if num_thumbnails_reviewed % 100 == 0:
                                    
                                    status = 'reviewed ' + HydrusNumbers.ToHumanInt( num_thumbnails_reviewed ) + ' thumbnails, found ' + HydrusNumbers.ToHumanInt( len( orphan_thumbnails ) ) + ' orphans'
                                    
                                    job_status.SetStatusText( status, level = 2 )
                                    
                                
                            
                            try:
                                
                                ( directory, filename ) = os.path.split( path )
                                
                                should_be_a_hex_hash = filename[:64]
                                
                                hash = bytes.fromhex( should_be_a_hex_hash )
                                
                                orphan_type = 'file' if subfolder.IsForFiles() else 'thumbnail'
                                
                                is_an_orphan = CG.client_controller.Read( 'is_an_orphan', orphan_type, hash )
                                
                            except:
                                
                                is_an_orphan = True
                                
                            
                            if is_an_orphan:
                                
                                if move_location is not None:
                                    
                                    ( source_dir, filename ) = os.path.split( path )
                                    
                                    if subfolder.IsForFiles():
                                        
                                        dest = os.path.join( files_move_location, filename )
                                        
                                    else:
                                        
                                        dest = os.path.join( thumbnails_move_location, filename )
                                        
                                    
                                    dest = HydrusPaths.AppendPathUntilNoConflicts( dest )
                                    
                                    HydrusData.Print( 'Moving the orphan ' + path + ' to ' + dest )
                                    
                                    try:
                                        
                                        HydrusPaths.MergeFile( path, dest )
                                        
                                    except Exception as e:
                                        
                                        HydrusData.ShowText( f'Had trouble moving orphan from {path} to {dest}! Abandoning job!' )
                                        
                                        HydrusData.ShowException( e, do_wait = False )
                                        
                                        job_status.Cancel()
                                        
                                        return
                                        
                                    
                                
                                if subfolder.IsForFiles():
                                    
                                    orphan_paths.append( path )
                                    
                                else:
                                    
                                    orphan_thumbnails.append( path )
                                    
                                
                            
                            if subfolder.IsForFiles():
                                
                                num_files_reviewed += 1
                                
                            else:
                                
                                num_thumbnails_reviewed += 1
                                
                            
                        
                    
                
            
            job_status.SetStatusText( 'finished checking' )
            job_status.DeleteStatusText( level = 2 )
            
            time.sleep( 2 )
            
            if move_location is None:
                
                if len( orphan_paths ) > 0:
                    
                    status = 'found ' + HydrusNumbers.ToHumanInt( len( orphan_paths ) ) + ' orphan files, now deleting'
                    
                    job_status.SetStatusText( status )
                    
                    time.sleep( 5 )
                    
                    for ( i, path ) in enumerate( orphan_paths ):
                        
                        ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        HydrusData.Print( 'Deleting the orphan ' + path )
                        
                        status = 'deleting orphan files: ' + HydrusNumbers.ValueRangeToPrettyString( i + 1, len( orphan_paths ) )
                        
                        job_status.SetStatusText( status )
                        
                        ClientPaths.DeletePath( path )
                        
                    
                
                if len( orphan_thumbnails ) > 0:
                    
                    status = 'found ' + HydrusNumbers.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails, now deleting'
                    
                    job_status.SetStatusText( status )
                    
                    time.sleep( 5 )
                    
                    for ( i, path ) in enumerate( orphan_thumbnails ):
                        
                        ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        HydrusData.Print( 'Deleting the orphan ' + path )
                        
                        status = 'deleting orphan thumbnails: ' + HydrusNumbers.ValueRangeToPrettyString( i + 1, len( orphan_thumbnails ) )
                        
                        job_status.SetStatusText( status )
                        
                        ClientPaths.DeletePath( path, always_delete_fully = True )
                        
                    
                
            
            if len( orphan_paths ) == 0 and len( orphan_thumbnails ) == 0:
                
                final_text = 'no orphans found!'
                
            else:
                
                final_text = HydrusNumbers.ToHumanInt( len( orphan_paths ) ) + ' orphan files and ' + HydrusNumbers.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails cleared!'
                
            
            job_status.SetStatusText( final_text )
            
            HydrusData.Print( job_status.ToString() )
            
            job_status.Finish()
            
        
    
    def DeleteNeighbourDupes( self, hash, true_mime ):
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 'f' ).write:
                
                correct_path = self._GenerateExpectedFilePath( hash, true_mime )
                
                if not os.path.exists( correct_path ):
                    
                    return # misfire, let's not actually delete the right one
                    
                
                for mime in HC.ALLOWED_MIMES:
                    
                    if mime == true_mime:
                        
                        continue
                        
                    
                    incorrect_path = self._GenerateExpectedFilePath( hash, mime )
                    
                    if incorrect_path == correct_path:
                        
                        # some diff mimes have the same ext
                        
                        continue
                        
                    
                    if os.path.exists( incorrect_path ):
                        
                        delete_ok = HydrusPaths.DeletePath( incorrect_path )
                        
                        if not delete_ok and random.randint( 1, 52 ) != 52:
                            
                            self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusTime.GetNow() + ( 7 * 86400 ) )
                            
                        
                    
                
            
        
    
    def DoDeferredPhysicalDeletes( self ):
        
        wait_period = HydrusTime.SecondiseMSFloat( self._controller.new_options.GetInteger( 'ms_to_wait_between_physical_file_deletes' ) )
        
        num_files_deleted = 0
        num_thumbnails_deleted = 0
        
        while not HG.started_shutdown:
            
            with self._master_locations_rwlock.read:
                
                ( file_hash, thumbnail_hash ) = self._controller.Read( 'deferred_physical_delete' )
                
                if file_hash is None and thumbnail_hash is None:
                    
                    break
                    
                
                if file_hash is not None:
                    
                    with self._GetPrefixRWLock( file_hash, 'f' ).write:
                        
                        media_result = self._controller.Read( 'media_result', file_hash )
                        
                        expected_mime = media_result.GetMime()
                        
                        try:
                            
                            path = self._GenerateExpectedFilePath( file_hash, expected_mime )
                            
                            if not os.path.exists( path ):
                                
                                ( path, actual_mime ) = self._LookForFilePath( file_hash )
                                
                            
                            ClientPaths.DeletePath( path )
                            
                            num_files_deleted += 1
                            
                        except HydrusExceptions.FileMissingException:
                            
                            HydrusData.Print( 'Wanted to physically delete the "{}" file, with expected mime "{}", but it was not found!'.format( file_hash.hex(), HC.mime_string_lookup[ expected_mime ] ) )
                            
                        
                    
                
                if thumbnail_hash is not None:
                    
                    with self._GetPrefixRWLock( thumbnail_hash, 't' ).write:
                        
                        path = self._GenerateExpectedThumbnailPath( thumbnail_hash )
                        
                        if os.path.exists( path ):
                            
                            ClientPaths.DeletePath( path, always_delete_fully = True )
                            
                            num_thumbnails_deleted += 1
                            
                        
                    
                
                self._controller.WriteSynchronous( 'clear_deferred_physical_delete', file_hash = file_hash, thumbnail_hash = thumbnail_hash )
                
                if num_files_deleted % 10 == 0 or num_thumbnails_deleted % 10 == 0:
                    
                    self._controller.pub( 'notify_new_physical_file_delete_numbers' )
                    
                
            
            self._physical_file_delete_wait.wait( wait_period )
            
            self._physical_file_delete_wait.clear()
            
        
        if num_files_deleted > 0 or num_thumbnails_deleted > 0:
            
            self._controller.pub( 'notify_new_physical_file_delete_numbers' )
            
            HydrusData.Print( 'Physically deleted {} files and {} thumbnails from file storage.'.format( HydrusNumbers.ToHumanInt( num_files_deleted ), HydrusNumbers.ToHumanInt( num_files_deleted ) ) )
            
        
    
    def GetAllDirectoriesInUse( self ):
        
        with self._master_locations_rwlock.read:
            
            subfolders = self._GetAllSubfolders()
            
            directories = { subfolder.base_location.path for subfolder in subfolders }
            
        
        return directories
        
    
    def GetCurrentFileBaseLocations( self ):
        
        with self._master_locations_rwlock.read:
            
            return self._GetCurrentSubfolderBaseLocations( only_files = True )
            
        
    
    def GetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        with self._master_locations_rwlock.read:
            
            if HG.file_report_mode:
                
                HydrusData.ShowText( 'File path request: ' + str( ( hash, mime ) ) )
                
            
            with self._GetPrefixRWLock( hash, 'f' ).read:
                
                if mime is None:
                    
                    ( path, mime ) = self._LookForFilePath( hash )
                    
                else:
                    
                    path = self._GenerateExpectedFilePath( hash, mime )
                    
                    if check_file_exists and not os.path.exists( path ):
                        
                        try:
                            
                            # let's see if the file exists, but with the wrong ext!
                            
                            ( actual_path, old_mime ) = self._LookForFilePath( hash )
                            
                        except HydrusExceptions.FileMissingException:
                            
                            raise HydrusExceptions.FileMissingException( 'No file found at path {}!'.format( path ) )
                            
                        
                        self._ChangeFileExt( hash, old_mime, mime )
                        
                        # we have now fixed the path, it is good to return
                        
                    
                
                return path
                
            
        
    
    def GetMissingSubfolders( self ):
        
        return self._missing_subfolders
        
    
    def GetAllSubfolders( self ) -> collections.abc.Collection[ ClientFilesPhysical.FilesStorageSubfolder ]:
        
        with self._master_locations_rwlock.read:
            
            return self._GetAllSubfolders()
            
        
    
    def GetThumbnailPath( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path request: ' + str( ( hash, mime ) ) )
            
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 't' ).read:
                
                path = self._GenerateExpectedThumbnailPath( hash )
                
                thumb_missing = not os.path.exists( path )
                
            
        
        if thumb_missing:
            
            self.RegenerateThumbnail( media_result )
            
        
        return path
        
    
    def LocklessHasFile( self, hash, mime ):
        
        path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'File path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def LocklessHasThumbnail( self, hash ):
        
        path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def Rebalance( self, job_status ):
        
        try:
            
            if self._bad_error_occurred:
                
                HydrusData.ShowText( 'A serious file error has previously occurred during this session, so further file moving will not be reattempted. Please restart the client before trying again.' )
                
                return
                
            
            with self._master_locations_rwlock.write:
                
                rebalance_tuple = self._GetRebalanceTuple()
                
                while rebalance_tuple is not None:
                    
                    if job_status.IsCancelled():
                        
                        break
                        
                    
                    ( source_subfolder, dest_subfolder ) = rebalance_tuple
                    
                    text = f'Moving "{source_subfolder}" to "{dest_subfolder}".'
                    
                    HydrusData.Print( text )
                    
                    job_status.SetStatusText( text )
                    
                    # these two lines can cause a deadlock because the db sometimes calls stuff in here.
                    self._controller.WriteSynchronous( 'relocate_client_files', source_subfolder, dest_subfolder )
                    
                    self._Reinit()
                    
                    rebalance_tuple = self._GetRebalanceTuple()
                    
                    time.sleep( 0.01 )
                    
                
            
        finally:
            
            job_status.SetStatusText( 'done!' )
            
            job_status.FinishAndDismiss()
            
        
    
    def RebalanceWorkToDo( self ):
        
        with self._master_locations_rwlock.read:
            
            return self._GetRebalanceTuple() is not None
            
        
    
    def RegenerateThumbnail( self, media_result ):
        
        if not media_result.GetLocationsManager().IsLocal():
            
            raise HydrusExceptions.FileMissingException( 'I was called to regenerate a thumbnail from source, but the source file does not think it is in the local file store!' )
            
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 'f' ).read:
                
                file_path = self._GenerateExpectedFilePath( hash, mime )
                
                if not os.path.exists( file_path ):
                    
                    raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file because the original file is missing! This event could indicate hard drive corruption. Please check everything is ok.')
                    
                
            
            # in another world I do this inside the file read lock, but screw it I'd rather have the time spent outside
            thumbnail_bytes = self._GenerateThumbnailBytes( file_path, media_result )
            
            with self._GetPrefixRWLock( hash, 't' ).write:
                
                self._AddThumbnailFromBytes( hash, thumbnail_bytes )
                
            
        
        return True
        
    
    def RegenerateThumbnailIfWrongSize( self, media_result ):
        
        do_it = False
        
        try:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            if mime not in HC.MIMES_WITH_THUMBNAILS:
                
                return
                
            
            ( media_width, media_height ) = media_result.GetResolution()
            
            path = self._GenerateExpectedThumbnailPath( hash )
            
            if not os.path.exists( path ):
                
                raise Exception()
                
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( path )
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( path, thumbnail_mime )
            
            ( current_width, current_height ) = HydrusImageHandling.GetResolutionNumPy( numpy_image )
            
            bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( (media_width, media_height), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
            
            if current_width != expected_width or current_height != expected_height:
                
                do_it = True
                
            
        except:
            
            do_it = True
            
        
        if do_it:
            
            self.RegenerateThumbnail( media_result )
            
        
        return do_it
        
    
    def Reinit( self ):
        
        # this is still useful to hit on ideals changing, since subfolders bring the weight and stuff of those settings. we'd rather it was generally synced
        self._Reinit()
        
    
    def UpdateFileModifiedTimestampMS( self, media, modified_timestamp_ms: int ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        with self._master_locations_rwlock.read:
            
            with self._GetPrefixRWLock( hash, 'f' ).write:
                
                path = self._GenerateExpectedFilePath( hash, mime )
                
                if os.path.exists( path ):
                    
                    existing_access_time = os.path.getatime( path )
                    existing_modified_time = os.path.getmtime( path )
                    
                    # floats are ok here!
                    modified_timestamp = HydrusTime.SecondiseMSFloat( modified_timestamp_ms )
                    
                    try:
                        
                        os.utime( path, ( existing_access_time, modified_timestamp ) )
                        
                        HydrusData.Print( 'Successfully changed modified time of "{}" from {} to {}.'.format( path, HydrusTime.TimestampToPrettyTime( int( existing_modified_time ) ), HydrusTime.TimestampToPrettyTime( int( modified_timestamp ) ) ))
                        
                    except PermissionError:
                        
                        HydrusData.Print( 'Tried to set modified time of {} to file "{}", but did not have permission!'.format( HydrusTime.TimestampToPrettyTime( int( modified_timestamp ) ), path ) )
                        
                    
                
            
        
    
    def shutdown( self ):
        
        self._physical_file_delete_wait.set()
        
    
