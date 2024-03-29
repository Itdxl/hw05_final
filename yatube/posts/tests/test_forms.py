import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Group, Post, Comment
from http import HTTPStatus

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка создания поста"""
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'author': self.user,
            'image': uploaded,
        }
        posts_count = Post.objects.count()
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        post = Post.objects.latest('-pub_date')
        self.assertEqual(
            Post.objects.count(), posts_count + 1
        )
        self.assertEqual(
            post.text, form_data['text']
        )
        self.assertEqual(
            post.group.id, form_data['group']
        )
        self.assertEqual(
            post.author, form_data['author']
        )
        self.assertEqual(
            post.image, 'posts/small.gif'
        )

    def test_edit_form(self):
        """Проверка редактирования поста через форму на странице"""
        post_count = Post.objects.count()
        form_data = {
            'group': self.group.id,
            'text': 'Обновленный текст',
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.id,)),
            data=form_data, follow=True)
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.id,)))
        self.assertEqual(Post.objects.count(), post_count)
        post = Post.objects.get(id=self.post.id)
        self.assertEqual(
            post.text, form_data['text']
        )
        self.assertEqual(
            post.group.id, form_data['group']
        )

    def test_nonauthorized_user_create_post(self):
        """Проверка создания записи не авторизированным пользователем."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_add_comment_authorizet(self):
        """CommentForm working."""
        comment_count = Comment.objects.count()
        form_data = {
            'author': self.user,
            'text': 'Тестовый комментарий',
            'post': self.post,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment', args=(self.post.id,)
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            args=(self.post.id,)
        ))
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text']
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data['text'])

    def test_guest_cant_comment(self):
        """guest cant """
        comment_count = Comment.objects.count()
        response = self.client.post(
            reverse(
                'posts:add_comment', args=(self.post.id,)
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/comment/')
        self.assertEqual(Comment.objects.count(), comment_count)
