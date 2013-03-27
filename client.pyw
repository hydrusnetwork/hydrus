# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.

import string
string.whitespace
# this is some woo woo - if you call it after the locale, it has 0xa0 (non-breaking space) (non-ascii!!) included
# if you call it before, the locale call doesn't update
# what a mess!

import locale
print( locale.setlocale( locale.LC_ALL, '' ) )


import os
from include import HydrusConstants as HC
from include import ClientController

try:
    
    app = ClientController.Controller( True, HC.LOGS_DIR + os.path.sep + 'client.log' )
    
    app.MainLoop()
    
except:
    
    import traceback
    print( traceback.format_exc() )
    

HC.shutdown = True

HC.pubsub.pubimmediate( 'shutdown' )
