import requests

def set_edge_id(edgeID:int, address:str):
    if address.endswith("/"):
        URL = address + "edges/"
    else:
        URL = address + "/edges/"

    response = requests.post(url=URL, json=edgeID)

    try:
        if response.text.lower() == "true":
            return True
    except Exception as e:
        print("error : ",e)

    return False

