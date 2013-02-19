# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.

import os
from include import HydrusConstants as HC
from include import ServerController

try:
    
    app = ServerController.Controller( True, HC.LOGS_DIR + os.path.sep + 'server.log' )
    
    app.MainLoop()
    
except:
    
    import traceback
    print( traceback.format_exc() )
    

try: HC.shutdown = True
except: pass

HC.pubsub.pubimmediate( 'shutdown' )
