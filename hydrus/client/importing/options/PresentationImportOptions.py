from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation

PRESENTATION_STATUS_ANY_GOOD = 0
PRESENTATION_STATUS_NEW_ONLY = 1
PRESENTATION_STATUS_NONE = 2

presentation_status_enum_str_lookup = {
    PRESENTATION_STATUS_ANY_GOOD : 'all files',
    PRESENTATION_STATUS_NEW_ONLY : 'new files',
    PRESENTATION_STATUS_NONE : 'do not show anything'
}

PRESENTATION_INBOX_AGNOSTIC = 0
PRESENTATION_INBOX_REQUIRE_INBOX = 1
PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX = 2

presentation_inbox_enum_str_lookup = {
    PRESENTATION_INBOX_AGNOSTIC : 'inbox or archive',
    PRESENTATION_INBOX_REQUIRE_INBOX : 'must be in inbox',
    PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX : 'or in inbox'
}

class PresentationImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PRESENTATION_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Presentation Import Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        self._presentation_status = PRESENTATION_STATUS_ANY_GOOD
        self._presentation_inbox = PRESENTATION_INBOX_AGNOSTIC
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PresentationImportOptions ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._location_context.__hash__(), self._presentation_status, self._presentation_inbox ).__hash__()
        
    
    def _DefinitelyShouldNotPresentIgnorantOfInbox( self, status ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return True
            
        
        if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status != CC.STATUS_SUCCESSFUL_AND_NEW and self._presentation_inbox != PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX:
                
                # only want new, and this isn't
                
                return True
                
            
        
        
        return False
        
    
    def _DefinitelyShouldPresentIgnorantOfInbox( self, status ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return False
            
        
        if self._presentation_inbox == PRESENTATION_INBOX_REQUIRE_INBOX:
            
            # we can't know either way
            
            return False
            
        
        #
        
        if self._presentation_status == PRESENTATION_STATUS_ANY_GOOD:
            
            # we accept all
            
            return True
            
        elif self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                
                # we accept all new and this is new
                
                return True
                
            
        
        return False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_location_context = self._location_context.GetSerialisableTuple()
        
        return ( serialisable_location_context, self._presentation_status, self._presentation_inbox )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_location_context, self._presentation_status, self._presentation_inbox ) = serialisable_info
        
        self._location_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_location_context )
        
    
    def _ShouldPresentGivenStatusAndInbox( self, status, inbox ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return False
            
        
        if self._presentation_inbox == PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX:
            
            if inbox:
                
                return True
                
            
        elif self._presentation_inbox == PRESENTATION_INBOX_REQUIRE_INBOX:
            
            if not inbox:
                
                return False
                
            
        
        #
        
        if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status != CC.STATUS_SUCCESSFUL_AND_NEW:
                
                return False
                
            
        
        return True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( presentation_location, presentation_status, presentation_inbox ) = old_serialisable_info
            
            #PRESENTATION_LOCATION_IN_LOCAL_FILES = 0
            #PRESENTATION_LOCATION_IN_TRASH_TOO = 1
            
            if presentation_location == 1:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
                
            else:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                
            
            serialisable_location_context = location_context.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_location_context, presentation_status, presentation_inbox )
            
            return ( 2, new_serialisable_info )
            
        
    def GetPresentationInbox( self ) -> int:
        
        return self._presentation_inbox
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._location_context
        
    
    def GetPresentationStatus( self ) -> int:
        
        return self._presentation_status
        
    
    def GetSummary( self ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return 'not presenting any files'
            
        
        summary = presentation_status_enum_str_lookup[ self._presentation_status ]
        
        if self._presentation_inbox == PRESENTATION_INBOX_REQUIRE_INBOX:
            
            if self._presentation_status == PRESENTATION_STATUS_ANY_GOOD:
                
                summary = 'inbox files'
                
            else:
                
                summary = 'new inbox files'
                
            
        elif self._presentation_inbox == PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX:
            
            if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
                
                summary = 'new or inbox files'
                
            
        elif self._presentation_inbox == PRESENTATION_INBOX_AGNOSTIC:
            
            if self._presentation_status == PRESENTATION_STATUS_ANY_GOOD:
                
                summary = 'all files'
                
            elif self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
                
                summary = 'new files'
                
            
        
        if not self._location_context.IsCombinedLocalFileDomains():
            
            if self._location_context.IsHydrusLocalFileStorage():
                
                s = 'including if trashed'
                
            else:
                
                s = 'in {}'.format( self._location_context.ToString( CG.client_controller.services_manager.GetName ) )
                
            
            summary = '{}, {}'.format( summary, s )
            
        
        summary = 'presenting {}'.format( summary )
        
        return summary
        
    
    def SetPresentationInbox( self, presentation_inbox: int ):
        
        self._presentation_inbox = presentation_inbox
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetPresentationStatus( self, presentation_status: int ):
        
        self._presentation_status = presentation_status
        
    
    def GetPresentedHashes( self, hashes_and_statuses, location_context_override = None ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return []
            
        
        hashes_handled = set()
        needs_inbox_lookup = set()
        desired_hashes = set()
        
        for ( hash, status ) in hashes_and_statuses:
            
            if hash in hashes_handled:
                
                continue
                
            
            if status not in CC.SUCCESSFUL_IMPORT_STATES:
                
                hashes_handled.add( hash )
                
                continue
                
            
            if self._DefinitelyShouldNotPresentIgnorantOfInbox( status ):
                
                hashes_handled.add( hash )
                
                continue
                
            
            if self._DefinitelyShouldPresentIgnorantOfInbox( status ):
                
                hashes_handled.add( hash )
                desired_hashes.add( hash )
                
                continue
                
            
            needs_inbox_lookup.add( hash )
            
        
        if len( needs_inbox_lookup ) > 0:
            
            inbox_hashes = CG.client_controller.Read( 'inbox_hashes', needs_inbox_lookup )
            
            for ( hash, status ) in hashes_and_statuses:
                
                if hash in hashes_handled:
                    
                    continue
                    
                
                in_inbox = hash in inbox_hashes
                
                if self._ShouldPresentGivenStatusAndInbox( status, in_inbox ):
                    
                    desired_hashes.add( hash )
                    
                
                hashes_handled.add( hash )
                
            
        
        presented_hashes = [ hash for ( hash, status ) in hashes_and_statuses if hash in desired_hashes ]
        
        if len( presented_hashes ) > 0:
            
            if location_context_override is None:
                
                location_context = self._location_context
                
            else:
                
                location_context = location_context_override
                
            
            if not location_context.IsAllKnownFiles():
                
                presented_hashes = CG.client_controller.Read( 'filter_hashes', location_context, presented_hashes )
                
            
        
        return presented_hashes
        
    
    def ShouldPresentHashAndStatus( self, hash, status, should_check_location = True ):
        
        location_context_override = None if should_check_location else ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
        
        hashes = self.GetPresentedHashes( [ ( hash, status ) ], location_context_override = location_context_override )
        
        return len( hashes ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PRESENTATION_IMPORT_OPTIONS ] = PresentationImportOptions
