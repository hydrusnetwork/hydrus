import typing

if typing.TYPE_CHECKING:
    
    from hydrus.client import ClientController
    

client_controller: typing.Optional[ "ClientController.Controller" ] = None
