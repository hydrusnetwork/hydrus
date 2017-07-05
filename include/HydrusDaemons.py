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
    
def DAEMONMaintainMemoryFast( controller ):
    
    controller.pub( 'memory_maintenance_pulse' )
    
def DAEMONMaintainMemorySlow( controller ):
    
    controller.MaintainMemorySlow()
    
def DAEMONSleepCheck( controller ):
    
    controller.SleepCheck()
    
