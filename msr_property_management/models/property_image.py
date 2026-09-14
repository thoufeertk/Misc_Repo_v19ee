from odoo import fields, models


class PropertyRoomImage(models.Model):
    _name = 'property.room.image'
    _description = 'Property Room Image'
    _order = 'sequence, id'

    name = fields.Char(string='Caption')
    sequence = fields.Integer(default=10)
    room_id = fields.Many2one('property.room', required=True, ondelete='cascade')
    image_1920 = fields.Image(string='Image', required=True)
    image_256 = fields.Image(string='Thumbnail', related='image_1920', max_width=256, max_height=256, store=True)


class PropertyBuildingImage(models.Model):
    _name = 'property.building.image'
    _description = 'Property Building Image'
    _order = 'sequence, id'

    name = fields.Char(string='Caption')
    sequence = fields.Integer(default=10)
    building_id = fields.Many2one('property.building', required=True, ondelete='cascade')
    image_1920 = fields.Image(string='Image', required=True)
    image_256 = fields.Image(string='Thumbnail', related='image_1920', max_width=256, max_height=256, store=True)
