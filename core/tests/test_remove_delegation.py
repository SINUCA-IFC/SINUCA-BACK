from core.tests.test_registration_approval import RegistrationApprovalTests


class RemoveDelegationTests(RegistrationApprovalTests):
    def test_organizer_removes_membership_not_account(self):
        self.authenticate(self.organizer)
        response = self.client.post(f'/api/usuarios/{self.student.pk}/remover-delegacao/', {'country': self.country.pk})
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.country_id)
        self.assertTrue(self.student.is_active)
        self.assertTrue(response.data['approval_pending'])

    def test_wrong_country_is_not_removed(self):
        self.authenticate(self.organizer)
        response = self.client.post(f'/api/usuarios/{self.student.pk}/remover-delegacao/', {'country': self.other_country.pk})
        self.assertEqual(response.status_code, 400)
        self.student.refresh_from_db()
        self.assertEqual(self.student.country_id, self.country.pk)

    def test_student_cannot_remove_members(self):
        self.authenticate(self.student)
        response = self.client.post(f'/api/usuarios/{self.student.pk}/remover-delegacao/', {'country': self.country.pk})
        self.assertEqual(response.status_code, 403)
