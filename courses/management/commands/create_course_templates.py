import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates empty template files for courses app'

    def handle(self, *args, **options):
        # Template files list
        template_files = [
            'dashboard.html',
            'manage_courses.html', 
            'course_form.html',
            'course_detail.html',
            'delete_course.html',
            'manage_categories.html',
            'category_form.html',
            'delete_category.html',
            'course_modules.html',
            'module_form.html',
            'delete_module.html',
            'module_lessons.html',
            'lesson_form.html',
            'delete_lesson.html',
            'manage_enrollments.html',
            'manual_enrollment.html',
            'analytics.html',
            'catalog.html',
            'course_preview.html',
            'enroll_course.html',
            'my_courses.html',
            'course_content.html',
        ]
        
        # Get current directory of the courses app
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        templates_dir = os.path.join(app_dir, 'templates', 'courses')
        
        # Create templates directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)
        
        created_count = 0
        
        for filename in template_files:
            filepath = os.path.join(templates_dir, filename)
            
            # Create empty file if doesn't exist
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    pass  # Create empty file
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {filename}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'- Skipped {filename} (already exists)')
                )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Done! Created {created_count} template files in {templates_dir}')
        )