from odoo import fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    approval_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(copy=False)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)

    def action_submit(self):
        self.write({'approval_state': 'submitted'})

    def action_approve(self):
        self.write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'approval_state': 'rejected'})

    def action_reset_draft(self):
        self.write({
            'approval_state': 'draft',
            'approved_by': False,
            'approved_date': False,
        })