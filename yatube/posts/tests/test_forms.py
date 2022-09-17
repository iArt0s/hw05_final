import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from posts.forms import PostForm, CommentForm
from posts.models import Group, Post, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateForm(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()

        cls.group = Group.objects.create(
            title='First group',
            slug='First',
            description='Первая тестовая группа',
        )

        cls.group_second = Group.objects.create(
            title='Second group',
            slug='Second',
            description='Вторая тестовая группа',
        )

        cls.author = User.objects.create_user(
            username='First_user'
        )

        cls.post = Post.objects.create(
            group=cls.group,
            text="Тестовый пост",
            author=cls.author,
        )

        cls.form = PostForm()

    def setUp(self):
        self.user = User.objects.create_user(username='Second_user')
        self.authorized_client.force_login(self.author)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_form_create(self):
        """проверка создание поста"""

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        old_posts = set(Post.objects.all())

        form_data = {
            'group': self.group.id,
            'text': 'New post',
            'image': uploaded
        }
        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data,
                                               follow=True)

        new_posts = set(Post.objects.all())
        post_difference = new_posts.difference(old_posts)
        self.assertEqual(len(post_difference), 1)
        (new_post,) = post_difference

        self.assertRedirects(
            response, reverse('posts:profile',
                              kwargs={'username': self.author}))
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.id, form_data['group'])
        self.assertEqual(new_post.author, self.author)
        self.assertEqual(new_post.image, 'posts/small.gif')

    def test_form_edit_post(self):
        """проверка редактирования поста"""

        post_count = Post.objects.count()
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        form_data = {
            'group': self.group_second.id,
            'text': 'Edited post',
        }
        self.authorized_client.post(
            url, data=form_data, follow=True)
        edit_post_from_base = Post.objects.get(id=self.post.id)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(edit_post_from_base.text, form_data['text'])
        self.assertEqual(
            edit_post_from_base.group.slug,
            self.group_second.slug
        )
        self.assertEqual(
            edit_post_from_base.author.username,
            self.author.username
        )


class CommentCreationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.authorized_client = Client()

        cls.group = Group.objects.create(
            title='First group',
            slug='First',
            description='Первая тестовая группа',
        )

        cls.author = User.objects.create_user(
            username='First_user'
        )

        cls.post = Post.objects.create(
            group=cls.group,
            text="Тестовый пост",
            author=cls.author,
        )


class CommentFormTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.not_author = User.objects.create_user(
            username='NOT_Author')

        cls.group1 = Group.objects.create(
            title='title1',
            slug='slug1',
            description='description1',
        )

        cls.form = CommentForm()

        cls.post = Post.objects.create(
            author=cls.author,
            text='text',
            group=cls.group1,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorised_not_post_author_client = Client()
        self.authorised_post_author_client = Client()

        self.authorised_not_post_author_client.force_login(
            self.not_author
        )

        self.authorised_post_author_client.force_login(
            self.author)

    def test_new_comment_is_created_in_db(self):
        """Комментарий создается после отпровки формы."""

        new_comment_text = 'Blah blah blah'
        new_comment_quantity = 1
        comment_count = Comment.objects.count()

        form_data = {
            'text': new_comment_text,
            'author': self.author,
            'comment': self.post
        }

        response = self.authorised_post_author_client.post(
            f'/posts/{self.post.id}/comment/',
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail', kwargs={
                    'post_id': self.post.id
                }
            )
        )

        self.assertEqual(
            Comment.objects.all().count(),
            comment_count + new_comment_quantity,
            msg='Количество комментариев не увеличилось в базе данных.'
        )

        new_comment = Comment.objects.all().first()
        self.assertEqual(
            new_comment.text,
            form_data['text']
        )
        self.assertEqual(
            new_comment.author,
            self.author
        )
        self.assertEqual(
            new_comment.post,
            self.post
        )
