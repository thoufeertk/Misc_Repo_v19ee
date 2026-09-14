from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PropertyBuilding(models.Model):
    _name = 'property.building'
    _description = 'Property Building'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(string='Reference')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                           copy=False,
                                           help='Automatically created under the "Buildings" analytic plan. '
                                                'You may pick a different analytic account instead.')
    building_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed Use'),
    ], default='residential', tracking=True)
    manager_id = fields.Many2one('res.users', string='Property Manager',
                                  default=lambda self: self.env.user, tracking=True)
    owner_id = fields.Many2one('res.partner', string='Owner')

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one('res.country', default=lambda self: self.env.company.country_id)
    zip = fields.Char(string='ZIP')

    latitude = fields.Float(string='Latitude', digits=(16, 5), copy=False)
    longitude = fields.Float(string='Longitude', digits=(16, 5), copy=False)

    total_floors = fields.Integer(default=1, string='Total Floors')
    image_1920 = fields.Image(string='Image')
    building_image_ids = fields.One2many('property.building.image', 'building_id', string='Gallery')
    amenity_ids = fields.Many2many('property.amenity', 'property_building_amenity_rel', 'building_id', 'amenity_id',
                                    string='Amenities')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    active = fields.Boolean(default=True)

    room_ids = fields.One2many('property.room', 'building_id', string='Rooms')
    document_ids = fields.One2many('property.document', 'building_id', string='Documents')

    room_count = fields.Integer(compute='_compute_room_stats', string='Room Count')
    occupied_room_count = fields.Integer(compute='_compute_room_stats', string='Occupied')
    vacant_room_count = fields.Integer(compute='_compute_room_stats', string='Vacant')
    maintenance_room_count = fields.Integer(compute='_compute_room_stats', string='Under Maintenance')
    occupancy_rate = fields.Float(compute='_compute_room_stats', string='Occupancy %')

    monthly_expected_revenue = fields.Monetary(compute='_compute_revenue', currency_field='currency_id',
                                                string='Expected Monthly Revenue')
    total_invoiced_amount = fields.Monetary(compute='_compute_revenue', currency_field='currency_id',
                                             string='Total Invoiced (Posted)')

    document_expiring_count = fields.Integer(compute='_compute_document_stats', store=True,
                                              string='Expiring Documents')

    @api.model_create_multi
    def create(self, vals_list):
        buildings = super().create(vals_list)
        for building in buildings:
            building._ensure_analytic_account()
        return buildings

    def _ensure_analytic_account(self):
        self.ensure_one()
        if self.analytic_account_id:
            return
        plan = self.env.ref('msr_property_management.analytic_plan_buildings')
        self.analytic_account_id = self.env['account.analytic.account'].sudo().create({
            'name': self.name,
            'plan_id': plan.id,
            'company_id': self.company_id.id,
        }).id

    @api.depends('room_ids.status')
    def _compute_room_stats(self):
        for building in self:
            rooms = building.room_ids
            building.room_count = len(rooms)
            building.occupied_room_count = len(rooms.filtered(lambda r: r.status == 'occupied'))
            building.vacant_room_count = len(rooms.filtered(lambda r: r.status == 'vacant'))
            building.maintenance_room_count = len(rooms.filtered(lambda r: r.status == 'maintenance'))
            building.occupancy_rate = (
                building.occupied_room_count / building.room_count
            ) if building.room_count else 0.0

    @api.depends('room_ids.tenancy_ids.state', 'room_ids.tenancy_ids.rent_amount_monthly')
    def _compute_revenue(self):
        for building in self:
            active_tenancies = building.room_ids.tenancy_ids.filtered(lambda t: t.state == 'active')
            building.monthly_expected_revenue = sum(active_tenancies.mapped('rent_amount_monthly'))
            moves = self.env['account.move'].search([
                ('property_building_id', '=', building.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
            building.total_invoiced_amount = sum(moves.mapped('amount_total_signed'))

    @api.depends('document_ids.state')
    def _compute_document_stats(self):
        for building in self:
            building.document_expiring_count = len(
                building.document_ids.filtered(lambda d: d.state in ('expiring', 'expired'))
            )

    def action_view_rooms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rooms',
            'res_model': 'property.room',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id},
        }

    def action_locate_on_map(self):
        for building in self:
            address = self.env['base.geocoder'].geo_query_address(
                street=building.street, zip=building.zip, city=building.city,
                state=building.state_id.name, country=building.country_id.name,
            )
            result = self.env['base.geocoder'].geo_find(address)
            if not result:
                raise UserError(_('Could not locate an address for %s. Please check the address fields.',
                                   building.display_name))
            building.latitude, building.longitude = result
        return True

    def action_view_on_map(self):
        self.ensure_one()
        if self.latitude or self.longitude:
            query = f'{self.latitude},{self.longitude}'
        else:
            query = ', '.join(filter(None, [
                self.street, self.city, self.state_id.name, self.zip, self.country_id.name,
            ]))
            if not query:
                raise UserError(_('This building has no address or coordinates to show on a map.'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'https://www.google.com/maps?q={query}',
            'target': 'new',
        }

    @api.model
    def get_map_data(self):
        """Return building markers (name, address, coordinates) for the Property Map client action."""
        buildings = self.search([('latitude', '!=', 0), ('longitude', '!=', 0)])
        return [{
            'id': building.id,
            'name': building.name,
            'address': ', '.join(filter(None, [building.street, building.city, building.state_id.name])),
            'latitude': building.latitude,
            'longitude': building.longitude,
            'room_count': building.room_count,
            'occupancy_rate': building.occupancy_rate * 100.0,
        } for building in buildings]

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'property.document',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id},
        }

    @api.model
    def get_dashboard_data(self):
        """Return aggregated KPI data used by the Property Management dashboard client action."""
        buildings = self.search([])
        rooms = self.env['property.room'].search([])
        documents = self.env['property.document'].search([('state', 'in', ('expiring', 'expired'))])
        currency = self.env.company.currency_id

        building_data = []
        for building in buildings:
            building_data.append({
                'id': building.id,
                'name': building.name,
                'room_count': building.room_count,
                'occupied_room_count': building.occupied_room_count,
                'vacant_room_count': building.vacant_room_count,
                'maintenance_room_count': building.maintenance_room_count,
                'occupancy_rate': building.occupancy_rate * 100.0,
                'monthly_expected_revenue': building.monthly_expected_revenue,
                'total_invoiced_amount': building.total_invoiced_amount,
            })
        # Highest revenue first, for the chart / ranking table.
        building_data.sort(key=lambda b: b['total_invoiced_amount'], reverse=True)

        total_rooms = len(rooms)
        occupied_rooms = len(rooms.filtered(lambda r: r.status == 'occupied'))
        vacant_rooms = len(rooms.filtered(lambda r: r.status == 'vacant'))
        maintenance_rooms = len(rooms.filtered(lambda r: r.status == 'maintenance'))

        return {
            'total_buildings': len(buildings),
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'vacant_rooms': vacant_rooms,
            'maintenance_rooms': maintenance_rooms,
            'occupancy_rate': (occupied_rooms / total_rooms * 100.0) if total_rooms else 0.0,
            'total_monthly_expected_revenue': sum(b['monthly_expected_revenue'] for b in building_data),
            'total_invoiced_amount': sum(b['total_invoiced_amount'] for b in building_data),
            'expiring_documents_count': len(documents),
            'currency_symbol': currency.symbol,
            'currency_position': currency.position,
            'buildings': building_data,
        }
