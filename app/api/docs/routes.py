from flask import current_app, jsonify, render_template_string, request, url_for

from . import blueprint
from .spec import build_spec

SWAGGER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body { margin: 0; background: #fafafa; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      SwaggerUIBundle({
        url: "{{ spec_url }}",
        dom_id: '#swagger-ui',
        deepLinking: true
      });
    };
  </script>
</body>
</html>
"""


def _external_url(endpoint: str) -> str:
    """Return absolute URL respecting X-Forwarded-Proto (https on Railway)."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    return url_for(endpoint, _external=True, _scheme=scheme)


@blueprint.route("/openapi.json")
def openapi_json():
    """Serve the OpenAPI specification."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    server_url = f"{scheme}://{request.host.rstrip('/')}"
    spec = build_spec(current_app.config, server_url)
    return jsonify(spec)


@blueprint.route("/swagger")
def swagger_ui():
    """Render a minimal Swagger UI powered by CDN assets."""
    spec_url = _external_url("docs.openapi_json")
    title = current_app.config.get("API_TITLE", "Casemind Claims API - Docs")
    return render_template_string(SWAGGER_TEMPLATE, spec_url=spec_url, title=title)


@blueprint.route("/")
def docs_index():
    """Redirect root docs route to Swagger UI."""
    spec_url = url_for("docs.swagger_ui")
    return ("", 302, {"Location": spec_url})
