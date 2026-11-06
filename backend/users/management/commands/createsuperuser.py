import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a superuser together with their personal profile.'

    def add_arguments(self, parser):
        parser.add_argument('--email')
        parser.add_argument('--username')
        parser.add_argument('--noinput', '--no-input', action='store_false', dest='interactive')

    def handle(self, *args, **options):
        User = get_user_model()

        email = options['email'] or os.environ.get('DJANGO_SUPERUSER_EMAIL')
        username = options['username'] or os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if options['interactive']:
            email = email or input('E-mail: ').strip()
            username = username or (input('Username: ')).strip()

            while password is None:
                first = getpass.getpass('Password: ')
                second = getpass.getpass('Password (again): ')

                if first != second:
                    self.stderr.write('Passwords do not match.')
                    continue

                try:
                    validate_password(first, User(email=email))

                except ValidationError as e:
                    self.stderr.write('\n'.join(e.messages))
                    continue

                password = first

        if not email or not username or not password:
            raise CommandError('E-mail, username and password are required.')

        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f'User with e-mail {email} already exists.')

        try:
            User.objects.create_superuser(email=email, password=password, handle=username)

        except ValidationError as e:
            raise CommandError('; '.join(e.messages))

        self.stdout.write(self.style.SUCCESS(f'Superuser {email} (@{username.lower()}) created.'))