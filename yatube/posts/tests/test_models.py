from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from posts.models import Group, Post


User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )

    def test_Post_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__ 15символов."""
        self.assertEqual(str(self.post), self.post.text[:settings.CONST_STR])

    def test_Group_models_have_correct_object_names(self):
        """У моделей корректно работает __str__ для назвний групп."""
        self.assertEqual(str(self.group), self.group.title)

    def test_correct_names(self):
        field_verboses = {
            str(self.post): self.post.text[:settings.CONST_STR],
            str(self.group): self.group.title
        }
        for field, excpected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(field, excpected_value)
