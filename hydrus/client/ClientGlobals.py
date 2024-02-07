import typing

from hydrus.client.interfaces import ClientControllerInterface

# TODO: move all HG.client_controller references here, and the various like 'mpv report mode' stuff
# make a ServerGlobals too, I think!
client_controller: typing.Optional[ ClientControllerInterface.ClientControllerInterface ] = None
