import langcodes
import unicodedata
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from media.models import MediaAsset

from .models import Post, PostMedia, PostMetrics, Reaction, Repost
from .utils import content_length


REACTION_COUNTERS = {
    Reaction.Value.LIKE: 'likes_count',
    Reaction.Value.DISLIKE: 'dislikes_count',
}

REPOSTABLE_VISIBILITIES = (Post.Visibility.PUBLIC, Post.Visibility.UNLISTED)
REPLYABLE_VISIBILITIES = (Post.Visibility.PUBLIC, Post.Visibility.UNLISTED)


class PostNotAllowed(Exception):
    pass

class InteractionNotAllowed(Exception):
    pass


def create_post(*, author, created_by, content='', visibility, parent=None, media=(), lang=''):
    if author.pk != created_by.pk:
        raise PostNotAllowed('You can only post as yourself.')

    if visibility not in Post.Visibility.values:
        raise ValidationError({'visibility': f'Invalid visibility: {visibility}.'})

    if lang and not langcodes.tag_is_valid(lang):
        raise ValidationError({'lang': f'Invalid language tag: {lang}.'})

    lang = langcodes.standardize_tag(lang) if lang else ''

    content = unicodedata.normalize('NFC', content.strip())

    if not content and not media:
        raise ValidationError({'content': 'Post cannot be empty.'})

    if content_length(content) > settings.POST_MAX_LENGTH:
        raise ValidationError({'content': f'Post cannot be longer than {settings.POST_MAX_LENGTH} characters.'})

    if len(media) > settings.POST_MAX_MEDIA:
        raise ValidationError({'media': f'Post cannot have more than {settings.POST_MAX_MEDIA} media.'})

    if len({asset.pk for asset in media}) != len(media):
        raise ValidationError({'media': 'The same media cannot be attached twice.'})

    if any(asset.owner_id != author.pk for asset in media):
        raise PostNotAllowed('You can only attach your own media.')

    if any(asset.status != MediaAsset.Status.READY for asset in media):
        raise ValidationError({'media': 'All media must be processed before posting.'})

    if PostMedia.objects.filter(media__in=media).exists():
        raise ValidationError({'media': 'Media is already attached to another post.'})

    if parent is not None:
        if parent.is_deleted:
            raise PostNotAllowed('Cannot reply to a deleted post.')

        if parent.visibility not in REPLYABLE_VISIBILITIES:
            raise PostNotAllowed('Only public and unlisted posts can be replied to.')

    with transaction.atomic():
        post = Post.objects.create(
            author=author, created_by=created_by, content=content, visibility=visibility, parent=parent, lang=lang
        )

        PostMedia.objects.bulk_create(
            PostMedia(post=post, media=asset, position=position) for position, asset in enumerate(media)
        )

        if parent is not None:
            PostMetrics.objects.get_or_create(post=parent)
            PostMetrics.objects.filter(post=parent).update(replies_count=F('replies_count') + 1)

        return post


def delete_post(*, post, deleted_by):
    if post.author_id != deleted_by.pk:
        raise PostNotAllowed('You can only delete your own posts.')

    with transaction.atomic():
        deleted = Post.objects.filter(pk=post.pk, deleted_at__isnull=True).update(
            content='', lang='', deleted_at=timezone.now(), deleted_by=deleted_by
        )

        if not deleted:
            return False

        assets = list(MediaAsset.objects.filter(post_item__post=post))
        PostMedia.objects.filter(post=post).delete()
        MediaAsset.objects.filter(pk__in=[asset.pk for asset in assets]).delete()

        for asset in assets:
            if asset.file:
                transaction.on_commit(partial(asset.file.delete, save=False))

        Reaction.objects.filter(post=post).delete()
        Repost.objects.filter(post=post).delete()
        PostMetrics.objects.filter(post=post).update(likes_count=0, dislikes_count=0, reposts_count=0)

        if post.parent_id is not None:
            PostMetrics.objects.filter(post_id=post.parent_id).update(replies_count=F('replies_count') - 1)

        return True


def repost_post(*, profile, created_by, post):
    if post.is_deleted:
        raise InteractionNotAllowed('Post has been deleted.')

    if post.visibility not in REPOSTABLE_VISIBILITIES:
        raise InteractionNotAllowed('Only public and unlisted posts can be reposted.')

    with transaction.atomic():
        repost, created = Repost.objects.get_or_create(
            profile=profile, post=post, defaults={'created_by': created_by}
        )

        if created:
            PostMetrics.objects.get_or_create(post=post)
            PostMetrics.objects.filter(post=post).update(reposts_count=F('reposts_count') + 1)

        return repost


def unrepost_post(*, profile, post):
    with transaction.atomic():
        deleted, _ = Repost.objects.filter(profile=profile, post=post).delete()

        if deleted:
            PostMetrics.objects.filter(post=post).update(reposts_count=F('reposts_count') - 1)

        return bool(deleted)


def like_post(*, profile, created_by, post):
    return _react_to_post(profile=profile, created_by=created_by, post=post, value=Reaction.Value.LIKE)


def unlike_post(*, profile, post):
    return _unreact_post(profile=profile, post=post, value=Reaction.Value.LIKE)


def dislike_post(*, profile, created_by, post):
    return _react_to_post(profile=profile, created_by=created_by, post=post, value=Reaction.Value.DISLIKE)


def undislike_post(*, profile, post):
    return _unreact_post(profile=profile, post=post, value=Reaction.Value.DISLIKE)


def _react_to_post(*, profile, created_by, post, value):
    counter = REACTION_COUNTERS[value]

    if post.is_deleted:
        raise InteractionNotAllowed('Post has been deleted.')

    with transaction.atomic():
        current = Reaction.objects.filter(profile=profile, post=post).first()

        if current is not None and current.value == value:
            return current

        if current is not None:
            _unreact_post(profile=profile, post=post, value=current.value)

        reaction = Reaction.objects.create(profile=profile, created_by=created_by, post=post, value=value)

        PostMetrics.objects.get_or_create(post=post)
        PostMetrics.objects.filter(post=post).update(**{counter: F(counter) + 1})

        return reaction


def _unreact_post(*, profile, post, value):
    counter = REACTION_COUNTERS[value]

    with transaction.atomic():
        deleted, _ = Reaction.objects.filter(profile=profile, post=post, value=value).delete()

        if deleted:
            PostMetrics.objects.filter(post=post).update(**{counter: F(counter) - 1})

        return bool(deleted)
