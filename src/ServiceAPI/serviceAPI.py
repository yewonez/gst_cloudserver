import os
from src.RequestAPI.requestAPI import *

def set_register_edge_addr(name:str, address:str):
    print("name :", name)
    print("address : ", address)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  #src directory
    edge_info = os.path.join(root_dir, "edge_info")

    edgeID = -1

    try:
        with open(edge_info, 'r') as file_data:
            for file_buffer in file_data.readlines():
                if file_buffer is None:
                    break
                registed_edge_id = file_buffer.split(',')
                if edgeID < int(registed_edge_id[0]):
                    edgeID = int(registed_edge_id[0])
    except FileNotFoundError as e:
        with open(edge_info, 'w'):
            pass
    edgeID += 1

    with open(edge_info, 'a') as file_data:
        edge_info = str(edgeID) + "," + name + "," + address + "\n"
        file_data.write(edge_info)

    ret = set_edge_id(edgeID, address)

    if ret is False:
        return False

    return True

def post_event(edgeID:int, rtspsrc:str):
    print("edgeID:",edgeID)
    print("rtspsrc:",rtspsrc)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    event = os.path.join(root_dir, "event")

    try:
        with open(event, 'a') as file_data:
            event_info = str(edgeID) + "," + rtspsrc + "\n"
            file_data.write(event_info)
    except FileNotFoundError as e:
        with open(event, 'w') as file_data:
            event_info = str(edgeID) + "," + rtspsrc + "\n"
            file_data.write(event_info)
    except Exception as e:
        print("error", e)
        return False

    return True

def get_rtsp(edgeID:int):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src directory
    event_info = os.path.join(root_dir, "event")
    try:
        with open(event_info, 'r') as file_data:
            for file_buffer in file_data.readlines():
                if file_buffer is None:
                    break
                event_list = file_buffer.split(',')
                if edgeID == int(event_list[0]):
                    return event_list[1]
    except FileNotFoundError as e:
        print("error:",e)
    return ""