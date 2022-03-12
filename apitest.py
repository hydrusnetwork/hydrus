import requests
import cbor2
import base64
import json
import urllib.parse

hydrus_api_url = "http://localhost:45888"
metadata =  hydrus_api_url+"/get_files/file_metadata"
del_note = hydrus_api_url+"/add_notes/delete_notes"
set_note = hydrus_api_url+"/add_notes/set_notes"
search = hydrus_api_url+"/get_files/search_files"

hsh="1b625544bcfbd7151000a816e6db6388ba0ef4dc3a664b62e2cb4e9d3036bed8"
key="222f3c82f4f7e8ce57747ff1cccfaf7014357dc509cdb77af20ff910c26ea05b"

# search for notes
print(json.loads((requests.get(url = search, params = {
    "Hydrus-Client-API-Access-Key": key,
    "tags": urllib.parse.quote("[\"system:has notes\"]")
}).text)))

# retrieve notes
print(json.loads((requests.get(url = metadata, params = {
    "Hydrus-Client-API-Access-Key": key,
    "include_notes": "true",
    "hashes": urllib.parse.quote("[\""+hsh+"\"]")
}).text))["metadata"][0]["notes"])

# retrieve notes, request that the response is CBOR encoded
print(cbor2.loads((requests.get(url = metadata, params = {
    "Hydrus-Client-API-Access-Key": key,
    "include_notes": base64.urlsafe_b64encode(cbor2.dumps(True)),
    "hashes": base64.urlsafe_b64encode(cbor2.dumps([hsh])),
    "cbor": ""
}).content))["metadata"][0]["notes"])

# Add notes

headers = {"Hydrus-Client-API-Access-Key": key, "Content-Type": "application/json"}
print(requests.post(url = set_note, headers = headers, data = json.dumps({
    "notes": {"note1":"content1", "note2":"content2"},
    "hash": hsh
})))

# Delete notes

headers = {"Hydrus-Client-API-Access-Key": key, "Content-Type": "application/json"}
print(requests.post(url = del_note, headers = headers, data = json.dumps({
    "note_names": ["note1","note2","asgasgasgasgaa"],
    "hash": hsh
})))

# Add notes, but send CBOR instead of json

headers = {"Hydrus-Client-API-Access-Key": key, "Content-Type": "application/cbor"}
print(requests.post(url = set_note, headers = headers, data = cbor2.dumps({
    "notes": {"note1":"content1", "note2":"content2"},
    "hash": hsh
})))