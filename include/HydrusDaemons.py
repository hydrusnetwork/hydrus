import HydrusConstants as HC
import HydrusExceptions
import os
import sys
import threading
import time
import traceback
import HydrusData

def DAEMONMaintainDB( controller ):
    
    controller.MaintainDB()
    
