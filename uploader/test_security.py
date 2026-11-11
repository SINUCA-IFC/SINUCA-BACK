import io
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection
from django.test import override_settings
from PIL import Image as PillowImage
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Country, Post, User
from uploader.models import Document, Image


def photo(width=2, height=2, padding=0):
    content = io.BytesIO()
    PillowImage.new('RGB', (width, height), color='blue').save(content, format='PNG')
    return SimpleUploadedFile('photo.png', content.getvalue() + b'\0' * padding, content_type='image/png')


def pdf(padding=0):
    return SimpleUploadedFile('document.pdf', b'%PDF-1.4\n%%EOF\n' + b' ' * padding, content_type='application/pdf')


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class UploadSecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.user = User.objects.create_user(email='upload@example.test', country=cls.country)
        cls.other = User.objects.create_user(email='other@example.test', country=cls.country)
        cls.organizer = User.objects.create_user(email='org@example.test', role=User.Role.ORGANIZER)

    def setUp(self):
        cache.clear()
        temporary_media = tempfile.TemporaryDirectory(prefix='sinuca-upload-test-')
        self.media_root = Path(temporary_media.name)
        self.addCleanup(temporary_media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=temporary_media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def test_anonymous_cannot_upload_or_list_media(self):
        for endpoint, file in [('images', photo()), ('documents', pdf())]:
            with self.subTest(endpoint=endpoint):
                url = f'/api/media/{endpoint}/'
                self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertEqual(self.client.post(url, {'file': file}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Image.objects.count(), 0)
        self.assertEqual(Document.objects.count(), 0)

    def test_upload_assigns_owner_and_listing_is_private(self):
        for endpoint, model, file in [('images', Image, photo()), ('documents', Document, pdf())]:
            with self.subTest(endpoint=endpoint):
                self.client.force_authenticate(self.user)
                response = self.client.post(f'/api/media/{endpoint}/', {'file': file, 'owner': self.other.pk})
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                uploaded = model.objects.get()
                self.assertEqual(getattr(uploaded, 'owner_id', None), self.user.pk)
                own = self.client.get(f'/api/media/{endpoint}/')
                self.assertEqual(len(own.data['results']), 1)
                self.client.force_authenticate(self.other)
                other = self.client.get(f'/api/media/{endpoint}/')
                self.assertEqual(other.data['results'], [])
                self.assertNotIn(str(uploaded.attachment_key), str(other.data))

    def test_oversized_files_and_images_with_excessive_dimensions_are_rejected(self):
        self.client.force_authenticate(self.user)
        cases = [
            ('images', photo(padding=5 * 1024 * 1024)),
            ('images', photo(width=4097, height=1)),
            ('documents', pdf(padding=10 * 1024 * 1024)),
            ('documents', SimpleUploadedFile('fake.pdf', b'<html>fake</html>', content_type='application/pdf')),
            ('images', SimpleUploadedFile('fake.png', b'fake', content_type='image/png')),
        ]
        for endpoint, file in cases:
            with self.subTest(endpoint=endpoint, size=file.size):
                response = self.client.post(f'/api/media/{endpoint}/', {'file': file})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Image.objects.count(), 0)
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(UPLOADER_MAX_FILES_PER_USER=1)
    def test_count_quota_covers_images_and_documents_together(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/media/images/', {'file': photo()}).status_code, 201)
        response = self.client.post('/api/media/documents/', {'file': pdf()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(UPLOADER_MAX_BYTES_PER_USER=100)
    def test_storage_quota_counts_existing_bytes(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/media/images/', {'file': photo()}).status_code, 201)
        response = self.client.post('/api/media/documents/', {'file': pdf(padding=50)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Document.objects.count(), 0)

    def test_upload_rate_limit_rejects_excess_requests(self):
        self.client.force_authenticate(self.user)
        for index in range(11):
            response = self.client.post('/api/media/images/', {'file': photo()})
            with self.subTest(index=index):
                self.assertEqual(response.status_code, 201 if index < 10 else 429)
        self.assertEqual(Image.objects.count(), 10)

    def test_registration_saves_photo_with_account_and_owner(self):
        response = self.client.post('/api/registro/', {
            'email': 'new@example.test', 'password': 'Synthetic-password-2026!', 'name': 'Aluno', 'foto': photo(),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='new@example.test')
        self.assertIsNone(user.country_id)
        self.assertIsNotNone(user.foto_id)
        self.assertEqual(getattr(user.foto, 'owner_id', None), user.pk)
        self.assertTrue(user.foto.file.storage.exists(user.foto.file.name))

    def test_invalid_registration_or_photo_does_not_leave_stored_files(self):
        for payload in [
            {'email': 'bad', 'password': 'Synthetic-password-2026!', 'foto': photo()},
            {'email': 'badphoto@example.test', 'password': 'Synthetic-password-2026!',
             'foto': photo(padding=5 * 1024 * 1024)},
        ]:
            response = self.client.post('/api/registro/', payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Image.objects.count(), 0)
        self.assertFalse(User.objects.filter(email='badphoto@example.test').exists())
        self.assertEqual([path for path in self.media_root.rglob('*') if path.is_file()], [])

    def test_registration_cannot_reuse_existing_image_id(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/media/images/', {'file': photo()})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        image_id = response.data['id']
        self.client.force_authenticate(None)
        response = self.client.post('/api/registro/', {
            'email': 'stolen@example.test', 'password': 'Synthetic-password-2026!', 'foto': image_id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email='stolen@example.test').exists())

    def test_registration_rate_limit_also_applies_without_photo(self):
        for index in range(31):
            response = self.client.post('/api/registro/', {
                'email': f'registration-{index}@example.test', 'password': 'Synthetic-password-2026!',
            }, format='json')
            with self.subTest(index=index):
                self.assertEqual(response.status_code, 201 if index < 30 else 429)
        self.assertEqual(User.objects.filter(email__startswith='registration-').count(), 30)

    def test_image_attachment_key_is_usable_only_by_its_owner(self):
        self.client.force_authenticate(self.user)
        uploaded = self.client.post('/api/media/images/', {'file': photo()})
        key = uploaded.data['attachment_key']
        self.client.force_authenticate(self.other)
        response = self.client.patch(f'/api/usuarios/{self.other.pk}/', {'foto_attachment_key': key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.other.refresh_from_db()
        self.assertIsNone(self.other.foto_id)
        self.client.force_authenticate(self.user)
        response = self.client.patch(f'/api/usuarios/{self.user.pk}/', {'foto_attachment_key': key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.foto_id, uploaded.data['id'])

    def test_organizer_cannot_reuse_someone_elses_image_in_public_content(self):
        self.client.force_authenticate(self.user)
        uploaded = self.client.post('/api/media/images/', {'file': photo()})
        self.client.force_authenticate(self.organizer)
        response = self.client.post('/api/postagens/', {
            'title': 'Post', 'content': 'Descrição', 'foto_attachment_key': uploaded.data['attachment_key'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Post.objects.count(), 0)
        response = self.client.patch(f'/api/paises/{self.country.pk}/', {
            'flag_attachment_key': uploaded.data['attachment_key'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_can_publish_own_uploaded_image(self):
        self.client.force_authenticate(self.organizer)
        uploaded = self.client.post('/api/media/images/', {'file': photo()})
        response = self.client.post('/api/postagens/', {
            'title': 'Post', 'content': 'Descrição', 'foto_attachment_key': uploaded.data['attachment_key'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.get().foto_id, uploaded.data['id'])

    def test_existing_images_remain_visible_in_profile_but_not_in_upload_lists(self):
        image = Image.objects.create(file='images/legacy.png')
        self.user.foto = image
        self.user.save(update_fields=['foto'])
        self.client.force_authenticate(self.user)
        profile = self.client.get('/api/usuarios/me/')
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertIn('images/legacy.png', profile.data['foto']['url'])
        uploads = self.client.get('/api/media/images/')
        self.assertEqual(uploads.data['results'], [])

    def test_failed_image_insert_does_not_leave_account_or_file(self):
        def reject_image_insert(execute, sql, params, many, context):
            if sql.startswith('INSERT INTO "uploader_image"'):
                raise DatabaseError('Synthetic image insert failure')
            return execute(sql, params, many, context)

        for endpoint in ['/api/registro/', '/api/media/images/']:
            with self.subTest(endpoint=endpoint):
                self.client.force_authenticate(None if endpoint == '/api/registro/' else self.user)
                payload = {
                    'email': 'rollback@example.test', 'password': 'Synthetic-password-2026!', 'foto': photo(),
                } if endpoint == '/api/registro/' else {'file': photo()}
                with connection.execute_wrapper(reject_image_insert), self.assertRaises(DatabaseError):
                    self.client.post(endpoint, payload)
                self.assertFalse(User.objects.filter(email='rollback@example.test').exists())
                self.assertEqual(Image.objects.count(), 0)
                self.assertEqual([path for path in self.media_root.rglob('*') if path.is_file()], [])
