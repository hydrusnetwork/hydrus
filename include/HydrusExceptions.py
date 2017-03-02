import os

class CancelledException( Exception ): pass
class CantRenderWithCVException( Exception ): pass
class DataMissing( Exception ): pass

class DBException( Exception ):
    
    def __str__( self ):
        
        return os.linesep.join( self.args )
        

class DBAccessException( Exception ): pass
class FileMissingException( Exception ): pass
class MimeException( Exception ): pass
class NameException( Exception ): pass
class ShutdownException( Exception ): pass
class SizeException( Exception ): pass
class VetoException( Exception ): pass

class NetworkException( Exception ): pass
class BandwidthException( NetworkException ): pass
class FirewallException( NetworkException ): pass
class ForbiddenException( NetworkException ): pass
class NetworkVersionException( NetworkException ): pass
class NoContentException( NetworkException ): pass
class NotFoundException( NetworkException ): pass
class NotModifiedException( NetworkException ): pass
class PermissionException( NetworkException ): pass
class RedirectionException( NetworkException ): pass
class ServerBusyException( NetworkException ): pass
class SessionException( NetworkException ): pass
class WrongServiceTypeException( NetworkException ): pass
class ShouldReattemptNetworkException( NetworkException ): pass
