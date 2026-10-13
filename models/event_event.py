from odoo import _, fields, models
from odoo.exceptions import AccessError


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

    def _check_eventflow_group(self, group_xmlid):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_("You do not have the rights to perform this action."))

    def action_submit(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_staff')
        self.write({'approval_state': 'submitted'})

    def action_approve(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.write({'approval_state': 'rejected'})

    def action_reset_draft(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.write({
            'approval_state': 'draft',
            'approved_by': False,
            'approved_date': False,
        })