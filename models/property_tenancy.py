from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PERIOD_MONTHS = {
    'monthly': 1,
    'quarterly': 3,
    'yearly': 12,
}


class PropertyTenancy(models.Model):
    _name = 'property.tenancy'
    _description = 'Property Tenancy / Rent Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char(default=lambda self: _('New'), copy=False, readonly=True, tracking=True)
    tenant_id = fields.Many2one('res.partner', required=True, string='Tenant', tracking=True)
    building_id = fields.Many2one('property.building', required=True, string='Building', tracking=True)
    room_id = fields.Many2one('property.room', required=True, string='Room/Unit', tracking=True,
                               help='Suggests the room\'s standard rent when selected.')
    company_id = fields.Many2one(related='room_id.company_id', store=True)
    currency_id = fields.Many2one(related='room_id.currency_id')

    date_start = fields.Date(required=True, default=fields.Date.context_today, tracking=True, string='Start Date')
    date_end = fields.Date(required=True, string='Valid Until', tracking=True)

    rent_amount = fields.Monetary(required=True, string='Rent Amount')
    security_deposit = fields.Monetary(string='Security Deposit')
    invoice_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ], default='monthly', required=True, string='Invoice Frequency', tracking=True)
    custom_period_months = fields.Integer(string='Every N Months', default=1)
    period_months = fields.Integer(compute='_compute_period_months', store=True, string='Period (Months)')
    rent_amount_monthly = fields.Monetary(compute='_compute_rent_amount_monthly', store=True,
                                           string='Monthly Equivalent Rent')

    product_id = fields.Many2one(
        'product.product', string='Rent Product', required=True,
        default=lambda self: self._default_product_id())
    journal_id = fields.Many2one('account.journal', string='Sales Journal', domain=[('type', '=', 'sale')])

    next_invoice_date = fields.Date(string='Next Invoice Date', copy=False, tracking=True)
    last_invoice_date = fields.Date(string='Last Invoice Date', copy=False)
    invoice_ids = fields.One2many('account.move', 'property_tenancy_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ], default='draft', tracking=True, copy=False, string='Status')

    note = fields.Text(string='Terms / Notes')
    active = fields.Boolean(default=True)

    def _default_product_id(self):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        product_id = IrConfigParameter.get_param('msr_property_management.default_product_id')
        if product_id:
            return self.env['product.product'].browse(int(product_id)).exists()
        return self.env.ref('msr_property_management.product_product_rent', raise_if_not_found=False)

    @api.depends('invoice_frequency', 'custom_period_months')
    def _compute_period_months(self):
        for rec in self:
            if rec.invoice_frequency == 'custom':
                rec.period_months = rec.custom_period_months or 1
            else:
                rec.period_months = PERIOD_MONTHS.get(rec.invoice_frequency, 1)

    @api.depends('rent_amount', 'period_months')
    def _compute_rent_amount_monthly(self):
        for rec in self:
            rec.rent_amount_monthly = (rec.rent_amount / rec.period_months) if rec.period_months else rec.rent_amount

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.room_id and self.room_id.building_id != self.building_id:
            self.room_id = False

    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.building_id = self.room_id.building_id
            self.rent_amount = self.room_id.rent_amount
            self.security_deposit = self.room_id.security_deposit

    @api.constrains('building_id', 'room_id')
    def _check_building_room_consistency(self):
        for rec in self:
            if rec.room_id and rec.building_id and rec.room_id.building_id != rec.building_id:
                raise ValidationError(_('Room %(room)s does not belong to building %(building)s.',
                                        room=rec.room_id.display_name, building=rec.building_id.display_name))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(_('The tenancy end date must be after the start date.'))

    @api.constrains('invoice_frequency', 'custom_period_months')
    def _check_custom_period(self):
        for rec in self:
            if rec.invoice_frequency == 'custom' and rec.custom_period_months <= 0:
                raise ValidationError(_('The custom invoicing period must be at least 1 month.'))

    @api.constrains('rent_amount')
    def _check_rent_amount(self):
        for rec in self:
            if rec.rent_amount <= 0:
                raise ValidationError(_('The rent amount must be strictly positive.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('property.tenancy') or _('New')
            if vals.get('room_id'):
                room = self.env['property.room'].browse(vals['room_id'])
                if not vals.get('building_id'):
                    vals['building_id'] = room.building_id.id
                if not vals.get('rent_amount'):
                    vals['rent_amount'] = room.rent_amount
                if not vals.get('security_deposit'):
                    vals['security_deposit'] = room.security_deposit
        records = super().create(vals_list)
        for rec in records:
            if rec.tenant_id and not rec.tenant_id.is_tenant:
                rec.tenant_id.is_tenant = True
        return records

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            overlapping = self.search([
                ('id', '!=', rec.id),
                ('room_id', '=', rec.room_id.id),
                ('state', '=', 'active'),
                ('date_start', '<=', rec.date_end),
                ('date_end', '>=', rec.date_start),
            ])
            if overlapping:
                raise ValidationError(_(
                    'Room %(room)s is already occupied by an active tenancy (%(other)s) during this period.',
                    room=rec.room_id.display_name, other=overlapping[0].name,
                ))
            rec.write({
                'state': 'active',
                'next_invoice_date': rec.next_invoice_date or rec.date_start,
            })
        return True

    def action_terminate(self):
        self.write({'state': 'terminated'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'default_move_type': 'out_invoice'},
        }

    def action_generate_invoice_now(self):
        """Manual trigger to generate the next due invoice immediately (mainly for testing/manual use)."""
        for rec in self:
            if rec.state == 'active' and rec.next_invoice_date and rec.next_invoice_date <= rec.date_end:
                rec._generate_invoice()

    def _prepare_invoice_vals(self, invoice_date):
        self.ensure_one()
        period_end = invoice_date + relativedelta(months=self.period_months, days=-1)
        line_vals = {
            'product_id': self.product_id.id,
            'name': _('Rent - %(room)s (%(start)s to %(end)s)', room=self.room_id.display_name,
                      start=invoice_date, end=period_end),
            'quantity': 1,
            'price_unit': self.rent_amount,
        }
        if self.room_id.analytic_account_id:
            line_vals['analytic_distribution'] = {str(self.room_id.analytic_account_id.id): 100}
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'invoice_date': invoice_date,
            'invoice_origin': self.name,
            'property_tenancy_id': self.id,
            'property_building_id': self.building_id.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        journal_id = self.journal_id.id or IrConfigParameter.get_param('msr_property_management.default_journal_id')
        if journal_id:
            vals['journal_id'] = int(journal_id)
        return vals

    def _generate_invoice(self):
        self.ensure_one()
        move = self.env['account.move'].create(self._prepare_invoice_vals(self.next_invoice_date))
        self.last_invoice_date = self.next_invoice_date
        self.next_invoice_date = self.next_invoice_date + relativedelta(months=self.period_months)
        auto_post = self.env['ir.config_parameter'].sudo().get_param('msr_property_management.auto_post_invoices')
        if auto_post:
            move.action_post()
        return move

    @api.model
    def _cron_generate_rent_invoices(self):
        today = fields.Date.context_today(self)
        tenancies = self.search([
            ('state', '=', 'active'),
            ('next_invoice_date', '!=', False),
            ('next_invoice_date', '<=', today),
        ])
        for tenancy in tenancies:
            # Catch up on any missed periods if the cron did not run for a while,
            # generating one draft invoice per due period, without going past date_end.
            while (tenancy.next_invoice_date and tenancy.next_invoice_date <= today
                   and tenancy.next_invoice_date <= tenancy.date_end):
                tenancy._generate_invoice()

    @api.model
    def _cron_update_tenancy_state(self):
        today = fields.Date.context_today(self)
        expired = self.search([('state', '=', 'active'), ('date_end', '<', today)])
        expired.write({'state': 'expired'})

    @api.model
    def _cron_remind_tenancy_expiry(self):
        reminder_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'msr_property_management.tenancy_reminder_days', default=15))
        today = fields.Date.context_today(self)
        deadline = today + relativedelta(days=reminder_days)
        tenancies = self.search([
            ('state', '=', 'active'),
            ('date_end', '>=', today),
            ('date_end', '<=', deadline),
        ])
        for tenancy in tenancies:
            manager = tenancy.room_id.building_id.manager_id
            if not manager:
                continue
            already_notified = self.env['mail.activity'].search_count([
                ('res_model', '=', 'property.tenancy'),
                ('res_id', '=', tenancy.id),
                ('summary', '=', _('Tenancy Expiry: %s', tenancy.name)),
            ])
            if already_notified:
                continue
            tenancy.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Tenancy Expiry: %s', tenancy.name),
                note=_(
                    'The tenancy %(name)s for %(tenant)s in %(room)s ends on %(date)s.',
                    name=tenancy.name, tenant=tenancy.tenant_id.display_name,
                    room=tenancy.room_id.display_name, date=tenancy.date_end,
                ),
                user_id=manager.id,
            )
