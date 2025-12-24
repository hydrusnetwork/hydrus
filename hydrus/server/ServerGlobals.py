import typing

if typing.TYPE_CHECKING:
    
    from hydrus.server import ServerController
    

server_controller: "ServerController.Controller | None" = None
