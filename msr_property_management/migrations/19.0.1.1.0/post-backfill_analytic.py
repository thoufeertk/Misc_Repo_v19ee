from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    buildings = env['property.building'].search([('analytic_plan_id', '=', False)])
    for building in buildings:
        building.analytic_plan_id = env['account.analytic.plan'].create({
            'name': building.name,
        }).id
    rooms = env['property.room'].search([('analytic_account_id', '=', False)])
    for room in rooms:
        room._ensure_analytic_account()
