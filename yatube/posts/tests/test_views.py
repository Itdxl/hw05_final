from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Follow, Group, Post


User = get_user_model()


class GroupViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.user_author = User.objects.create_user(username='test_user_author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
        )
        cls.group2 = Group.objects.create(
            title='Тестовый заголовок2',
            slug='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

        cls.templates_pages_names = {
            'posts/index.html': reverse('posts:mane_page'),
            'posts/profile.html': (
                reverse('posts:profile',
                        kwargs={'username': cls.user_author.username}
                        )
            ),
            'posts/create_post.html': (
                reverse('posts:post_edit', kwargs={'post_id': cls.post.id})
            ),
            'posts/post_detail.html': (
                reverse('posts:post_detail', kwargs={'post_id': cls.post.id})
            ),
            'posts/group_list.html': (
                reverse('posts:groups', kwargs={'slug': 'test-slug'})
            ),
        }

        cls.no_follow_user = User.objects.create_user(username='First')
        cls.follow_user = User.objects.create_user(username='Second')
        cls.follower = Follow.objects.create(
            user=cls.follow_user, author=cls.user)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.author = Client()
        self.authorized_client.force_login(self.user)
        self.author.force_login(self.user_author)
        self.follower_client = Client()
        self.follower_client.force_login(self.follow_user)
        self.no_follower_client = Client()
        self.no_follower_client.force_login(self.no_follow_user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, reverse_name in self.templates_pages_names.items():
            with self.subTest(template=template):
                response = self.author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def context_test_for_all(self, response):
        post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author.username, self.user.username)
        self.assertEqual(post.group.slug, self.group.slug)
        self.assertEqual(post.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """
        Шаблон index сформирован с правильным контекстом.
        Созданный пост появился на стартовой странице.
        """
        response = self.authorized_client.get(reverse('posts:mane_page'))
        self.context_test_for_all(response)

    def test_group_list_page_show_correct_context(self):
        """
        Шаблон group_list сформирован с правильным контекстом
        Созданный пост появился на странице группы
        """
        response = self.authorized_client.get(reverse(
            'posts:groups', kwargs={'slug': self.group.slug}))
        self.context_test_for_all(response)

    def test_profile_page_show_correct_context(self):
        """
        Шаблон profile сформирован с правильным контекстом
        Созданный пост появился на странице профиля автора
        """
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        self.context_test_for_all(response)

    def test_post_detail_page_show_correct_context(self):
        """
        Шаблон post_detail сформирован с правильным контекстом
        Подробная информация поста появляется на отдельной странице
        """
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').text, self.post.text)

    def test_post_not_on_the_page_not_belongs_to(self):
        """Пост не попал в другую группу"""
        reverse_name = reverse(
            'posts:groups',
            kwargs={'slug': self.group2.slug}
        )
        response = self.authorized_client.get(reverse_name)
        self.assertNotIn(
            self.post, response.context['page_obj']
        )

    def test_post_contain_on_the_page(self):
        """Пост  попал в нужную группу"""
        reverse_name = reverse(
            'posts:groups',
            kwargs={'slug': self.group.slug}
        )
        response = self.authorized_client.get(reverse_name)
        self.assertIn(
            self.post, response.context['page_obj']
        )

    def test_post_contain_in_profile(self):
        """Пост  попал в профиль"""
        reverse_name = reverse(
            'posts:profile',
            kwargs={'username': self.user.username}
        )
        response = self.authorized_client.get(reverse_name)
        self.assertIn(
            self.post, response.context['page_obj']
        )

    def test_post_contain_in_mane_page(self):
        """Пост  попал на главную"""
        reverse_name = reverse(
            'posts:mane_page'
        )
        response = self.authorized_client.get(reverse_name)
        self.assertIn(
            self.post, response.context['page_obj']
        )

    def test_cache_index_page(self):
        """Тест кэширования index."""
        new_post = Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(reverse('posts:mane_page'))
        temp = response.content
        new_post.delete()
        response = self.authorized_client.get(reverse('posts:mane_page'))
        self.assertEqual(response.content, temp)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:mane_page'))
        self.assertNotEqual(response.content, temp)

    def test_follow_index_show_cont(self):
        """Шаблон follow сформирован с правильным контекстом."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        count_post_no_follower = len(response.context['page_obj'])
        Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
            group=self.group,
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']), count_post_follower + 1)
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']), count_post_no_follower)

    def test_user_follow(self):
        """Проверка на создание подписчика."""
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.no_follower_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        self.assertFalse(count_post_follower)
        self.assertTrue(len(response.context['page_obj']))

    def test_follower_delete_to_user(self):
        """Проверка на удаление подписчика."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.follower_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user}))
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertTrue(count_post_follower)
        self.assertFalse(len(response.context['page_obj']))


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'

        )

        posts = [Post(author=cls.user, text=f'Тестовый пост {i}',
                      group=cls.group) for i in range(settings.AMOUNT_TEST)]
        Post.objects.bulk_create(posts, settings.AMOUNT_TEST)

    def test_paginator_first_page_contains_10_posts(self):
        """Колличество постов на первой странице равно 10"""
        response = self.client.get(reverse('posts:mane_page'))
        self.assertEqual(
            len(response.context['page_obj']), settings.AMOUNT_EXPECTED
        )

    def test_paginator_second_page_contains_3_posts(self):
        response = self.guest_client.get(
            reverse('posts:mane_page') + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']),
                         settings.AMOUNT_TEST - settings.AMOUNT_EXPECTED
                         )

    def test_paginator_group_page_contains_10_posts(self):
        """Колличество постов на странице группы  равно 10"""
        response = self.client.get(reverse('posts:groups',
                                           kwargs={'slug': 'test-slug'})
                                   )
        self.assertEqual(
            len(response.context['page_obj']), settings.AMOUNT_EXPECTED
        )

    def test_paginator_profile_page_contains_10_posts(self):
        """Колличество постов на странице профиля равно 10"""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(
            len(response.context['page_obj']), settings.AMOUNT_EXPECTED
        )
