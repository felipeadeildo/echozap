from fastapi import APIRouter, Depends, Request

from alexa.dispatcher import dispatch
from alexa.middleware import verify_alexa_signature

router = APIRouter(prefix="/alexa")


@router.post("/skill", dependencies=[Depends(verify_alexa_signature)])
async def skill_endpoint(request: Request) -> dict:
    body = await request.json()
    return await dispatch(body)
