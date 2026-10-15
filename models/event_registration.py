from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    checked_in_by = fields.Many2one(
        'res.users', string='Checked In By', readonly=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)
        not_approved = registrations.event_id.filtered(
            lambda e: e.approval_state != 'approved'
        )
        if not_approved:
            raise UserError(_(
                "Registration is only possible for approved events. Not approved: %s",
                ", ".join(not_approved.mapped('name')),
            ))
        return registrations

    def write(self, vals):
        newly_done = self.browse()
        if vals.get('state') == 'done':
            newly_done = self.filtered(lambda r: r.state != 'done')
        res = super().write(vals)
        if newly_done:
            newly_done.write({'checked_in_by': self.env.user.id})
        return res

    def action_set_done(self):
        if not self.env.user.has_group('eventflow_management.group_eventflow_staff'):
            raise AccessError(_("Only Event Staff can check in participants."))
        return super().action_set_done()