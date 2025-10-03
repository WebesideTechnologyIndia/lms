# management/commands/create_default_permissions.py
from django.core.management.base import BaseCommand
from userss.models import InstructorPermission

class Command(BaseCommand):
    help = 'Create default instructor permissions'

    def handle(self, *args, **options):
        permissions = [
            {
                'name': 'Content Management',
                'code': 'content_management',
                'description': 'Can create, edit, and manage course content, modules, and lessons',
                'category': 'Course Management'
            },
            {
                'name': 'Email Marketing',
                'code': 'email_marketing',
                'description': 'Can send bulk emails, create email templates, and manage email campaigns',
                'category': 'Email Marketing'
            },
            {
                'name': 'Course Management',
                'code': 'course_management',
                'description': 'Can create, edit, and manage courses',
                'category': 'Course Management'
            },
            {
                'name': 'Batch Management',
                'code': 'batch_management',
                'description': 'Can create and manage course batches',
                'category': 'Course Management'
            },
            {
                'name': 'Student Management',
                'code': 'student_management',
                'description': 'Can view and manage student enrollments and progress',
                'category': 'Student Management'
            },
            {
                'name': 'Analytics View',
                'code': 'analytics_view',
                'description': 'Can view course and student analytics',
                'category': 'Analytics'
            },
            {
                'name': 'Grade Management',
                'code': 'grade_management',
                'description': 'Can assign grades and certificates to students',
                'category': 'Student Management'
            }
        ]

        created_count = 0
        for perm_data in permissions:
            permission, created = InstructorPermission.objects.get_or_create(
                code=perm_data['code'],
                defaults=perm_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created permission: {permission.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Permission already exists: {permission.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new permissions')
        )