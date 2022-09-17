from django.test import TestCase

from ..models import Group, User, Post
from ..constants import MAX_CHAR_LENGTH


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый тайтл',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост dавпав апрваопловап авлпрваполр рвап',
        )

    def test_model_post_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        self.assertEqual(self.post.text[:MAX_CHAR_LENGTH],
                         str(self.post), 'текст при ошибке')

    def test_model_group_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        self.assertEqual(f"Группа {self.group.title}", str(self.group))
