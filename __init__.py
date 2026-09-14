from . import models


def post_init_hook(env):
    """Backfill analytic accounts for buildings and rooms that existed before this feature."""
    buildings = env['property.building'].search([('analytic_account_id', '=', False)])
    for building in buildings:
        building._ensure_analytic_account()
    rooms = env['property.room'].search([('analytic_account_id', '=', False)])
    for room in rooms:
        room._ensure_analytic_account()
