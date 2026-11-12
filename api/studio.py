import asyncio

from helpers.api import ApiHandler, Request, Response
from usr.plugins.open_design.helpers.studio import dispatch


class Studio(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            return {"ok": True, **await asyncio.to_thread(dispatch, **input)}
        except (ValueError, FileNotFoundError) as error:
            return Response(str(error), status=400)
        except RuntimeError as error:
            return Response(str(error), status=503)
