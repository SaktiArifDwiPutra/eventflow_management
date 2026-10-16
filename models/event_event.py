from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

APPROVAL_FIELDS = {'approval_state', 'approved_by', 'approved_date'}
LOCKED_FIELDS = {'name', 'date_begin', 'date_end', 'seats_max', 'seats_limited'}


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
    attendance_rate = fields.Float(
        string='Attendance Rate',
        compute='_compute_attendance_rate',
        store=True,
        aggregator='avg',
    )
    attendance_percent = fields.Float(
        string='Attendance (%)',
        compute='_compute_attendance_rate',
        store=True,
        digits=(16, 0),
        aggregator='avg',
    )

    @api.depends('registration_ids.state')
    def _compute_attendance_rate(self):
        for event in self:
            registrations = event.registration_ids
            taken = len(registrations.filtered(lambda r: r.state in ('open', 'done')))
            attended = len(registrations.filtered(lambda r: r.state == 'done'))
            rate = attended / taken if taken else 0.0
            event.attendance_rate = rate
            event.attendance_percent = rate * 100

    def write(self, vals):
        if not self.env.context.get('eventflow_action'):
            if APPROVAL_FIELDS & set(vals):
                raise UserError(_("Approval fields can only be changed using the workflow buttons."))
            if LOCKED_FIELDS & set(vals) and any(
                event.approval_state == 'approved' for event in self
            ):
                raise UserError(_(
                    "This event is approved, so its name, dates and seat limit are locked. "
                    "Ask a manager to reset it to draft before changing them."
                ))
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
        self._check_eventflow_group('eventflow_management.group_eventflow_staff')
        is_manager = self.env.user.has_group('eventflow_management.group_eventflow_manager')
        if not is_manager and any(event.approval_state != 'rejected' for event in self):
            raise AccessError(_("Only Event Managers can reset events that are not rejected."))
        self.with_context(eventflow_action=True).write({
            'approval_state': 'draft',
            'approved_by': False,
            'approved_date': False,
            'rejection_reason': False,
        })