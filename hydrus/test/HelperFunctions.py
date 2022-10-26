import unittest

def compare_content_updates( ut: unittest.TestCase, service_keys_to_content_updates, expected_service_keys_to_content_updates ):
    
    ut.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
        
        c_u_tuples = sorted( ( ( c_u.ToTuple(), c_u.GetReason() ) for c_u in content_updates ) )
        e_c_u_tuples = sorted( ( ( e_c_u.ToTuple(), e_c_u.GetReason() ) for e_c_u in expected_content_updates ) )
        
        ut.assertEqual( c_u_tuples, e_c_u_tuples )
        
    
