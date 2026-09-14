from odoo import fields, models


class PropertyAmenity(models.Model):
    _name = 'property.amenity'
    _description = 'Property Amenity'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection([
        ('furnishing', 'Furnishing'),
        ('utility', 'Utility'),
        ('safety', 'Safety'),
        ('recreation', 'Recreation'),
        ('other', 'Other'),
    ], default='other', required=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')

    _amenity_name_uniq = models.Constraint(
        'unique(name)',
        'An amenity with this name already exists.',
    )
