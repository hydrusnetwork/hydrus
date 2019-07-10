import os
import traceback

class HydrusException( Exception ):
    
    def __str__( self ):
        
        return os.linesep.join( self.args )
        
    
class CantRenderWithCVException( HydrusException ): pass
class DataMissing( HydrusException ): pass

class DBException( HydrusException ): pass
class DBAccessException( HydrusException ): pass
class FileMissingException( HydrusException ): pass
class DirectoryMissingException( HydrusException ): pass
class SerialisationException( HydrusException ): pass
class NameException( HydrusException ): pass
class ShutdownException( HydrusException ): pass
class WXDeadWindowException( HydrusException ): pass

class VetoException( HydrusException ): pass
class CancelledException( VetoException ): pass
class MimeException( VetoException ): pass
class SizeException( VetoException ): pass
class DecompressionBombException( SizeException ): pass

class ParseException( HydrusException ): pass
class StringConvertException( ParseException ): pass
class StringMatchException( ParseException ): pass
class URLClassException( ParseException ): pass
class GUGException( ParseException ): pass

class NetworkException( HydrusException ): pass

class NetworkInfrastructureException( NetworkException ): pass
class ConnectionException( NetworkInfrastructureException ): pass
class FirewallException( NetworkInfrastructureException ): pass
class ServerBusyException( NetworkInfrastructureException ): pass

class BandwidthException( NetworkException ): pass
class NetworkVersionException( NetworkException ): pass
class NoContentException( NetworkException ): pass
class NotFoundException( NetworkException ): pass
class NotModifiedException( NetworkException ): pass
class BadRequestException( NetworkException ): pass
class MissingCredentialsException( NetworkException ): pass
class DoesNotSupportCORSException( NetworkException ): pass
class InsufficientCredentialsException( NetworkException ): pass
class RedirectionException( NetworkException ): pass
class ServerException( NetworkException ): pass
class SessionException( NetworkException ): pass
class WrongServiceTypeException( NetworkException ): pass
class ValidationException( NetworkException ): pass
class ShouldReattemptNetworkException( NetworkException ): pass
