from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post
from http import HTTPStatus

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'

        )
        cls.public_pages_list = [
            ('/', 'posts/index.html'),
            ('/group/test-slug/', 'posts/group_list.html'),
            ('/profile/test_user/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html'),
        ]
        cls.private_pages_list = [
            ('/create/', 'posts/create_post.html'),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html'),
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_public_url_exists_and_accessible_for_all_users(self):
        """Общедоступные cтраницы доступны любому пользователю и используют
        соответствующий шаблон"""
        self.clients = {'guest': self.guest_client,
                        'auth': self.authorized_client, }
        for client in self.clients.values():
            for address, template in self.public_pages_list:
                with self.subTest(client=client, address=address):
                    response = self.client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    self.assertTemplateUsed(response, template)
