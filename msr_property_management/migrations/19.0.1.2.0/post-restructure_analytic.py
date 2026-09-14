from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Move from one analytic plan per building to two shared plans (Buildings/Rooms).

    Room analytic accounts are renamed and re-pointed in place (not recreated) so that
    any invoice line already referencing them via analytic_distribution keeps working.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    buildings_plan = env.ref('msr_property_management.analytic_plan_buildings')
    rooms_plan = env.ref('msr_property_management.analytic_plan_rooms')

    cr.execute("""
        SELECT id, analytic_plan_id FROM property_building
        WHERE analytic_plan_id IS NOT NULL
    """)
    old_plan_by_building = dict(cr.fetchall())

    buildings = env['property.building'].search([('analytic_account_id', '=', False)])
    for building in buildings:
        building.analytic_account_id = env['account.analytic.account'].create({
            'name': building.name,
            'plan_id': buildings_plan.id,
            'company_id': building.company_id.id,
        }).id

    rooms_with_account = env['property.room'].search([('analytic_account_id', '!=', False)])
    for room in rooms_with_account:
        room.analytic_account_id.write({'name': room.name, 'plan_id': rooms_plan.id})

    rooms_missing_account = env['property.room'].search([('analytic_account_id', '=', False)])
    for room in rooms_missing_account:
        room._ensure_analytic_account()

    old_plan_ids = [pid for pid in old_plan_by_building.values() if pid]
    if old_plan_ids:
        old_plans = env['account.analytic.plan'].browse(old_plan_ids).exists()
        old_plans.filtered(lambda p: not p.account_ids).unlink()
