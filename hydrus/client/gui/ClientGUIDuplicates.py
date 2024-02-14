import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick

def ClearFalsePositives( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to clear this file of its false-positive relations?'
        message += os.linesep * 2
        message += 'False-positive relations are recorded between alternate groups, so this change will also affect any files this file is alternate to.'
        message += os.linesep * 2
        message += 'All affected files will be queued up for another potential duplicates search, so you will likely see at least one of them again in the duplicate filter.'
        
    else:
        
        message = 'Are you sure you want to clear these {} files of their false-positive relations?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'False-positive relations are recorded between alternate groups, so this change will also affect all alternate files to your selection.'
        message += os.linesep * 2
        message += 'All affected files will be queued up for another potential duplicates search, so you will likely see some of them again in the duplicate filter.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'clear_false_positive_relations', hashes )
        
    
def DissolveAlternateGroup( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to dissolve this file\'s entire alternates group?'
        message += os.linesep * 2
        message += 'This will completely remove all duplicate, alternate, and false-positive relations for all files in the group and set them to come up again in the duplicate filter.'
        message += os.linesep * 2
        message += 'This is a potentially big change that throws away many previous decisions and cannot be undone. If you can achieve your result just by removing some alternate members, do that instead.'
        
    else:
        
        message = 'Are you sure you want to dissolve these {} files\' entire alternates groups?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'This will completely remove all duplicate, alternate, and false-positive relations for all alternate groups of all files selected and set them to come up again in the duplicate filter.'
        message += os.linesep * 2
        message += 'This is a potentially huge change that throws away many previous decisions and cannot be undone. If you can achieve your result just by removing some alternate members, do that instead.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'dissolve_alternates_group', hashes )
        
    
def DissolveDuplicateGroup( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to dissolve this file\'s duplicate group?'
        message += os.linesep * 2
        message += 'This will split the duplicates group back into individual files and remove any alternate relations they have. They will be queued back up in the duplicate filter for reprocessing.'
        message += os.linesep * 2
        message += 'This could be a big change that throws away many previous decisions and cannot be undone. If you can achieve your result just by removing one or two members, do that instead.'
        
    else:
        
        message = 'Are you sure you want to dissolve these {} files\' duplicate groups?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'This will split all the files\' duplicates groups back into individual files and remove any alternate relations they have. They will all be queued back up in the duplicate filter for reprocessing.'
        message += os.linesep * 2
        message += 'This could be a huge change that throws away many previous decisions and cannot be undone. If you can achieve your result just by removing some members, do that instead.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'dissolve_duplicates_group', hashes )
        
    
def RemoveFromAlternateGroup( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to remove this file from its alternates group?'
        message += os.linesep * 2
        message += 'Alternate relationships are stored between duplicate groups, so this will pull any duplicates of your file with it.'
        message += os.linesep * 2
        message += 'The removed file (and any duplicates) will be queued up for another potential duplicates search, so you will likely see at least one again in the duplicate filter.'
        
    else:
        
        message = 'Are you sure you want to remove these {} files from their alternates groups?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'Alternate relationships are stored between duplicate groups, so this will pull any duplicates of these files with them.'
        message += os.linesep * 2
        message += 'The removed files (and any duplicates) will be queued up for another potential duplicates search, so you will likely see some again in the duplicate filter.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'remove_alternates_member', hashes )
        
    
def RemoveFromDuplicateGroup( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to remove this file from its duplicate group?'
        message += os.linesep * 2
        message += 'The remaining group will be otherwise unaffected and will keep its alternate relationships.'
        message += os.linesep * 2
        message += 'The removed file will be queued up for another potential duplicates search, so you will likely see it again in the duplicate filter.'
        
    else:
        
        message = 'Are you sure you want to remove these {} files from their duplicate groups?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'The remaining groups will be otherwise unaffected and keep their alternate relationships.'
        message += os.linesep * 2
        message += 'The removed files will be queued up for another potential duplicates search, so you will likely see them again in the duplicate filter.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'remove_duplicates_member', hashes )
        
    
def RemovePotentials( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to remove all of this file\'s potentials?'
        message += os.linesep * 2
        message += 'This will mean it (or any of its duplicates) will not appear in the duplicate filter unless new potentials are found with new files. Use this command if the file has accidentally received many false positive potential relationships.'
        
    else:
        
        message = 'Are you sure you want to remove all of these {} files\' potentials?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'This will mean they (or any of their duplicates) will not appear in the duplicate filter unless new potentials are found with new files. Use this command if the files have accidentally received many false positive potential relationships.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'remove_potential_pairs', hashes )
        
    
def ResetPotentialSearch( win, hashes ):
    
    if len( hashes ) == 1:
        
        message = 'Are you sure you want to search this file for potential duplicates again?'
        message += os.linesep * 2
        message += 'This will not remove any existing potential pairs, and will typically not find any new relationships unless an error has occured.'
        
    else:
        
        message = 'Are you sure you want to search these {} files for potential duplicates again?'.format( HydrusData.ToHumanInt( len( hashes ) ) )
        message += os.linesep * 2
        message += 'This will not remove any existing potential pairs, and will typically not find any new relationships unless an error has occured.'
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        CG.client_controller.Write( 'reset_potential_search_status', hashes )
        
    
