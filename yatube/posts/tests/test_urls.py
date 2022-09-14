from http import HTTPStatus

from django.test import TestCase, Client

from ..models import Post, Group, User


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='First_user')
        auth_user = User.objects.create_user(username='HasNoName')
        cls.author_user = Client()
        cls.authorized_client = Client()
        cls.author_user.force_login(cls.user)
        cls.authorized_client.force_login(auth_user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='First',
            description='Описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.urls_status_for_guest = (
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.user}/',
            f'/posts/{cls.post.id}/'
        )
        cls.urls_status_for_auth_user_and_author = (
            ('/create/', cls.authorized_client),
            (f'/posts/{cls.post.id}/edit/', cls.author_user)
        )
        cls.templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
        }

    def test_urls_status_for_guest(self):
        """URL-получает http status-ok.Доступен неавторизированному юзеру"""
        for address in self.urls_status_for_guest:
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_status_for_auth_user_and_author(self):
        """URL-получает http status-ok."""
        for address, user in self.urls_status_for_auth_user_and_author:
            with self.subTest(address=address, user=user):
                response = user.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for address, template in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_user.get(address)
                self.assertTemplateUsed(response, template)

    def test_unexisting_page(self):
        """Тест проверяет доступность несуществующей страницы."""
        response = self.authorized_client.get(
            f'/profile/{self.user.username}/'
        )
        self.assertTrue(response.status_code, HTTPStatus.NOT_FOUND)

    def test_redirect_not_author_post(self):
        """проверка редиректа не автора поста."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_redirect_guest_user_from_edit(self):
        """проверка редиректа неавторизованного
        пользователя со стр редактирования"""
        response = self.client.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )

    def test_redirect_guest_user_from_create(self):
        """проверка редиректа неавторизованного
        пользователя со стр создания"""
        response = self.client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')
