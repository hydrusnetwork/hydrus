class DBException( Exception ):
    
    def __init__( self, text, caller_traceback, db_traceback ):
        
        Exception.__init__( self, text )
        
        self._caller_traceback = caller_traceback
        self._db_traceback = db_traceback
        
    
    def GetTracebacks( self ): return ( self._caller_traceback, self._db_traceback )
    
class DBAccessException( Exception ): pass
class FileException( Exception ): pass
class ForbiddenException( Exception ): pass
class MimeException( Exception ): pass
class NetworkVersionException( Exception ): pass
class NoContentException( Exception ): pass
class NotFoundException( Exception ): pass
class NotModifiedException( Exception ): pass
class PermissionException( Exception ): pass
class SessionException( Exception ): pass
class ShutdownException( Exception ): pass
class SizeException( Exception ): pass
class WrongServiceTypeException( Exception ): pass
