from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group, User, Follow, Comment
from ..constants import PAGINATOR_COUNT
from .utils import compare_fields


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='First_user')
        cls.user2 = User.objects.create_user(username='Second_user')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author_user = Client()
        cls.author_user2 = Client()
        cls.author_user.force_login(cls.user)
        cls.author_user2.force_login(cls.user2)
        cls.group = Group.objects.create(
            title='First_group',
            slug='First',
            description='Описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.profile_user = reverse(
            'posts:profile',
            kwargs={'username': cls.post.author}
        )
        cls.test_comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Blah blah blah',
        )
        cls.post2 = Post.objects.create(
            group=cls.group,
            text="Тестовый пост2",
            author=cls.user,
            image=cls.uploaded,
        )
        cls.post3 = Post.objects.create(
            group=cls.group,
            text="Тестовый пост3",
            author=cls.user2,
            image=cls.uploaded,
        )
        cls.profile_user2 = reverse(
            'posts:profile',
            kwargs={'username': cls.post3.author}
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.user2,
        )

        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                'posts/group_list.html',
            cls.profile_user: 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}):
                'posts/create_post.html',
        }
        cls.page_urls = {
            reverse(
                'posts:index'): 'page_obj',
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug}
            ): 'page_obj',
            reverse(
                'posts:profile',
                kwargs={'username': cls.post.author}
            ): 'page_obj',
        }

        cls.response_list = (
            (reverse('posts:post_create'), {}),
            (
                reverse('posts:post_edit',
                        kwargs={
                            'post_id': cls.post.id
                        }),
                {'is_edit': True})
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """проверка корректных темплейтов"""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_user.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_author_in_profile_correct_context(self):
        """проверка контекста профиля """
        response = self.author_user.get(
            TaskPagesTests.profile_user2
        )
        index_of_testing_post = 0

        context_author = response.context.get('author')
        context_follow = response.context.get('following')
        context_post = response.context.get('page_obj')[index_of_testing_post]

        self.assertEqual(
            self.user2,
            context_author,
            msg='В конексте вернулся некорректный автор.'
        )
        self.assertEqual(
            context_follow,
            True,
        )

        self.assertIsInstance(response.context['author'], User)
        fields_to_test = (
            ('text', self.post3.text, 'Некорректный текст поста'),
            ('group', self.post3.group, 'Некорректная группа поста'),
            ('author', self.post3.author, 'Некорректный автор поста'),
        )

        compare_fields(self, fields_to_test, context_post)

    def test_groups_in_group_lists(self):
        """проверка корректности группы в group_lists"""
        response = self.client.get(f'/group/{self.group.slug}/')
        self.assertIn('group', response.context)
        self.assertIsInstance(response.context['group'], Group)
        self.assertEquals(
            response.context['group'].slug,
            self.group.slug
        )
        self.assertEquals(
            response.context['group'].id,
            self.group.id
        )

    def test_index_page_shows_correct_context(self):
        """проверка контекста на главной стр."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(
            first_object.text,
            self.post3.text
        )
        self.assertEqual(
            first_object.group.id,
            self.group.id
        )
        self.assertEqual(
            first_object.id, self.post3.id
        )
        self.assertEqual(
            first_object.author,
            self.post3.author
        )
        self.assertEqual(
            first_object.image,
            self.post3.image
        )

    def test_post_detail_pages_show_correct_context(self):
        """проверка корректности контекста у post_detail"""
        url = reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        response = self.authorized_client.get(url)
        context_post = response.context['post']
        context_comments = response.context['comments']
        self.post_check(context_post, self.post)


        self.assertIn(
            self.test_comment,
            context_comments,
            msg='Новый коммент не отображается на странце поста.')

    def test_comment_is_not_on_detail_page_of_other_post(self):
        """
        Проверяет, что комментарий не отображается на странице другого поста.
        """

        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post2.id}))

        context_comments = response.context['comments']
        self.assertEqual(
            len(context_comments),
            0,
            msg='Новый коммент отображается на странце другого поста.')

    def test_cache(self):
        """тест корректной работы кеша """
        old_response = self.author_user.get(
            reverse('posts:index')
        )

        new_post = Post.objects.create(
            author=self.user,
            text='post_text',
        )
        response = self.authorized_client.get(reverse("posts:index"))
        self.assertNotContains(response, new_post.text)

        old_post_lists = [i for i in old_response.context['page_obj']]

        cache.clear()

        new_response = self.author_user.get(
            reverse('posts:index')
        )
        new_post_lists = [i for i in new_response.context['page_obj']]
        post_difference = set(new_post_lists).difference(set(old_post_lists))

        self.assertEqual(len(post_difference), 1)
        self.assertIn(new_post, post_difference)

    def post_check(self, context_post, post_to_check):
        self.assertEqual(
            context_post.text,
            post_to_check.text
        )
        self.assertEqual(
            context_post.group.id,
            post_to_check.group.id
        )
        self.assertEqual(
            context_post.id,
            post_to_check.id
        )
        self.assertEqual(
            context_post.author,
            post_to_check.author
        )
        self.assertEqual(
            context_post.image,
            post_to_check.image
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='New_user')
        cls.author_user = Client()
        cls.author_user.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Seconddfd',
            description='Описание группы'
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа',
            slug='Seconddfd2',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        Post.objects.bulk_create(
            Post(group=cls.group, author=cls.user, text='Тестовый текст')
            for _ in range(PAGINATOR_COUNT)
        )
        cls.paginator_obj = {
            reverse('posts:index'): ('page_obj', PAGINATOR_COUNT),
            reverse('posts:index') + '?page=2': ('page_obj', 1),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                ('page_obj', PAGINATOR_COUNT),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug})
            + '?page=2': ('page_obj', 1),
            reverse(
                'posts:profile', kwargs={'username': cls.user}):
                ('page_obj', PAGINATOR_COUNT),
            reverse('posts:profile', kwargs={'username': cls.user})
            + '?page=2': ('page_obj', 1),
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_count_posts_on_page(self):
        """проверка кол-ва постов на странице"""
        for reverse_name, (post_list, num_posts) in self.paginator_obj.items():
            with self.subTest(post_list=post_list):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context[post_list]),
                                 num_posts)

    def test_groups_are_in_right_place(self):
        """проверка того что при создании
        поста пост попадает на первую позицию.)"""
        new_post = Post.objects.create(
            group=PaginatorViewsTest.group,
            author=PaginatorViewsTest.user
        )
        for address in (reverse('posts:index'),
                        reverse('posts:group_list',
                                kwargs={'slug': PaginatorViewsTest.group.slug}
                                ),
                        reverse('posts:profile',
                                kwargs={'username': PaginatorViewsTest.user}
                                )):
            response = self.client.get(address)
            self.assertIn('page_obj', response.context)
            post_on_page = response.context['page_obj'][0]
            self.assertEqual(post_on_page.id, new_post.id)


class FollowingTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group1 = Group.objects.create(
            title='title1',
            slug='slug',
            description='description1',
        )

        cls.author = User.objects.create_user(
            username='author'
        )

        cls.users = [
            User.objects.create_user(username=f'user_{i}') for i in range(3)
        ]

        for i, user in enumerate(cls.users):
            for j in range(2):
                Post.objects.create(
                    author=user,
                    text=f'Пост {user}',
                    group=cls.group1
                )
        Follow.objects.create(user=cls.users[0], author=cls.users[1])

    def setUp(self):
        self.authorised_user = Client()
        self.authorised_user.force_login(
            self.users[0])
        self.other_user = User.objects.create_user(username='other_user')
        self.authorized_client_other = Client()
        self.authorized_client_other.force_login(self.other_user)

    def test_authorised_user_can_follow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей.
        """
        Follow.objects.all().delete()

        self.authorised_user.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.other_user.username
            })
        )
        self.assertEqual(
            Follow.objects.filter(user=self.users[0],
                                  author=self.other_user).exists(),
            True
        )

    def test_authorised_user_can_unfollow(self):
        """
        Авторизованный пользователь может отписываться от
        пользователей.
        """

        self.assertEqual(
            True,
            Follow.objects.filter(user=self.users[0],
                                  author=self.users[1]).exists(),
        )

        self.authorised_user.get(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.users[1].username
            })
        )
        self.assertEqual(
            False,
            Follow.objects.filter(user=self.users[0],
                                  author=self.users[1]).exists(),
        )



    def test_new_post_shown_for_follower(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан."""
        Follow.objects.all().delete()
        Follow.objects.create(user=self.users[0], author=self.users[1])

        response = self.authorised_user.get(reverse('posts:follow_index'))
        first_post = response.context['page_obj'][0]
        self.assertEqual(first_post.text, self.users[1].posts.all()[0].text)
        self.assertEqual(first_post.author, self.users[1].posts.all()[0].author)
        self.assertEqual(first_post.group, self.users[1].posts.all()[0].group)

    def test_new_post_not_shown_for_follower(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто на него не подписан."""
        Post.objects.create(
            author=self.other_user,
            text='Новый пост',
            group=self.group1
        )
        response = self.authorised_user.get(reverse('posts:follow_index'))
        count_followed_post = len(response.context['page_obj'])
        self.assertEqual(count_followed_post, 2)