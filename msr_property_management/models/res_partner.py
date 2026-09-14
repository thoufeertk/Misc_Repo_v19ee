from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_tenant = fields.Boolean(string='Is Tenant', copy=False)
    tenancy_ids = fields.One2many('property.tenancy', 'tenant_id', string='Tenancies')
    tenancy_count = fields.Integer(compute='_compute_tenancy_count', string='Tenancy Count')

    @api.depends('tenancy_ids')
    def _compute_tenancy_count(self):
        for partner in self:
            partner.tenancy_count = len(partner.tenancy_ids)

    def action_view_tenancies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenancies'),
            'res_model': 'property.tenancy',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
