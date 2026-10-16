from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestEventFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': 'Test Event',
            'date_begin': fields.Datetime.now() + timedelta(days=1),
            'date_end': fields.Datetime.now() + timedelta(days=2),
        })
        cls.staff = new_test_user(
            cls.env, login='ef_staff',
            groups='base.group_user,eventflow_management.group_eventflow_staff',
        )
        cls.manager = new_test_user(
            cls.env, login='ef_manager',
            groups='base.group_user,eventflow_management.group_eventflow_manager',
        )

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