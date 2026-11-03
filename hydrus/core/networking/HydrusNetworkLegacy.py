from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetwork

def ConvertToNewAccountType( account_type_key, title, dictionary_string, deserialisation_context: HydrusSerialisable.DeserialisationContext ) -> HydrusNetwork.AccountType:
    
    dict_deserialisation_context = deserialisation_context.DuplicateForNewWhitelist(
        {
            HydrusSerialisable.SERIALISABLE_TYPE_DICTIONARY,
            HydrusSerialisable.SERIALISABLE_TYPE_LIST,
            HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_RULES
        }
    )
    
    dictionary = HydrusSerialisable.CreateFromString( dictionary_string, dict_deserialisation_context )
    
    permissions = dict( dictionary[ 'permissions' ] )
    bandwidth_rules = dictionary[ 'bandwidth_rules' ]
    
    return HydrusNetwork.AccountType( account_type_key = account_type_key, title = title, permissions = permissions, bandwidth_rules = bandwidth_rules )
    
