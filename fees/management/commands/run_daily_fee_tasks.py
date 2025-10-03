# fees/management/commands/run_daily_fee_tasks.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from fees.models import DailyTaskLog, StudentFeeAssignment, EMISchedule
from fees.utils import check_and_lock_courses, auto_unlock_courses, calculate_late_fees_for_overdue, send_payment_reminders
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run daily fee management tasks automatically'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force run even if already completed today',
        )
    
    def handle(self, *args, **options):
        today = date.today()
        force = options['force']
        
        # Check if already run today
        existing_log = DailyTaskLog.objects.filter(
            run_date=today,
            status='completed'
        ).first()
        
        if existing_log and not force:
            self.stdout.write(
                self.style.WARNING(f'Daily tasks already completed today at {existing_log.run_time}')
            )
            return
        
        # Create or get today's log
        task_log, created = DailyTaskLog.objects.get_or_create(
            run_date=today,
            defaults={'status': 'pending'}
        )
        
        task_log.status = 'running'
        task_log.save()
        
        try:
            self.stdout.write('Starting daily fee management tasks...')
            
            # 1. Lock courses for overdue payments
            self.stdout.write('Checking and locking courses for overdue payments...')
            locked_count = check_and_lock_courses()
            task_log.courses_locked = locked_count
            self.stdout.write(f'Locked {locked_count} courses')
            
            # 2. Auto-unlock courses based on unlock dates
            self.stdout.write('Checking and unlocking courses...')
            unlocked_count = auto_unlock_courses()
            task_log.courses_unlocked = unlocked_count
            self.stdout.write(f'Unlocked {unlocked_count} courses')
            
            # 3. Calculate and apply late fees
            self.stdout.write('Processing late fees for overdue payments...')
            late_fee_result = calculate_late_fees_for_overdue()
            task_log.late_fees_applied = late_fee_result.get('processed_count', 0)
            self.stdout.write(f'Applied late fees to {task_log.late_fees_applied} EMIs')
            
            # 4. Send payment reminders
            self.stdout.write('Sending payment reminders...')
            reminder_count = send_payment_reminders()
            task_log.reminders_sent = reminder_count
            self.stdout.write(f'Sent {reminder_count} payment reminders')
            
            # 5. Calculate total overdue amount
            overdue_amount = EMISchedule.objects.filter(
                status='overdue',
                due_date__lt=today
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            task_log.total_overdue_amount = overdue_amount
            
            # Mark as completed
            task_log.status = 'completed'
            task_log.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Daily tasks completed successfully!\n'
                    f'Courses locked: {locked_count}\n'
                    f'Courses unlocked: {unlocked_count}\n'
                    f'Late fees applied: {task_log.late_fees_applied}\n'
                    f'Reminders sent: {reminder_count}\n'
                    f'Total overdue amount: ${overdue_amount}'
                )
            )
            
        except Exception as e:
            task_log.status = 'failed'
            task_log.error_message = str(e)
            task_log.save()
            
            logger.error(f'Daily fee tasks failed: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Daily tasks failed: {str(e)}')
            )
            raise e