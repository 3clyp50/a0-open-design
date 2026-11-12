import asyncio
import json

from helpers.tool import Tool, Response
from usr.plugins.open_design.helpers.studio import dispatch


class OpenDesign(Tool):
    async def execute(self, action="status", **kwargs):
        try:
            result = await asyncio.to_thread(dispatch, action=action, **kwargs)
            return Response(message=json.dumps(result, ensure_ascii=False), break_loop=False)
        except (ValueError, OSError, RuntimeError) as error:
            return Response(message=f"OpenDesign: {error}", break_loop=False)
