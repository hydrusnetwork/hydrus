import os
import traceback

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTemp
from hydrus.core import HydrusText
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client.files.images import ClientImagePerceptualHashes
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientFileMigration
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedAddFiles( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_FILES )
        
    

class HydrusResourceClientAPIRestrictedAddFilesAddFile( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        path = None
        delete_after_successful_import = False
        
        if not hasattr( request, 'temp_file_info' ):
            
            # ok the caller has not sent us a file in the POST content, we have a 'path'
            
            path = request.parsed_request_args.GetValue( 'path', str )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" does not exist!'.format( path ) )
                
            
            if not os.path.isfile( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" is not a file!'.format( path ) )
                
            
            delete_after_successful_import = request.parsed_request_args.GetValue( 'delete_after_successful_import', bool, default_value = False )
            
            ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            HydrusPaths.MirrorFile( path, temp_path )
            
        
        ( os_file_handle, temp_path ) = request.temp_file_info
        
        file_import_options = CG.client_controller.new_options.GetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_QUIET ).Duplicate()
        
        custom_location_context = ClientLocalServerCore.ParseLocalFileDomainLocationContext( request )
        
        if custom_location_context is not None:
            
            file_import_options.SetDestinationLocationContext( custom_location_context )
            
        
        file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options, human_file_description = f'API POSTed File' )
        
        body_dict = {}
        
        try:
            
            file_import_status = file_import_job.DoWork()
            
        except Exception as e:
            
            if isinstance( e, ( HydrusExceptions.VetoException, HydrusExceptions.UnsupportedFileException ) ):
                
                note = str( e )
                
            else:
                
                note = HydrusText.GetFirstLine( repr( e ) )
                
            
            file_import_status = ClientImportFiles.FileImportStatus( CC.STATUS_ERROR, file_import_job.GetHash(), note = note )
            
            body_dict[ 'traceback' ] = traceback.format_exc()
            
        
        if path is not None:
            
            if delete_after_successful_import and file_import_status.status in CC.SUCCESSFUL_IMPORT_STATES:
                
                ClientPaths.DeletePath( path )
                
            
        
        body_dict[ 'status' ] = file_import_status.status
        body_dict[ 'hash' ] = HydrusData.BytesToNoneOrHex( file_import_status.hash )
        body_dict[ 'note' ] = file_import_status.note
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesArchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    


class HydrusResourceClientAPIRestrictedAddFilesClearDeletedFileRecord( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        media_results = CG.client_controller.Read( 'media_results', hashes )
        
        media_results = [ media_result for media_result in media_results if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in media_result.GetLocationsManager().GetDeleted() ]
        
        clearee_hashes = { m.GetHash() for m in media_results }
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, clearee_hashes )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
        
        CG.client_controller.Write( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesDeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ClientLocalServerCore.ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ), deleted_allowed = False )
        
        if 'reason' in request.parsed_request_args:
            
            reason = request.parsed_request_args.GetValue( 'reason', str )
            
        else:
            
            reason = 'Deleted via Client API.'
            
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        location_context.LimitToServiceTypes( CG.client_controller.services_manager.GetServiceType, ( HC.COMBINED_LOCAL_FILE, HC.COMBINED_LOCAL_MEDIA, HC.LOCAL_FILE_DOMAIN ) )
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in location_context.current_service_keys:
            
            media_results = CG.client_controller.Read( 'media_results', hashes )
            
            undeletable_media_results = [ m for m in media_results if m.IsPhysicalDeleteLocked() ]
            
            if len( undeletable_media_results ) > 0:
                
                message = 'Sorry, some of the files you selected are currently delete locked. Their hashes are:'
                message += '\n' * 2
                message += '\n'.join( sorted( [ m.GetHash().hex() for m in undeletable_media_results ] ) )
                
                raise HydrusExceptions.ConflictException( message )
                
            
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = reason )
        
        for service_key in location_context.current_service_keys:
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesMigrateFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        location_context = ClientLocalServerCore.ParseLocalFileDomainLocationContext( request )
        
        if location_context is None:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you need to set a destination for the migration!' )
            
        
        media_results = CG.client_controller.Read( 'media_results', hashes )
        
        for media_result in media_results:
            
            if not CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent():
                
                raise HydrusExceptions.BadRequestException( f'The file "{media_result.GetHash().hex()} is not in any local file domains, so I cannot copy!' )
                
            
        
        for service_key in location_context.current_service_keys:
            
            CG.client_controller.CallToThread( ClientFileMigration.DoMoveOrDuplicateLocalFiles, service_key, HC.CONTENT_UPDATE_ADD, media_results )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesUnarchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesUndeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ClientLocalServerCore.ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        location_context.LimitToServiceTypes( CG.client_controller.services_manager.GetServiceType, ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_MEDIA ) )
        
        media_results = CG.client_controller.Read( 'media_results', hashes )
        
        # this is the only scan I have to do. all the stuff like 'can I undelete from here' and 'what does an undelete to combined local media mean' is all sorted at the db level no worries
        media_results = [ media_result for media_result in media_results if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent() ]
        
        hashes = { media_result.GetHash() for media_result in media_results }
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes )
        
        for service_key in location_context.current_service_keys:
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddFilesGenerateHashes( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not hasattr( request, 'temp_file_info' ):
            
            path = request.parsed_request_args.GetValue( 'path', str )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" does not exist!'.format( path ) )
                
            
            if not os.path.isfile( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" is not a file!'.format( path ) )
                
            
            ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            HydrusPaths.MirrorFile( path, temp_path )
            
        
        ( os_file_handle, temp_path ) = request.temp_file_info
        
        mime = HydrusFileHandling.GetMime( temp_path )
        
        body_dict = {}
        
        sha256_hash = HydrusFileHandling.GetHashFromPath( temp_path )
        
        body_dict[ 'hash' ] = sha256_hash.hex()
        
        if mime in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH or mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH:
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( temp_path, mime )
            
            if mime in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
                
                perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashesNumPy( numpy_image )
                
                body_dict[ 'perceptual_hashes' ] = [ perceptual_hash.hex() for perceptual_hash in perceptual_hashes ]
                
            
            if mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH:
                
                pixel_hash = HydrusImageHandling.GetImagePixelHashNumPy( numpy_image )
                
                body_dict[ 'pixel_hash' ] = pixel_hash.hex()
                
            
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
