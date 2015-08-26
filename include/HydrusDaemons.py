import HydrusConstants as HC
import HydrusExceptions
import os
import sys
import threading
import time
import traceback
import HydrusData
import HydrusGlobals

def DAEMONMaintainDB():
    
    if HydrusGlobals.controller.CurrentlyIdle():
        
        HydrusGlobals.controller.MaintainDB()
        
    
def DAEMONMaintainMemory():
    
    HydrusGlobals.controller.MaintainMemory()
    
def DAEMONSleepCheck():
    
    HydrusGlobals.controller.SleepCheck()
    