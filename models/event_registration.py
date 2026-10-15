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

    def _is_paid_for_checkin(self):
        """Free or order-less registrations are fine; paid orders need paid invoices."""
        self.ensure_one()
        order = self.sale_order_id.sudo()
        if not order or order.currency_id.is_zero(order.amount_total):
            return True
        invoices = order.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        )
        return bool(invoices) and all(
            m.payment_state in ('paid', 'in_payment') for m in invoices
        )

    def write(self, vals):
        newly_done = self.browse()
        if vals.get('state') == 'done':
            newly_done = self.filtered(lambda r: r.state != 'done')
            unpaid = newly_done.filtered(lambda r: not r._is_paid_for_checkin())
            if unpaid:
                raise UserError(_(
                    "Check-in is only possible after the invoice is paid. "
                    "Unpaid: %s",
                    ", ".join(unpaid.mapped('name')),
                ))
        res = super().write(vals)
        if newly_done:
            newly_done.write({'checked_in_by': self.env.user.id})
        return res

    def action_set_done(self):
        if not self.env.user.has_group('eventflow_management.group_eventflow_staff'):
            raise AccessError(_("Only Event Staff can check in participants."))
        return super().action_set_done()