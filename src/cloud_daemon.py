from fastapi import FastAPI, Body
from src.ServiceAPI.serviceAPI import *

app = FastAPI()

@app.on_event("startup")
def do_something():
    pass

@app.post("/servers/",tags=["Register-Setting"])
async def p_set_register_edge_addr(name:str = Body(...),
                               address:str = Body(...)):
    try:
        return set_register_edge_addr(name, address)
    except Exception as e:
        print("error",e)
        return False

@app.post("/servers/events/")
async def p_post_event(edgeID:int = Body(...),
                        rtspsrc:str = Body(...)):
    try:
        return post_event(edgeID, rtspsrc)
    except Exception as e:
        print("error",e)
        return False