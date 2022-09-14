from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .utils import pagination

POST_TITLE_LENGTH = 30


def index(request):
    template = 'posts/index.html'
    posts = Post.objects.order_by('-pub_date')
    context = pagination(posts, request)
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(
        group=group,
    ).order_by('-pub_date')
    context = {'group': group}
    context.update(pagination(posts, request))

    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    following = (request.user.is_authenticated and Follow.objects.filter(
            user=request.user,
            author=author
    ).exists())
    posts = author.posts.all().order_by('-pub_date')
    context = {'author': author, 'following': following}
    context.update(pagination(posts, request))

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    all_comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': all_comments
    }

    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()

        return redirect('posts:profile', request.user)

    context = {'form': form}

    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()

        return redirect('posts:post_detail', post_id)

    context = {
        'form': form,
        'is_edit': True,
    }

    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('posts:post_detail', post_id)
    return redirect('posts:post_detail', post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    context = {
        'title': 'Избранные авторы',
    }
    context.update(pagination(posts, request))

    return render(request, 'posts/follow.html', context)

@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follower = request.user
    # following = False
    follower_list = Follow.objects.filter(author=author, user=follower)
    if follower_list.exists() or follower == author:
        return redirect('posts:index')
    Follow.objects.create(
        author=author,
        user=follower
    )
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follower = request.user
    follower_list = Follow.objects.filter(author=author, user=follower)
    if not follower_list.exists():
        return redirect('posts:index')
    follower_list.delete()
    return redirect('posts:profile', username)


