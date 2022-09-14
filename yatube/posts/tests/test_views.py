from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Post, Group, User, Follow
from posts.utils import PAGINATOR_COUNT


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = User.objects.create_user(username='First_user')
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
        cls.author_user.force_login(user)
        cls.group = Group.objects.create(
            title='First_group',
            slug='First',
            description='Описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.profile_user = reverse(
            'posts:profile',
            kwargs={'username': cls.post.author}
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
        self.user = User.objects.create_user(username='Sandoren')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """проверка корректных темплейтов"""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_user.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_author_in_profile(self):
        """проверка автора профиля"""
        response = self.author_user.get(
            TaskPagesTests.profile_user
        )
        self.assertIn('author', response.context)
        self.assertIsInstance(response.context['author'], User)
        self.assertEquals(
            response.context['author'].username,
            TaskPagesTests.post.author.username
        )

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

    def test_all_page_show_correct_context_for_post(self):
        """проверка корректности контекста у постов"""
        for reverse_name, post_context in self.page_urls.items():
            with self.subTest(post_context=post_context):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(
                    first_object.text,
                    self.post.text
                )
                self.assertEqual(
                    first_object.group.id,
                    self.group.id
                )
                self.assertEqual(
                    first_object.id, self.post.id
                )
                self.assertEqual(
                    first_object.author,
                    self.post.author
                )
                self.assertEqual(
                    first_object.image,
                    self.post.image
                )

    def test_post_detail_pages_show_correct_context(self):
        """проверка корректности контекста у post_detail"""
        url = reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        response = self.authorized_client.get(url)
        context_post = response.context['post']
        self.assertEqual(
            context_post.text,
            self.post.text
        )
        self.assertEqual(
            context_post.group.id,
            self.group.id
        )
        self.assertEqual(
            context_post.id,
            self.post.id
        )
        self.assertEqual(
            context_post.author,
            self.post.author
        )
        self.assertEqual(
            context_post.image,
            self.post.image
        )

    def test_page_form_show_correct_context(self):
        """проверка корректности контекста у формы"""
        for address, args in self.response_list:
            with self.subTest(address=address):
                response = self.author_user.get(address)
                form_fields = response.context['form']
                self.assertIsInstance(form_fields, PostForm)
                for variable, value in args.items():
                    self.assertIn(
                        variable,
                        response.context
                    )
                    self.assertEquals(
                        response.context[variable],
                        value
                    )

    def test_cache(self):
        old_response = self.author_user.get(
            reverse('posts:index')
        )

        new_post = Post.objects.create(
            author=self.user,
            text='text',
        )

        old_post_lists = [i for i in old_response.context['page_obj']]

        cache.clear()

        new_response = self.author_user.get(
            reverse('posts:index')
        )
        new_post_lists = [i for i in new_response.context['page_obj']]
        post_difference = set(new_post_lists).difference(set(old_post_lists))

        self.assertEqual(len(post_difference), 1)
        self.assertIn(new_post, post_difference)


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
        self.user = User.objects.create_user(username='Sandoren')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_count_posts_on_page(self):
        """проверка кол-ва постов на странице"""
        for reverse_name, (post_list, num_posts) in self.paginator_obj.items():
            with self.subTest(post_list=post_list):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context[post_list]),
                                 num_posts)

    def test_groups_are_different(self):
        """проверка того что группы отличаются"""
        response = self.client.get(
            reverse('posts:group_list',
                    kwargs={'slug': PaginatorViewsTest.group2.slug}
                    )
        )
        post_group2_quantity = len(response.context['page_obj'])
        self.assertEqual(post_group2_quantity, 0)

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
            self.assertTrue(len(response.context['page_obj']))
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
        self.guest_client = Client()
        self.authorized_client_other = Client()
        self.authorized_client_other.force_login(self.other_user)

    def test_authorised_user_can_follow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей.
        """

        response = self.authorised_user.get(
            reverse('posts:follow_index')
        )

        expected_posts = []
        user_following = self.users[0].follower.all()
        for following in user_following:
            following_posts = [i for i in following.author.posts.all()]
            expected_posts += following_posts

        expected_posts.sort(key=lambda x: x.pub_date, reverse=True)
        context_posts = list(response.context['page_obj'])

        self.assertListEqual(
            expected_posts,
            context_posts,
            msg='Ожидаемые посты не попали в подписки.'
        )
        self.assertEqual(
            len(expected_posts),
            len(context_posts),
            msg='Количество жжидаемые постов от подписок не соотвествует'
                'полученным постам.'
        )

    def test_authorised_user_can_unfollow(self):
        """
        Авторизованный пользователь может отписываться от
        пользователей.
        """

        old_user_following = [i.author for i in self.users[0].follower.all()]

        self.authorised_user.get(
            reverse('posts:profile_unfollow',
                    kwargs={
                        'username': self.users[1].username
                    }
                    )
        )

        new_user_following = [i.author for i in self.users[0].follower.all()]
        following_difference = set(old_user_following).difference(
            set(new_user_following)
        )

        self.assertEqual(len(following_difference), 1)
        self.assertIn(self.users[1], following_difference)
