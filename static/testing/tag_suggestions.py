#!/bin/python

import argparse
import json

TAGS = [
    "solo",
    "red_hair",
    "white_skin",
    "business_suit",
    "skirt",
    "blouse",
]

def main() -> None:
    
    parser = argparse.ArgumentParser()
    parser.add_argument( "file_id", type = int )
    
    args = parser.parse_args()
    
    print( json.dumps( { "tags" : TAGS + [ str( args.file_id ) ] } ) )
    

if __name__ == "__main__":
    
    main()
    
