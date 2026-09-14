from odoo import api, fields, models


class PropertyRoom(models.Model):
    _name = 'property.room'
    _description = 'Property Room / Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'building_id, name'

    name = fields.Char(required=True, string='Room/Unit No.')
    building_id = fields.Many2one('property.building', required=True, ondelete='cascade', string='Building')
    company_id = fields.Many2one(related='building_id.company_id', store=True)
    currency_id = fields.Many2one(related='building_id.currency_id')

    floor = fields.Char()
    room_type = fields.Selection([
        ('studio', 'Studio'),
        ('1bhk', '1 BHK'),
        ('2bhk', '2 BHK'),
        ('3bhk', '3 BHK'),
        ('office', 'Office'),
        ('shop', 'Shop'),
        ('other', 'Other'),
    ], default='1bhk', required=True, string='Type')
    area = fields.Float(string='Area (sqft)')
    rent_amount = fields.Monetary(string='Standard Rent', required=True)
    security_deposit = fields.Monetary(string='Standard Security Deposit')

    furnishing_status = fields.Selection([
        ('unfurnished', 'Unfurnished'),
        ('semi_furnished', 'Semi-Furnished'),
        ('fully_furnished', 'Fully Furnished'),
    ], default='unfurnished', required=True, string='Furnishing')
    bathroom_count = fields.Integer(string='Bathrooms', default=1)
    balcony_count = fields.Integer(string='Balconies', default=0)
    amenity_ids = fields.Many2many('property.amenity', 'property_room_amenity_rel', 'room_id', 'amenity_id',
                                    string='Amenities')

    image_1920 = fields.Image(string='Cover Image')
    image_128 = fields.Image(string='Cover Thumbnail', related='image_1920', max_width=128, max_height=128, store=True)
    room_image_ids = fields.One2many('property.room.image', 'room_id', string='Gallery')

    under_maintenance = fields.Boolean(string='Under Maintenance')
    status = fields.Selection([
        ('vacant', 'Vacant'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
    ], compute='_compute_status', store=True, string='Status')

    tenancy_ids = fields.One2many('property.tenancy', 'room_id', string='Tenancies')
    active_tenancy_id = fields.Many2one('property.tenancy', compute='_compute_active_tenancy',
                                         store=True, string='Current Tenancy')
    tenant_id = fields.Many2one(related='active_tenancy_id.tenant_id', string='Current Tenant')
    active = fields.Boolean(default=True)

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                           copy=False,
                                           help='Automatically created under the "Rooms" analytic plan. '
                                                'Rent invoice lines for this room are attributed to it. '
                                                'You may pick a different analytic account instead.')

    _room_name_building_uniq = models.Constraint(
        'unique(building_id, name)',
        'Room number must be unique per building.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        rooms = super().create(vals_list)
        for room in rooms:
            room._ensure_analytic_account()
        return rooms

    def _ensure_analytic_account(self):
        self.ensure_one()
        if self.analytic_account_id:
            return
        plan = self.env.ref('msr_property_management.analytic_plan_rooms')
        self.analytic_account_id = self.env['account.analytic.account'].sudo().create({
            'name': self.name,
            'plan_id': plan.id,
            'company_id': self.company_id.id,
        }).id

    @api.depends('under_maintenance', 'tenancy_ids.state')
    def _compute_status(self):
        for room in self:
            if room.under_maintenance:
                room.status = 'maintenance'
            elif room.tenancy_ids.filtered(lambda t: t.state == 'active'):
                room.status = 'occupied'
            else:
                room.status = 'vacant'

    @api.depends('tenancy_ids.state')
    def _compute_active_tenancy(self):
        for room in self:
            room.active_tenancy_id = room.tenancy_ids.filtered(lambda t: t.state == 'active')[:1]

    def action_view_tenancies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tenancies',
            'res_model': 'property.tenancy',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id, 'default_building_id': self.building_id.id},
        }
