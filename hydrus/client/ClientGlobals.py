import typing

if typing.TYPE_CHECKING:
    
    from hydrus.client import ClientController
    

client_controller: "ClientController.Controller | None" = None
