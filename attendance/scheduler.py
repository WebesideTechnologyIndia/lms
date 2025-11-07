# attendance/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from .utils import mark_absent_for_ended_sessions
import logging

logger = logging.getLogger(__name__)

scheduler = None

def start_scheduler():
    """Start the background scheduler for auto-absent marking"""
    
    global scheduler
    
    if scheduler is not None:
        return  # Already running
    
    scheduler = BackgroundScheduler()
    
    # Run every 5 minutes
    scheduler.add_job(
        mark_absent_for_ended_sessions,
        'interval',
        minutes=5,
        id='mark_absent_ended_sessions',
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    logger.info("✅ Attendance scheduler started")