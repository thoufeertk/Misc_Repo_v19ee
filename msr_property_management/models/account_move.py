from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    property_tenancy_id = fields.Many2one('property.tenancy', string='Tenancy', readonly=True,
                                           copy=False, index=True)
    property_building_id = fields.Many2one('property.building', string='Building', readonly=True,
                                            copy=False, index=True)
