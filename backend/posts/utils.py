import regex

from django.conf import settings


URL_PATTERN = regex.compile(r'https?://\S+')
GRAPHEME_PATTERN = regex.compile(r'\X')


def content_length(content):
    without_urls, url_count = URL_PATTERN.subn('', content)
    return len(GRAPHEME_PATTERN.findall(without_urls)) + url_count * settings.POST_URL_LENGTH