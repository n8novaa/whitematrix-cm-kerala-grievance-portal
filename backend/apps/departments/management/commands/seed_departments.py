from django.core.management.base import BaseCommand
from apps.departments.models import Department


DEPARTMENTS = [
    ('Health and Family Welfare', 'HEALTH', 'Public hospitals, primary health centres, and health services.'),
    ('Public Works Department', 'PWD', 'Roads, bridges, and public infrastructure maintenance.'),
    ('Local Self Government', 'LSGD', 'Municipalities, panchayats, sanitation, and local services.'),
    ('Water Resources', 'WATER', 'Drinking water supply, irrigation, and water infrastructure.'),
    ('General Education', 'EDUCATION', 'Government schools and public education services.'),
    ('Electricity Board', 'KSEB', 'Electricity distribution and related public services.'),
]


class Command(BaseCommand):
    help = 'Seed fictional public-service departments for the prototype.'

    def handle(self, *args, **options):
        created_count = 0
        for name, code, description in DEPARTMENTS:
            _, created = Department.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': description, 'is_active': True},
            )
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(
            f'Department seed complete: {created_count} created, {len(DEPARTMENTS) - created_count} already present.'
        ))
