from flask import send_file

from helpers.api import ApiHandler, Request, Response
from usr.plugins.open_design.helpers.studio import PROJECTS, get_project, inside


class Artifact(ApiHandler):
    @classmethod
    def get_methods(cls):
        return ["GET"]

    @classmethod
    def requires_csrf(cls):
        return False

    async def process(self, input: dict, request: Request):
        try:
            project = get_project(request.args.get("id", ""))
            path = inside(inside(PROJECTS, project["id"]), project["artifact"])
            response = send_file(path, mimetype="text/html", as_attachment=request.args.get("download") == "1", download_name="design.html")
            response.headers["Content-Security-Policy"] = (
                "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; img-src data: blob: https:; font-src data:; "
                "connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"
            return response
        except (ValueError, OSError, KeyError):
            return Response("Design not found.", status=404)
