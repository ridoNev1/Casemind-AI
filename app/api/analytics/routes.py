from flask import jsonify

from . import blueprint
from ...auth import jwt_required
from ...services.analytics import get_casemix_by_province


@blueprint.route("/casemix")
@jwt_required
def casemix():
    """Aggregate casemix metrics grouped by province."""
    data = get_casemix_by_province()
    return jsonify({"data": data})
