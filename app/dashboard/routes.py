from flask import Blueprint

from app.auth.decorators import roles_required
from app.dashboard.service import stats
from app.utils.response import success_response

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/stats")
@roles_required("admin")
def dashboard_stats():
    """
    ---
    tags: [Dashboard]
    summary: Statistics
    description: Admin-only dashboard metrics.
    security: [{Bearer: []}]
    responses:
      200: {description: Dashboard statistics}
    """
    return success_response("Dashboard stats fetched successfully.", stats())
