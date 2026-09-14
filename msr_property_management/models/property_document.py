from datetime import timedelta

from odoo import _, api, fields, models


class PropertyDocument(models.Model):
    _name = 'property.document'
    _description = 'Property Building Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(required=True, tracking=True)
    building_id = fields.Many2one('property.building', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='building_id.company_id', store=True)

    document_type = fields.Selection([
        ('tax', 'Property Tax'),
        ('insurance', 'Insurance'),
        ('license', 'License / Permit'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ], default='other', required=True, tracking=True, string='Type')

    attachment = fields.Binary(string='File', attachment=True)
    attachment_filename = fields.Char(string='File Name')

    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(required=True, tracking=True, string='Expiry Date')
    reminder_days = fields.Integer(default=lambda self: self._default_reminder_days(),
                                    string='Remind Before (days)')
    responsible_id = fields.Many2one('res.users', string='Responsible',
                                      default=lambda self: self.env.user)

    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], compute='_compute_state', store=True, string='Status')
    notification_sent = fields.Boolean(default=False, copy=False)

    note = fields.Text()
    active = fields.Boolean(default=True)

    def _default_reminder_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'msr_property_management.document_reminder_days', default=30))

    @api.depends('expiry_date', 'reminder_days')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.state = 'valid'
            elif rec.expiry_date < today:
                rec.state = 'expired'
            elif rec.expiry_date <= today + timedelta(days=rec.reminder_days or 0):
                rec.state = 'expiring'
            else:
                rec.state = 'valid'

    def write(self, vals):
        if 'expiry_date' in vals and 'notification_sent' not in vals:
            vals['notification_sent'] = False
        return super().write(vals)

    @api.model
    def _cron_check_document_expiry(self):
        docs = self.search([('state', 'in', ('expiring', 'expired')), ('notification_sent', '=', False)])
        for doc in docs:
            status_label = _('expired') if doc.state == 'expired' else _('expiring soon')
            type_label = dict(doc._fields['document_type'].selection).get(doc.document_type, doc.document_type)
            note = _(
                'The document "%(name)s" (%(type)s) for building %(building)s is %(status)s (expiry date: %(date)s).',
                name=doc.name, type=type_label, building=doc.building_id.display_name,
                status=status_label, date=doc.expiry_date,
            )
            if doc.responsible_id:
                doc.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Document Expiry: %s', doc.name),
                    note=note,
                    user_id=doc.responsible_id.id,
                )
            doc.message_post(body=note)
            doc.notification_sent = True
