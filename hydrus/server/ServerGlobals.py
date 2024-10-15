import typing

if typing.TYPE_CHECKING:
    
    from hydrus.server import ServerController
    

server_controller: typing.Optional[ "ServerController.Controller" ] = None
