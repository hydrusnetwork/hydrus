from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetwork

def ConvertToNewAccountType( account_type_key, title, dictionary_string ) -> HydrusNetwork.AccountType:
    
    dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
    
    permissions = dict( dictionary[ 'permissions' ] )
    bandwidth_rules = dictionary[ 'bandwidth_rules' ]
    
    return HydrusNetwork.AccountType( account_type_key = account_type_key, title = title, permissions = permissions, bandwidth_rules = bandwidth_rules )
    
