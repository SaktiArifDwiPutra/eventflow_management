from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestEventFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff = new_test_user(
            cls.env, login='ef_staff',
            groups='base.group_user,eventflow_management.group_eventflow_staff',
        )
        cls.manager = new_test_user(
            cls.env, login='ef_manager',
            groups='base.group_user,eventflow_management.group_eventflow_manager',
        )
        cls.event = cls.env['event.event'].with_user(cls.staff).create({
            'name': 'Test Event',
            'date_begin': fields.Datetime.now() + timedelta(days=1),
            'date_end': fields.Datetime.now() + timedelta(days=2),
        }).sudo()

    def _registration_vals(self):
        return {
            'event_id': self.event.id,
            'name': 'Alice',
            'email': 'alice@example.com',
        }

    def test_registration_blocked_for_draft_event(self):
        with self.assertRaises(UserError):
            self.env['event.registration'].create(self._registration_vals())

    def test_registration_allowed_for_approved_event(self):
        self.event.with_context(eventflow_action=True).write(
            {'approval_state': 'approved'}
        )
        registration = self.env['event.registration'].create(self._registration_vals())
        self.assertEqual(registration.event_id, self.event)

    def test_direct_write_to_approval_state_blocked(self):
        with self.assertRaises(UserError):
            self.event.write({'approval_state': 'approved'})

    def test_staff_cannot_approve_but_manager_can(self):
        self.event.with_user(self.staff).action_submit()
        self.assertEqual(self.event.approval_state, 'submitted')
        with self.assertRaises(AccessError):
            self.event.with_user(self.staff).action_approve()
        self.event.with_user(self.manager).action_approve()
        self.assertEqual(self.event.approval_state, 'approved')
        self.assertEqual(self.event.approved_by, self.manager)

    def test_reject_requires_reason(self):
        self.event.with_user(self.staff).action_submit()
        with self.assertRaises(UserError):
            self.event.with_user(self.manager).action_reject()
        self.event.rejection_reason = 'Budget not approved'
        self.event.with_user(self.manager).action_reject()
        self.assertEqual(self.event.approval_state, 'rejected')

    def test_staff_can_reset_rejected_but_not_approved(self):
        self.event.with_user(self.staff).action_submit()
        self.event.rejection_reason = 'Needs more detail'
        self.event.with_user(self.manager).action_reject()
        self.event.with_user(self.staff).action_reset_draft()
        self.assertEqual(self.event.approval_state, 'draft')

        self.event.with_user(self.staff).action_submit()
        self.event.with_user(self.manager).action_approve()
        with self.assertRaises(AccessError):
            self.event.with_user(self.staff).action_reset_draft()
        self.event.with_user(self.manager).action_reset_draft()
        self.assertEqual(self.event.approval_state, 'draft')

    def test_approved_event_core_fields_locked(self):
        self.event.write({'name': 'Renamed while draft'})
        self.event.with_user(self.staff).action_submit()
        self.event.with_user(self.manager).action_approve()
        with self.assertRaises(UserError):
            self.event.write({'name': 'Renamed after approval'})
        with self.assertRaises(UserError):
            self.event.write({'seats_max': 99})
        self.event.with_user(self.manager).action_reset_draft()
        self.event.write({'name': 'Renamed after reset'})
        self.assertEqual(self.event.name, 'Renamed after reset')

    def test_submit_creates_manager_activity_and_approve_closes_it(self):
        def manager_activities():
            return self.event.activity_ids.filtered(
                lambda a: a.user_id == self.manager and a.summary == 'Approval needed'
            )

        self.event.with_user(self.staff).action_submit()
        self.assertEqual(len(manager_activities()), 1)
        self.event.with_user(self.manager).action_approve()
        self.assertFalse(manager_activities())

    def test_submitter_notified_on_reject_and_approve(self):
        self.event.with_user(self.staff).action_submit()
        self.assertEqual(self.event.submitted_by, self.staff)

        self.event.rejection_reason = 'Needs more detail'
        self.event.with_user(self.manager).action_reject()
        notified = self.event.message_ids.filtered(
            lambda m: self.staff.partner_id in m.partner_ids
        )
        self.assertTrue(any('Needs more detail' in (m.body or '') for m in notified))

        self.event.with_user(self.staff).action_reset_draft()
        self.event.with_user(self.staff).action_submit()
        self.event.with_user(self.manager).action_approve()
        notified = self.event.message_ids.filtered(
            lambda m: self.staff.partner_id in m.partner_ids
        )
        self.assertTrue(any('approved' in (m.body or '') for m in notified))

    def test_staff_visibility_rule(self):
        other = self.env['event.event'].create({
            'name': 'Other Event',
            'date_begin': fields.Datetime.now() + timedelta(days=1),
            'date_end': fields.Datetime.now() + timedelta(days=2),
        })

        domain = [('id', 'in', [self.event.id, other.id])]
        Event = self.env['event.event']
        self.assertEqual(Event.with_user(self.staff).search(domain), self.event)
        other.with_context(eventflow_action=True).write({'approval_state': 'approved'})
        self.assertEqual(
            Event.with_user(self.staff).search(domain), self.event | other
        )

        self.assertEqual(
            Event.with_user(self.manager).search(domain), self.event | other
        )

    def test_staff_registration_visibility_rule(self):
        Registration = self.env['event.registration']
        other = self.env['event.event'].create({
            'name': 'Other Event',
            'date_begin': fields.Datetime.now() + timedelta(days=1),
            'date_end': fields.Datetime.now() + timedelta(days=2),
        })
        for event in (self.event, other):
            event.with_context(eventflow_action=True).write(
                {'approval_state': 'approved'}
            )
        reg_own = Registration.create({
            'event_id': self.event.id, 'name': 'Alice', 'email': 'alice@example.com',
        })
        reg_other = Registration.create({
            'event_id': other.id, 'name': 'Bob', 'email': 'bob@example.com',
        })
        other.with_context(eventflow_action=True).write({'approval_state': 'draft'})

        domain = [('id', 'in', [reg_own.id, reg_other.id])]
        self.assertEqual(Registration.with_user(self.staff).search(domain), reg_own)
        self.assertEqual(
            Registration.with_user(self.manager).search(domain), reg_own | reg_other
        )

    def test_checkin_only_while_event_is_running(self):
        Registration = self.env['event.registration']

        self.event.with_context(eventflow_action=True).write(
            {'approval_state': 'approved'}
        )
        future_reg = Registration.create({
            'event_id': self.event.id, 'name': 'Alice', 'email': 'alice@example.com',
        })
        with self.assertRaises(UserError):
            future_reg.write({'state': 'done'})

        running = self.env['event.event'].create({
            'name': 'Running Event',
            'date_begin': fields.Datetime.now() - timedelta(hours=1),
            'date_end': fields.Datetime.now() + timedelta(hours=1),
        })
        running.with_context(eventflow_action=True).write(
            {'approval_state': 'approved'}
        )
        running_reg = Registration.create({
            'event_id': running.id, 'name': 'Bob', 'email': 'bob@example.com',
        })
        running_reg.write({'state': 'done'})
        self.assertEqual(running_reg.state, 'done')

    def test_attendance_list_registrations(self):
        self.event.with_context(eventflow_action=True).write(
            {'approval_state': 'approved'}
        )
        Registration = self.env['event.registration']
        vals = {'event_id': self.event.id}
        zed = Registration.create(dict(vals, name='Zed', email='zed@example.com'))
        Registration.create(dict(vals, name='Amy', email='amy@example.com'))
        cancelled = Registration.create(dict(vals, name='Cat', email='cat@example.com'))
        cancelled.write({'state': 'cancel'})

        listed = self.event._get_attendance_list_registrations()
        self.assertEqual(listed.mapped('name'), ['Amy', 'Zed'])
        self.assertNotIn(cancelled, listed)
        self.assertIn(zed, listed)

    def test_cancel_event_cancels_registrations(self):
        Registration = self.env['event.registration']
        self.event.with_context(eventflow_action=True).write(
            {'approval_state': 'approved'}
        )
        reg = Registration.create({
            'event_id': self.event.id, 'name': 'Alice', 'email': 'alice@example.com',
        })

        with self.assertRaises(AccessError):
            self.event.with_user(self.staff).action_cancel_event()
        with self.assertRaises(UserError):
            self.event.with_user(self.manager).action_cancel_event()

        self.event.cancel_reason = 'Venue unavailable'
        self.event.with_user(self.manager).action_cancel_event()
        self.assertEqual(self.event.approval_state, 'cancelled')
        self.assertEqual(reg.state, 'cancel')

        with self.assertRaises(UserError):
            Registration.create({
                'event_id': self.event.id, 'name': 'Bob', 'email': 'bob@example.com',
            })
        with self.assertRaises(UserError):
            self.event.with_user(self.manager).action_reset_draft()