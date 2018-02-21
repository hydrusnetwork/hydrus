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
class DecompressionBombException( SizeException ): pass
class VetoException( Exception ): pass

class ParseException( Exception ): pass
class StringConvertException( ParseException ): pass
class StringMatchException( ParseException ): pass
class URLMatchException( ParseException ): pass

class NetworkException( Exception ): pass

class NetworkInfrastructureException( NetworkException ): pass
class ConnectionException( NetworkInfrastructureException ): pass
class FirewallException( NetworkInfrastructureException ): pass
class ServerBusyException( NetworkInfrastructureException ): pass

class BandwidthException( NetworkException ): pass
class ForbiddenException( NetworkException ): pass
class LoginException( NetworkException ): pass
class NetworkVersionException( NetworkException ): pass
class NoContentException( NetworkException ): pass
class NotFoundException( NetworkException ): pass
class NotModifiedException( NetworkException ): pass
class PermissionException( NetworkException ): pass
class RedirectionException( NetworkException ): pass
class ServerException( NetworkException ): pass
class SessionException( NetworkException ): pass
class WrongServiceTypeException( NetworkException ): pass
class ValidationException( NetworkException ): pass
class ShouldReattemptNetworkException( NetworkException ): pass
