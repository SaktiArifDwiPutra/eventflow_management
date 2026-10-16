from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

APPROVAL_FIELDS = {'approval_state', 'approved_by', 'approved_date', 'submitted_by'}
LOCKED_FIELDS = {'name', 'date_begin', 'date_end', 'seats_max', 'seats_limited'}
APPROVAL_ACTIVITY_SUMMARY = 'Approval needed'


class EventEvent(models.Model):
    _inherit = 'event.event'

    approval_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Approval Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(copy=False)
    cancel_reason = fields.Text(copy=False)
    submitted_by = fields.Many2one('res.users', readonly=True, copy=False)
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

    def _get_attendance_list_registrations(self):
        self.ensure_one()
        return self.registration_ids.filtered(
            lambda r: r.state in ('open', 'done')
        ).sorted('name')

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

    def _eventflow_managers(self):
        users = self.env['res.users'].search([('share', '=', False)])
        return users.filtered(
            lambda u: u.has_group('eventflow_management.group_eventflow_manager')
        )

    def _close_approval_activities(self, feedback):
        activities = self.activity_ids.filtered(
            lambda a: a.summary == APPROVAL_ACTIVITY_SUMMARY
        )
        activities.action_feedback(feedback=feedback)

    def _notify_submitter(self, body):
        self.ensure_one()
        submitter = self.submitted_by
        if submitter and submitter != self.env.user:
            self.message_post(
                body=body,
                partner_ids=submitter.partner_id.ids,
                subtype_xmlid='mail.mt_comment',
            )

    def action_submit(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_staff')
        self.with_context(eventflow_action=True).write({
            'approval_state': 'submitted',
            'submitted_by': self.env.user.id,
        })
        managers = self._eventflow_managers()
        for event in self:
            for manager in managers:
                event.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=manager.id,
                    summary=APPROVAL_ACTIVITY_SUMMARY,
                    note=_("This event was submitted and is waiting for your approval."),
                )

    def action_approve(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        self.with_context(eventflow_action=True).write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        self._close_approval_activities(_("Approved"))
        for event in self:
            event._notify_submitter(
                _("Your event was approved by %s.", self.env.user.name)
            )

    def action_reject(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        if any(not event.rejection_reason for event in self):
            raise UserError(_("Please fill in the rejection reason before rejecting."))
        self.with_context(eventflow_action=True).write({'approval_state': 'rejected'})
        self._close_approval_activities(_("Rejected"))
        for event in self:
            event._notify_submitter(_(
                "Your event was rejected by %(user)s. Reason: %(reason)s",
                user=self.env.user.name,
                reason=event.rejection_reason,
            ))

    def action_cancel_event(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_manager')
        if any(event.approval_state != 'approved' for event in self):
            raise UserError(_("Only approved events can be cancelled."))
        if any(not event.cancel_reason for event in self):
            raise UserError(_("Please fill in the cancellation reason before cancelling."))
        self.with_context(eventflow_action=True).write({'approval_state': 'cancelled'})
        for event in self:
            event.registration_ids.filtered(
                lambda r: r.state in ('draft', 'open')
            ).action_cancel()
            event._notify_submitter(_(
                "Your event was cancelled by %(user)s. Reason: %(reason)s",
                user=self.env.user.name,
                reason=event.cancel_reason,
            ))

    def action_reset_draft(self):
        self._check_eventflow_group('eventflow_management.group_eventflow_staff')
        if any(event.approval_state == 'cancelled' for event in self):
            raise UserError(_("Cancelled events cannot be reset to draft."))
        is_manager = self.env.user.has_group('eventflow_management.group_eventflow_manager')
        if not is_manager and any(event.approval_state != 'rejected' for event in self):
            raise AccessError(_("Only Event Managers can reset events that are not rejected."))
        self.with_context(eventflow_action=True).write({
            'approval_state': 'draft',
            'approved_by': False,
            'approved_date': False,
            'rejection_reason': False,
        })