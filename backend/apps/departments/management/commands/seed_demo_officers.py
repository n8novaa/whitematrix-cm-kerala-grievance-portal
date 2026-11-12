import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.departments.models import Department


DEMO_OFFICERS = (
    ('HEALTH', 'officerhealth@gmail.com'),
    ('LSGD', 'officerlsgd@gmail.com'),
    ('WATER', 'officerwater@gmail.com'),
    ('EDUCATION', 'officereducation@gmail.com'),
    ('KSEB', 'officerkseb@gmail.com'),
)


class Command(BaseCommand):
    help = 'Create missing fictional evaluator officer accounts (excluding PWD).'

    def handle(self, *args, **options):
        password = os.environ.get('DEMO_OFFICER_PASSWORD', '')
        if not password:
            raise CommandError('Set DEMO_OFFICER_PASSWORD before creating demo officers.')

        departments = {}
        for code, email in DEMO_OFFICERS:
            try:
                departments[code] = Department.objects.get(code=code, is_active=True)
            except Department.DoesNotExist as exc:
                raise CommandError(f'Active department {code} is missing; run seed_departments first.') from exc

            existing = User.objects.filter(email=email).first()
            if existing and (existing.role != User.Role.OFFICER or existing.department_id != departments[code].pk):
                raise CommandError(f'{email} already exists but is not the expected officer for {code}.')
            other_officers = User.objects.filter(
                role=User.Role.OFFICER,
                department=departments[code],
            ).exclude(email=email)
            if other_officers.exists():
                raise CommandError(f'{code} already has another officer; refusing to create a duplicate.')

        created = 0
        with transaction.atomic():
            for code, email in DEMO_OFFICERS:
                if User.objects.filter(email=email).exists():
                    continue
                User.objects.create_user(
                    email=email,
                    password=password,
                    role=User.Role.OFFICER,
                    department=departments[code],
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Demo officer seed complete: {created} created, {len(DEMO_OFFICERS) - created} already present; PWD unchanged.'
        ))
