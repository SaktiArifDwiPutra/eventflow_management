from odoo import _, api, models
from odoo.exceptions import UserError


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.model_create_multi
    def create(self, vals_list):
        event_ids = {vals['event_id'] for vals in vals_list if vals.get('event_id')}
        events = self.env['event.event'].browse(event_ids)
        not_approved = events.filtered(lambda e: e.approval_state != 'approved')
        if not_approved:
            raise UserError(_(
                "Registration is only possible for approved events. Not approved: %s",
                ", ".join(not_approved.mapped('name')),
            ))
        return super().create(vals_list)