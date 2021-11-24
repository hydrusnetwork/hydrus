from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC

PRESENTATION_LOCATION_IN_LOCAL_FILES = 0
PRESENTATION_LOCATION_IN_TRASH_TOO = 1

presentation_location_enum_str_lookup = {
    PRESENTATION_LOCATION_IN_LOCAL_FILES : 'in my collection',
    PRESENTATION_LOCATION_IN_TRASH_TOO : 'in my collection or trash'
}

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
PRESENTATION_INBOX_INCLUDE_INBOX = 2

presentation_inbox_enum_str_lookup = {
    PRESENTATION_INBOX_AGNOSTIC : 'inbox or archive',
    PRESENTATION_INBOX_REQUIRE_INBOX : 'must be in inbox',
    PRESENTATION_INBOX_INCLUDE_INBOX : 'or in inbox'
}

class PresentationImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PRESENTATION_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Presentation Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._presentation_location = PRESENTATION_LOCATION_IN_LOCAL_FILES
        self._presentation_status = PRESENTATION_STATUS_ANY_GOOD
        self._presentation_inbox = PRESENTATION_INBOX_AGNOSTIC
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PresentationImportOptions ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._presentation_location, self._presentation_status, self._presentation_inbox ).__hash__()
        
    
    def _DefinitelyShouldNotPresentIgnorantOfInbox( self, status ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return True
            
        
        if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT and self._presentation_inbox != PRESENTATION_INBOX_INCLUDE_INBOX:
                
                # only want new, and this is already in db
                
                return True
                
            
        
        return False
        
    
    def _DefinitelyShouldPresentIgnorantOfInbox( self, status ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return False
            
        
        if self._presentation_inbox == PRESENTATION_INBOX_REQUIRE_INBOX:
            
            # we can't know either way
            
            return False
            
        
        if self._presentation_status == PRESENTATION_STATUS_ANY_GOOD:
            
            # we accept all
            
            return True
            
        elif self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                
                # we accept all new and this is new
                
                return True
                
            
        
        return False
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._presentation_location, self._presentation_status, self._presentation_inbox )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._presentation_location, self._presentation_status, self._presentation_inbox ) = serialisable_info
        
    
    def _ShouldPresentGivenStatusAndInbox( self, status, inbox ):
        
        if self._presentation_status == PRESENTATION_STATUS_NONE:
            
            return False
            
        
        if self._presentation_inbox == PRESENTATION_INBOX_REQUIRE_INBOX:
            
            if not inbox:
                
                return False
                
            
        
        #
        
        if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
            
            if status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                
                if self._presentation_inbox == PRESENTATION_INBOX_AGNOSTIC:
                    
                    # only want new, and this is already in db
                    
                    return False
                    
                elif self._presentation_inbox == PRESENTATION_INBOX_INCLUDE_INBOX:
                    
                    if not inbox:
                        
                        # only want new or inbox, and this is already in db and archived
                        
                        return False
                        
                    
                
            
        
        return True
        
    
    def GetPresentationInbox( self ) -> int:
        
        return self._presentation_inbox
        
    
    def GetPresentationLocation( self ) -> int:
        
        return self._presentation_location
        
    
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
                
            
        elif self._presentation_inbox == PRESENTATION_INBOX_INCLUDE_INBOX:
            
            if self._presentation_status == PRESENTATION_STATUS_NEW_ONLY:
                
                summary = 'new or inbox files'
                
            
        
        if self._presentation_location == PRESENTATION_LOCATION_IN_TRASH_TOO:
            
            summary = '{}, including trash'.format( summary )
            
        
        return summary
        
    
    def SetPresentationInbox( self, presentation_inbox: int ):
        
        self._presentation_inbox = presentation_inbox
        
    
    def SetPresentationLocation( self, presentation_location: int ):
        
        self._presentation_location = presentation_location
        
    
    def SetPresentationStatus( self, presentation_status: int ):
        
        self._presentation_status = presentation_status
        
    
    def GetPresentedHashes( self, hashes_and_statuses, should_check_location = True ):
        
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
            
            inbox_hashes = HG.client_controller.Read( 'inbox_hashes', needs_inbox_lookup )
            
            for ( hash, status ) in hashes_and_statuses:
                
                if hash in hashes_handled:
                    
                    continue
                    
                
                in_inbox = hash in inbox_hashes
                
                if self._ShouldPresentGivenStatusAndInbox( status, in_inbox ):
                    
                    desired_hashes.add( hash )
                    
                
                hashes_handled.add( hash )
                
            
        
        presented_hashes = [ hash for ( hash, status ) in hashes_and_statuses if hash in desired_hashes ]
        
        if len( presented_hashes ) > 0 and should_check_location:
            
            file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
            if self._presentation_location == PRESENTATION_LOCATION_IN_TRASH_TOO:
                
                file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
            presented_hashes = HG.client_controller.Read( 'filter_hashes', file_service_key, presented_hashes )
            
        
        return presented_hashes
        
    
    def ShouldPresentHashAndStatus( self, hash, status, should_check_location = True ):
        
        hashes = self.GetPresentedHashes( [ ( hash, status ) ], should_check_location = should_check_location )
        
        return len( hashes ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PRESENTATION_IMPORT_OPTIONS ] = PresentationImportOptions
