from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

APPROVAL_FIELDS = {'approval_state', 'approved_by', 'approved_date'}


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

    def write(self, vals):
        if APPROVAL_FIELDS & set(vals) and not self.env.context.get('eventflow_action'):
            raise UserError(_("Approval fields can only be changed using the workflow buttons."))
        return super().write(vals)

    def _check_eventflow_group(self, group_xmlid):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_("You do not have the rights to perform this action."))

    def action_submit(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_staff')
        self.with_context(eventflow_action=True).write({'approval_state': 'submitted'})

    def action_approve(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.with_context(eventflow_action=True).write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        if any(not event.rejection_reason for event in self):
            raise UserError(_("Please fill in the rejection reason before rejecting."))
        self.with_context(eventflow_action=True).write({'approval_state': 'rejected'})

    def action_reset_draft(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.with_context(eventflow_action=True).write({
            'approval_state': 'draft',
            'approved_by': False,
            'approved_date': False,
            'rejection_reason': False,
        })