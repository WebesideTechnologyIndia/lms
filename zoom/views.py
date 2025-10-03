from django.shortcuts import render


# zoom/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import *
from .services import ZoomAPIService
from courses.models import Batch

# Add these fixes to your views.py

@login_required
def zoom_config_status(request):
    """API endpoint to check zoom configuration status"""
    try:
        config_ok, config_result = check_zoom_configuration()
        
        if config_ok and isinstance(config_result, ZoomConfiguration):
            # Convert ZoomConfiguration object to dict
            data = {
                'status': 'configured',
                'account_id': config_result.account_id if config_result.account_id else None,
                'client_id': config_result.client_id[:8] + '...' if config_result.client_id else None,
                'configured_at': config_result.created_at.isoformat() if hasattr(config_result, 'created_at') else None,
                'message': 'Zoom is properly configured'
            }
        else:
            data = {
                'status': 'not_configured',
                'message': config_result if isinstance(config_result, str) else 'Zoom configuration is incomplete'
            }
            
    except Exception as e:
        data = {
            'status': 'error',
            'message': f'Error checking Zoom configuration: {str(e)}'
        }
    
    return JsonResponse(data)


def check_zoom_configuration():
    """
    Check if Zoom is properly configured
    Returns: (bool, ZoomConfiguration or str)
    """
    try:
        from .models import ZoomConfiguration
        
        config = ZoomConfiguration.objects.filter(is_active=True).first()
        
        if not config:
            return False, "No Zoom configuration found"
        
        # Check required fields
        if not config.account_id:
            return False, "Account ID is missing"
            
        if not config.client_id:
            return False, "Client ID is missing"
            
        if not config.client_secret:
            return False, "Client Secret is missing"
            
        # Optional: Test API connection
        try:
            zoom_service = ZoomAPIService()
            # You can add a simple API test here if needed
            return True, config
            
        except Exception as api_error:
            return False, f"API connection failed: {str(api_error)}"
            
    except Exception as e:
        return False, f"Configuration check failed: {str(e)}"


class ZoomAPIService:
    """Enhanced Zoom API Service with better error handling"""
    
    def __init__(self):
        self.config = None
        self.access_token = None
        self._initialize_config()
    
    def _initialize_config(self):
        """Initialize Zoom configuration"""
        try:
            from .models import ZoomConfiguration
            self.config = ZoomConfiguration.objects.filter(is_active=True).first()
            
            if not self.config:
                raise ValueError("No active Zoom configuration found")
                
        except Exception as e:
            raise ValueError(f"Failed to initialize Zoom config: {str(e)}")
    
    def _get_access_token(self):
        """Get or refresh access token"""
        if not self.config:
            raise ValueError("Zoom configuration not initialized")
            
        try:
            import requests
            import base64
            
            # Prepare credentials
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'account_credentials',
                'account_id': self.config.account_id
            }
            
            response = requests.post(
                'https://zoom.us/oauth/token',
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return self.access_token
            else:
                error_detail = response.json() if response.content else {}
                raise ValueError(f"Token request failed: {response.status_code} - {error_detail}")
                
        except requests.exceptions.Timeout:
            raise ValueError("Zoom API request timed out")
        except requests.exceptions.ConnectionError:
            raise ValueError("Failed to connect to Zoom API")
        except Exception as e:
            raise ValueError(f"Token generation failed: {str(e)}")
    
    def create_meeting(self, session):
        """Create Zoom meeting for session"""
        try:
            if not self.access_token:
                self._get_access_token()

            import requests
            from datetime import datetime, timezone

            # Combine date + start_time for Zoom
            meeting_start = datetime.combine(session.scheduled_date, session.start_time)

            meeting_data = {
                'topic': session.title,
                'type': 2,  # Scheduled meeting
                'start_time': meeting_start.strftime('%Y-%m-%dT%H:%M:%S'),
                'duration': session.duration_minutes,
                'timezone': 'Asia/Kolkata',
                'agenda': session.description or f'Session for {session.batch.name}',
                'settings': {
                    'host_video': True,
                    'participant_video': True,
                    'join_before_host': False,
                    'mute_upon_entry': True,
                    'waiting_room': True,
                    'audio': 'both',
                    'auto_recording': 'cloud' if session.is_recorded else 'none',
                    'alternative_hosts': '',
                }
            }

            user_identifier = self.config.admin_email or "me"

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                f'https://api.zoom.us/v2/users/{user_identifier}/meetings',
                json=meeting_data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                meeting_info = response.json()

                # Save Zoom details into session
                session.zoom_meeting_id = str(meeting_info['id'])
                session.zoom_join_url = meeting_info['join_url']
                session.zoom_start_url = meeting_info['start_url']
                session.zoom_meeting_password = meeting_info.get('password', '')
                session.save()

                return True, meeting_info
            else:
                error_detail = response.json() if response.content else {}
                return False, f"Zoom meeting creation failed: {response.status_code} - {error_detail}"

        except Exception as e:
            import logging
            logger = logging.getLogger('zoom')
            logger.exception(f'Exception in create_meeting: {str(e)}')
            return False, f"Meeting creation failed: {str(e)}"

    def test_connection(self):
        """Test Zoom API connection"""
        try:
            if not self.access_token:
                self._get_access_token()
            
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://api.zoom.us/v2/users/me',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return True, f"Connected successfully as {user_data.get('email', 'Unknown')}"
            else:
                error_detail = response.json() if response.content else {}
                return False, f"Connection test failed: {response.status_code} - {error_detail}"
                
        except Exception as e:
            return False, f"Connection test error: {str(e)}"


# Update your session_detail view to handle missing CSS
# zoom/views.py - Complete Session Views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, date
from courses.models import Batch, BatchEnrollment
from .utils import (
    create_zoom_meeting_for_session, 
    check_zoom_configuration,
    delete_zoom_meeting
)

# zoom/views.py - Replace your create_session view with this simple version

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime, timedelta, date
from courses.models import Batch, BatchEnrollment





# zoom/views.py - Complete Debug Create Session View

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime, timedelta, date
from courses.models import Batch, BatchEnrollment
import traceback

@login_required
def create_session(request):
    """Create new batch session - FULL DEBUG VERSION"""
    print(f"\n{'='*50}")
    print(f"=== CREATE SESSION DEBUG START ===")
    print(f"Method: {request.method}")
    print(f"User: {request.user}")
    print(f"User ID: {request.user.id}")
    print(f"User role: {getattr(request.user, 'role', 'NO_ROLE_ATTRIBUTE')}")
    print(f"User is authenticated: {request.user.is_authenticated}")
    print(f"{'='*50}")
    
    # Check Zoom config
    try:
        from .models import ZoomConfiguration
        config = ZoomConfiguration.objects.filter(is_active=True).first()
        zoom_configured = bool(config and config.client_id and config.client_secret)
        print(f"Zoom configured: {zoom_configured}")
    except Exception as e:
        print(f"Zoom config error: {e}")
        zoom_configured = False
    
    if request.method == 'POST':
        print(f"\n--- POST DATA RECEIVED ---")
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                print(f"{key}: '{value}'")
        print(f"--- END POST DATA ---\n")
        
        try:
            # Step 1: Extract form data
            print("STEP 1: Extracting form data...")
            batch_id = request.POST.get('batch')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            scheduled_date = request.POST.get('scheduled_date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            session_type = request.POST.get('session_type', 'live_class')
            max_participants = request.POST.get('max_participants', '100')
            is_recorded = bool(request.POST.get('is_recorded'))
            recurring_type = request.POST.get('recurring_type', 'none')
            
            print(f"Batch ID: '{batch_id}'")
            print(f"Title: '{title}'")
            print(f"Scheduled Date: '{scheduled_date}'")
            print(f"Start Time: '{start_time}'")
            print(f"End Time: '{end_time}'")
            print(f"Session Type: '{session_type}'")
            print(f"Max Participants: '{max_participants}'")
            print(f"Is Recorded: {is_recorded}")
            print(f"Recurring Type: '{recurring_type}'")
            
            # Step 2: Basic validation
            print("\nSTEP 2: Basic validation...")
            
            if not batch_id:
                print("ERROR: Batch ID is empty")
                messages.error(request, 'Please select a batch.')
                return redirect('zoom:create_session')
            
            if not title:
                print("ERROR: Title is empty")
                messages.error(request, 'Please enter a session title.')
                return redirect('zoom:create_session')
            
            if not scheduled_date:
                print("ERROR: Scheduled date is empty")
                messages.error(request, 'Please select a date.')
                return redirect('zoom:create_session')
            
            if not start_time:
                print("ERROR: Start time is empty")
                messages.error(request, 'Please select start time.')
                return redirect('zoom:create_session')
            
            if not end_time:
                print("ERROR: End time is empty")
                messages.error(request, 'Please select end time.')
                return redirect('zoom:create_session')
            
            print("Basic validation PASSED")
            
            # Step 3: Get and validate batch
            print(f"\nSTEP 3: Getting batch with ID: {batch_id}")
            try:
                batch = get_object_or_404(Batch, id=batch_id)
                print(f"Batch found: {batch.name} (ID: {batch.id})")
                print(f"Batch course: {batch.course.title}")
                print(f"Batch instructor: {batch.instructor}")
            except Exception as e:
                print(f"ERROR getting batch: {e}")
                messages.error(request, 'Invalid batch selected.')
                return redirect('zoom:create_session')
            
            # Step 4: Permission check
            print(f"\nSTEP 4: Permission check...")
            print(f"User role: {request.user.role}")
            print(f"Batch instructor: {batch.instructor}")
            print(f"User == Batch instructor: {request.user == batch.instructor}")
            
            if request.user.role == 'instructor' and batch.instructor != request.user:
                print("ERROR: Permission denied - not batch instructor")
                messages.error(request, 'You can only create sessions for your own batches.')
                return redirect('zoom:create_session')
            
            print("Permission check PASSED")
            
            # Step 5: Parse and validate dates/times
            print(f"\nSTEP 5: Parsing dates and times...")
            try:
                scheduled_date_obj = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                max_participants_int = int(max_participants)
                
                print(f"Parsed date: {scheduled_date_obj}")
                print(f"Parsed start time: {start_time_obj}")
                print(f"Parsed end time: {end_time_obj}")
                print(f"Max participants: {max_participants_int}")
            except ValueError as e:
                print(f"ERROR parsing dates/times: {e}")
                messages.error(request, 'Invalid date or time format.')
                return redirect('zoom:create_session')
            
            # Step 6: Date validations
            print(f"\nSTEP 6: Date validations...")
            today = date.today()
            print(f"Today: {today}")
            print(f"Scheduled: {scheduled_date_obj}")
            
            if scheduled_date_obj < today:
                print("ERROR: Date is in the past")
                messages.error(request, 'Session date cannot be in the past.')
                return redirect('zoom:create_session')
            
            if start_time_obj >= end_time_obj:
                print("ERROR: Start time >= End time")
                messages.error(request, 'End time must be after start time.')
                return redirect('zoom:create_session')
            
            print("Date validations PASSED")
            
            # Step 7: Create sessions based on type
            print(f"\nSTEP 7: Creating sessions (type: {recurring_type})...")
            
            if recurring_type == 'none':
                print("Creating SINGLE session...")
                
                # Check if BatchSession model has required fields
                print("Checking BatchSession model...")
                try:
                    # Test if model has all required fields
                    test_fields = ['batch', 'title', 'description', 'scheduled_date', 
                                  'start_time', 'end_time', 'session_type', 
                                  'max_participants', 'is_recorded', 'created_by']
                    
                    # Check if recurring fields exist
                    recurring_fields = ['is_recurring', 'recurring_type']
                    for field in recurring_fields:
                        if hasattr(BatchSession, field):
                            print(f"Model has field: {field}")
                        else:
                            print(f"WARNING: Model missing field: {field}")
                    
                except Exception as e:
                    print(f"Error checking model fields: {e}")
                
                print("Creating session object...")
                try:
                    session_data = {
                        'batch': batch,
                        'title': title,
                        'description': description,
                        'scheduled_date': scheduled_date_obj,
                        'start_time': start_time_obj,
                        'end_time': end_time_obj,
                        'session_type': session_type,
                        'max_participants': max_participants_int,
                        'is_recorded': is_recorded,
                        'created_by': request.user
                    }
                    
                    # Add recurring fields if they exist
                    if hasattr(BatchSession, 'is_recurring'):
                        session_data['is_recurring'] = False
                    if hasattr(BatchSession, 'recurring_type'):
                        session_data['recurring_type'] = 'none'
                    
                    print("Session data prepared:")
                    for key, value in session_data.items():
                        print(f"  {key}: {value}")
                    
                    print("Calling BatchSession.objects.create()...")
                    session = BatchSession.objects.create(**session_data)
                    print(f"SUCCESS: Session created with ID: {session.id}")
                    
                    # Try Zoom meeting creation
                    if zoom_configured:
                        print("Attempting Zoom meeting creation...")
                        try:
                            from .services import ZoomAPIService
                            service = ZoomAPIService()
                            success, result = service.create_meeting(session)
                            if success:
                                print(f"Zoom meeting created successfully")
                            else:
                                print(f"Zoom meeting creation failed: {result}")
                        except Exception as zoom_e:
                            print(f"Zoom error (non-critical): {zoom_e}")
                    
                    messages.success(request, f'Session "{title}" created successfully!')
                    print("SUCCESS: Redirecting to session list")
                    return redirect('zoom:session_list')
                    
                except Exception as create_error:
                    print(f"ERROR creating session: {create_error}")
                    print("Full traceback:")
                    traceback.print_exc()
                    messages.error(request, f'Database error: {str(create_error)}')
                    return redirect('zoom:create_session')
            
            else:
                # Recurring sessions logic
                print(f"Creating RECURRING sessions ({recurring_type})...")
                
                recurring_end_date_str = request.POST.get('recurring_end_date')
                if not recurring_end_date_str:
                    print("ERROR: No end date for recurring sessions")
                    messages.error(request, 'End date required for recurring sessions.')
                    return redirect('zoom:create_session')
                
                try:
                    recurring_end_date = datetime.strptime(recurring_end_date_str, '%Y-%m-%d').date()
                    print(f"Recurring end date: {recurring_end_date}")
                except ValueError as e:
                    print(f"ERROR parsing recurring end date: {e}")
                    messages.error(request, 'Invalid recurring end date.')
                    return redirect('zoom:create_session')
                
                if recurring_end_date <= scheduled_date_obj:
                    print("ERROR: End date not after start date")
                    messages.error(request, 'End date must be after start date.')
                    return redirect('zoom:create_session')
                
                # Generate dates
                session_dates = []
                current_date = scheduled_date_obj
                
                if recurring_type == 'daily':
                    print("Generating daily session dates...")
                    while current_date <= recurring_end_date:
                        session_dates.append(current_date)
                        current_date += timedelta(days=1)
                
                elif recurring_type == 'weekly':
                    print("Generating weekly session dates...")
                    weekly_days = request.POST.getlist('weekly_days')
                    print(f"Weekly days selected: {weekly_days}")
                    
                    if not weekly_days:
                        print("ERROR: No weekly days selected")
                        messages.error(request, 'Select at least one day for weekly sessions.')
                        return redirect('zoom:create_session')
                    
                    weekly_days = [int(d) for d in weekly_days]
                    
                    while current_date <= recurring_end_date:
                        current_weekday = current_date.weekday() + 1
                        if current_weekday in weekly_days:
                            session_dates.append(current_date)
                        current_date += timedelta(days=1)
                
                print(f"Generated {len(session_dates)} session dates")
                if not session_dates:
                    print("ERROR: No session dates generated")
                    messages.error(request, 'No valid session dates generated.')
                    return redirect('zoom:create_session')
                
                # Create all sessions
                parent_session = None
                created_count = 0
                
                for i, session_date in enumerate(session_dates):
                    try:
                        session_title = f"{title} - Session {i+1}" if len(session_dates) > 1 else title
                        print(f"Creating session {i+1}/{len(session_dates)}: {session_title}")
                        
                        session_data = {
                            'batch': batch,
                            'title': session_title,
                            'description': description,
                            'scheduled_date': session_date,
                            'start_time': start_time_obj,
                            'end_time': end_time_obj,
                            'session_type': session_type,
                            'max_participants': max_participants_int,
                            'is_recorded': is_recorded,
                            'created_by': request.user
                        }
                        
                        # Add recurring fields if they exist
                        if hasattr(BatchSession, 'is_recurring'):
                            session_data['is_recurring'] = True
                        if hasattr(BatchSession, 'recurring_type'):
                            session_data['recurring_type'] = recurring_type
                        if hasattr(BatchSession, 'recurring_end_date'):
                            session_data['recurring_end_date'] = recurring_end_date
                        if hasattr(BatchSession, 'parent_session'):
                            session_data['parent_session'] = parent_session
                        if hasattr(BatchSession, 'session_sequence'):
                            session_data['session_sequence'] = i + 1
                        
                        session = BatchSession.objects.create(**session_data)
                        print(f"Session {i+1} created with ID: {session.id}")
                        
                        if i == 0:
                            parent_session = session
                        
                        # Try Zoom meeting
                        if zoom_configured:
                            try:
                                from .services import ZoomAPIService
                                service = ZoomAPIService()
                                service.create_meeting(session)
                            except Exception as zoom_e:
                                print(f"Zoom error for session {i+1}: {zoom_e}")
                        
                        created_count += 1
                        
                    except Exception as session_error:
                        print(f"Error creating session {i+1}: {session_error}")
                        continue
                
                if created_count > 0:
                    messages.success(request, f'{created_count} sessions created successfully!')
                    print(f"SUCCESS: {created_count} recurring sessions created")
                    return redirect('zoom:session_list')
                else:
                    print("ERROR: No sessions were created")
                    messages.error(request, 'Failed to create any sessions.')
                    return redirect('zoom:create_session')
            
        except Exception as e:
            print(f"\nFATAL ERROR in create_session: {e}")
            print("Full traceback:")
            traceback.print_exc()
            messages.error(request, f'System error: {str(e)}')
            return redirect('zoom:create_session')
    
    # GET request - show form
    print(f"\nGET REQUEST - Loading form...")
    try:
        batches = Batch.objects.filter(status='active').select_related('course', 'instructor')
        print(f"Found {batches.count()} active batches")
        
        if request.user.role == 'instructor':
            batches = batches.filter(instructor=request.user)
            print(f"Filtered to {batches.count()} batches for instructor")
        
        if not batches.exists():
            print("WARNING: No batches available for this user")
            if request.user.role == 'instructor':
                messages.info(request, 'No active batches assigned to you.')
            else:
                messages.info(request, 'No active batches available.')
        
        context = {
            'batches': batches,
            'zoom_configured': zoom_configured,
            'today': date.today(),
            'user_role': request.user.role,
        }
        
        print(f"Context prepared. Rendering template...")
        return render(request, 'zoom/create_session.html', context)
        
    except Exception as e:
        print(f"ERROR loading form: {e}")
        traceback.print_exc()
        messages.error(request, f'Error loading form: {str(e)}')
        return redirect('zoom:session_list')


@login_required
def batch_details_api(request, batch_id):
    """API for batch details with full debugging"""
    print(f"\n=== BATCH DETAILS API ===")
    print(f"Batch ID requested: {batch_id}")
    print(f"User: {request.user} (Role: {request.user.role})")
    
    try:
        batch = get_object_or_404(Batch, id=batch_id)
        print(f"Batch found: {batch.name}")
        
        # Check permissions
        if request.user.role == 'instructor' and batch.instructor != request.user:
            print("ERROR: Permission denied for batch details")
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        enrolled_count = batch.get_enrolled_count()
        print(f"Enrolled count: {enrolled_count}")
        
        data = {
            'enrolled_count': enrolled_count,
            'max_students': batch.max_students,
            'available_seats': batch.get_available_seats(),
            'course_title': batch.course.title,
            'course_code': batch.course.course_code,
            'instructor_name': batch.instructor.get_full_name() or batch.instructor.username,
        }
        
        print(f"Returning data: {data}")
        return JsonResponse(data)
    
    except Exception as e:
        print(f"ERROR in batch_details_api: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)




def get_form_context(request, zoom_configured):
    """Get context data for the create session form"""
    # Get batches based on user role
    batches = Batch.objects.filter(status='active').select_related('course', 'instructor')
    
    # Check user permissions
    if request.user.role == 'student':
        messages.error(request, 'Students cannot create sessions.')
        return redirect('zoom:dashboard')
    
    # Filter instructor's batches
    if request.user.role == 'instructor':
        batches = batches.filter(instructor=request.user)
    
    if not batches.exists():
        if request.user.role == 'instructor':
            messages.info(request, 'No active batches assigned to you. Contact admin to assign batches.')
        else:
            messages.info(request, 'No active batches available. Create a batch first.')
    
    today = date.today()
    
    context = {
        'batches': batches,
        'zoom_configured': zoom_configured,
        'today': today,
        'form_data': getattr(request, 'POST', None) if request.method == 'POST' else None,
        'session_types': BatchSession.SESSION_TYPE_CHOICES,
        'recurring_types': BatchSession.RECURRING_TYPE_CHOICES,
        'user_role': request.user.role,
    }
    
    return context


def create_single_session(batch, title, description, scheduled_date, start_time, end_time,
                         session_type, max_participants, is_recorded, user, zoom_configured):
    """Create a single session"""
    session = BatchSession.objects.create(
        batch=batch,
        title=title,
        description=description,
        scheduled_date=scheduled_date,
        start_time=start_time,
        end_time=end_time,
        session_type=session_type,
        max_participants=max_participants,
        is_recorded=is_recorded,
        created_by=user
    )
    
    # Create Zoom meeting if configured
    if zoom_configured:
        try:
            create_zoom_meeting_for_session(session)
        except Exception as e:
            print(f"Failed to create Zoom meeting for session {session.id}: {e}")
    
    return session


def create_recurring_sessions(request, batch, recurring_type, title, description, 
                            scheduled_date, start_time, end_time, session_type, 
                            max_participants, is_recorded, zoom_configured):
    """Create multiple sessions based on recurring type"""
    
    # Get recurring-specific data
    recurring_end_date_str = request.POST.get('recurring_end_date')
    if not recurring_end_date_str:
        raise ValueError("End date is required for recurring sessions")
    
    recurring_end_date = datetime.strptime(recurring_end_date_str, '%Y-%m-%d').date()
    
    if recurring_end_date <= scheduled_date:
        raise ValueError("End date must be after start date")
    
    # Generate session dates based on type
    session_dates = []
    
    if recurring_type == 'daily':
        current_date = scheduled_date
        while current_date <= recurring_end_date:
            session_dates.append(current_date)
            current_date += timedelta(days=1)
    
    elif recurring_type == 'weekly':
        weekly_days = request.POST.getlist('weekly_days')
        if not weekly_days:
            raise ValueError("Please select at least one day for weekly sessions")
        
        weekly_days = [int(d) for d in weekly_days]  # Convert to integers
        current_date = scheduled_date
        
        while current_date <= recurring_end_date:
            # Monday is 1, Sunday is 7 in our system
            # Python weekday(): Monday is 0, Sunday is 6
            current_weekday = current_date.weekday() + 1  # Convert to our system
            
            if current_weekday in weekly_days:
                session_dates.append(current_date)
            
            current_date += timedelta(days=1)
    
    elif recurring_type == 'custom':
        # For now, just add the initial date
        # Can be extended later for custom date selection
        session_dates.append(scheduled_date)
    
    if not session_dates:
        raise ValueError("No valid session dates generated")
    
    # Create sessions
    sessions_created = 0
    parent_session = None
    recurring_days_str = ','.join(request.POST.getlist('weekly_days')) if recurring_type == 'weekly' else ''
    
    for i, session_date in enumerate(session_dates):
        # Create session title
        if len(session_dates) > 1:
            session_title = f"{title} - Session {i+1}"
        else:
            session_title = title
        
        session = BatchSession.objects.create(
            batch=batch,
            title=session_title,
            description=description,
            scheduled_date=session_date,
            start_time=start_time,
            end_time=end_time,
            session_type=session_type,
            max_participants=max_participants,
            is_recorded=is_recorded,
            is_recurring=True,
            recurring_type=recurring_type,
            recurring_end_date=recurring_end_date,
            recurring_days=recurring_days_str,
            parent_session=parent_session,
            session_sequence=i + 1,
            created_by=request.user
        )
        
        # Set first session as parent
        if i == 0:
            parent_session = session
            # Don't set parent_session on the first session itself
        
        # Create Zoom meeting if configured
        if zoom_configured:
            try:
                create_zoom_meeting_for_session(session)
            except Exception as e:
                print(f"Failed to create Zoom meeting for session {session.id}: {e}")
        
        sessions_created += 1
    
    return sessions_created


@login_required
def session_list(request):
    """List all sessions with filtering and pagination"""
    sessions = BatchSession.objects.select_related('batch', 'batch__course', 'created_by')
    
    # Filter based on user role
    if request.user.role == 'instructor':
        sessions = sessions.filter(batch__instructor=request.user)
    elif request.user.role == 'student':
        # Show sessions for batches the student is enrolled in
        enrolled_batches = BatchEnrollment.objects.filter(
            student=request.user, 
            is_active=True
        ).values_list('batch_id', flat=True)
        sessions = sessions.filter(batch_id__in=enrolled_batches)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    # Filter by batch
    batch_filter = request.GET.get('batch')
    if batch_filter:
        sessions = sessions.filter(batch_id=batch_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        sessions = sessions.filter(scheduled_date__gte=date_from)
    if date_to:
        sessions = sessions.filter(scheduled_date__lte=date_to)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        sessions = sessions.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(batch__name__icontains=search_query)
        )
    
    sessions = sessions.order_by('-scheduled_date', '-start_time')
    
    # Get batches for filter dropdown
    if request.user.role == 'instructor':
        filter_batches = Batch.objects.filter(instructor=request.user, status='active')
    elif request.user.role == 'student':
        enrolled_batches = BatchEnrollment.objects.filter(
            student=request.user, is_active=True
        ).values_list('batch_id', flat=True)
        filter_batches = Batch.objects.filter(id__in=enrolled_batches)
    else:
        filter_batches = Batch.objects.filter(status='active')
    
    context = {
        'sessions': sessions,
        'filter_batches': filter_batches,
        'status_choices': BatchSession.STATUS_CHOICES,
        'current_filters': {
            'status': status_filter,
            'batch': int(batch_filter) if batch_filter else None,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'zoom/session_list.html', context)


# zoom/views.py

# zoom/views.py

@login_required
def session_detail(request, session_id):
    """Session detail - ONLY batch lock matters for sessions"""
    session = get_object_or_404(
        BatchSession.objects.select_related(
            'batch', 'batch__course', 'batch__instructor', 'created_by'
        ),
        id=session_id
    )
    
    # Permission check
    if not session.can_join_meeting(request.user) and request.user.role != 'superadmin':
        messages.error(request, 'You do not have permission to view this session.')
        return redirect('zoom:session_list')
    
    # Get all batch enrollments
    all_enrollments = BatchEnrollment.objects.filter(
        batch=session.batch
    ).select_related('student').order_by('student__first_name', 'student__last_name')
    
    # Filter based on BATCH lock ONLY (ignore course lock)
    active_enrollments = []
    locked_students_info = []
    
    for enrollment in all_enrollments:
        student = enrollment.student
        is_batch_locked = False
        lock_reason = None
        
        # Check 1: Enrollment inactive
        if not enrollment.is_active:
            is_batch_locked = True
            lock_reason = 'Enrollment Deactivated'
        
        # Check 2: ONLY batch-specific lock (NOT course lock)
        elif enrollment.is_locked:
            is_batch_locked = True
            reason = enrollment.get_lock_reason()
            if reason == 'payment':
                lock_reason = 'Batch Locked - Payment Issue'
            elif reason == 'admin':
                lock_reason = 'Batch Locked by Admin'
            else:
                lock_reason = 'Batch Access Locked'
        
        # Categorize student
        if is_batch_locked:
            locked_students_info.append({
                'student': student,
                'enrollment': enrollment,
                'lock_reason': lock_reason
            })
        else:
            # Student can access session (even if course is locked)
            active_enrollments.append(enrollment)
    
    # Get attendance records
    attendance_records = SessionAttendance.objects.filter(
        session=session
    ).select_related('student')
    
    attendance_map = {record.student_id: record for record in attendance_records}
    
    # Prepare attendance list for ACTIVE students
    student_attendance = []
    present_count = 0
    absent_count = 0
    
    for enrollment in active_enrollments:
        student = enrollment.student
        attendance = attendance_map.get(student.id)
        
        if attendance and attendance.is_present:
            status = 'present'
            join_time = attendance.joined_at
            leave_time = attendance.left_at
            duration = attendance.duration_minutes
            present_count += 1
        else:
            status = 'absent'
            join_time = None
            leave_time = None
            duration = 0
            absent_count += 1
        
        student_attendance.append({
            'student': student,
            'enrollment': enrollment,
            'status': status,
            'join_time': join_time,
            'leave_time': leave_time,
            'duration': duration,
            'attendance_record': attendance
        })
    
    # Calculate statistics
    total_students = len(active_enrollments)
    total_locked = len(locked_students_info)
    attendance_percentage = round((present_count / total_students * 100), 1) if total_students > 0 else 0
    
    context = {
        'session': session,
        'student_attendance': student_attendance,
        'locked_students_info': locked_students_info,
        'total_students': total_students,
        'total_locked': total_locked,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_percentage': attendance_percentage,
        'can_start': session.can_start_meeting(request.user),
        'can_join': session.can_join_meeting(request.user),
    }
    
    return render(request, 'zoom/session_detail.html', context)


@login_required
def delete_session(request, session_id):
    """Delete a session"""
    session = get_object_or_404(BatchSession, id=session_id)
    
    # Permission check
    if request.user.role == 'instructor' and session.batch.instructor != request.user:
        messages.error(request, 'You can only delete sessions for your own batches.')
        return redirect('zoom:session_list')
    elif request.user.role not in ['instructor', 'superadmin']:
        messages.error(request, 'You do not have permission to delete sessions.')
        return redirect('zoom:session_list')
    
    if request.method == 'POST':
        try:
            # Delete from Zoom if meeting exists
            if session.zoom_meeting_id:
                try:
                    delete_zoom_meeting(session.zoom_meeting_id)
                except Exception as e:
                    print(f"Failed to delete Zoom meeting: {e}")
            
            session_title = session.title
            session.delete()
            messages.success(request, f'Session "{session_title}" deleted successfully!')
        
        except Exception as e:
            messages.error(request, f'Error deleting session: {str(e)}')
    
    return redirect('zoom:session_list')


# Add these methods to your BatchSession model
def can_start_meeting(self, user):
    """Check if user can start the meeting"""
    if user.role not in ['instructor', 'admin']:
        return False
    
    if user.role == 'instructor' and self.batch.instructor != user:
        return False
        
    return self.status in ['UPCOMING', 'LIVE'] and self.zoom_meeting_id
    
def can_join_meeting(self, user):
    """Check if user can join the meeting"""
    if self.status != 'LIVE':
        return False
        
    if not self.zoom_join_url:
        return False
        
    # Check if user is enrolled in the batch
    if user.role == 'student':
        return self.batch.students.filter(id=user.id).exists()
    elif user.role == 'instructor':
        return self.batch.instructor == user
    elif user.role == 'admin':
        return True
        
    return False

@login_required
def zoom_dashboard(request):
    """Zoom Management Dashboard"""
    
    # Get statistics
    today = timezone.now().date()
    total_sessions = BatchSession.objects.count()
    today_sessions = BatchSession.objects.filter(scheduled_date=today).count()
    live_sessions = BatchSession.objects.filter(status='live').count()
    total_recordings = ZoomRecording.objects.count()
    
    # Recent sessions
    recent_sessions = BatchSession.objects.select_related('batch', 'created_by')[:10]
    
    # Upcoming sessions
    upcoming_sessions = BatchSession.objects.filter(
        scheduled_date__gte=today,
        status='scheduled'
    ).select_related('batch')[:5]
    
    context = {
        'total_sessions': total_sessions,
        'today_sessions': today_sessions,
        'live_sessions': live_sessions,
        'total_recordings': total_recordings,
        'recent_sessions': recent_sessions,
        'upcoming_sessions': upcoming_sessions,
    }
    
    return render(request, 'zoom/dashboard.html', context)





# zoom/views.py mein add karo:
@login_required
def test_zoom_config(request):
    """Test Zoom configuration"""
    try:
        from .services import ZoomAPIService
        service = ZoomAPIService()
        success, message = service.test_connection()
        
        if success:
            messages.success(request, f"Zoom test successful: {message}")
        else:
            messages.error(request, f"Zoom test failed: {message}")
            
    except Exception as e:
        messages.error(request, f"Zoom test error: {str(e)}")
    
    return redirect('zoom:create_session')


@login_required
def start_meeting(request, session_id):
    """Start Zoom meeting"""
    session = get_object_or_404(BatchSession, id=session_id)
    
    if not session.can_start_meeting(request.user):
        messages.error(request, 'You do not have permission to start this meeting.')
        return redirect('zoom:session_detail', session_id=session.id)
    
    if session.zoom_start_url:
        # Update session status
        session.status = 'live'
        session.save()
        
        messages.success(request, 'Meeting started! You will be redirected to Zoom.')
        return redirect(session.zoom_start_url)
    else:
        messages.error(request, 'Zoom meeting not configured for this session.')
        return redirect('zoom:session_detail', session_id=session.id)

@login_required
def join_meeting(request, session_id):
    """Join Zoom meeting as student"""
    session = get_object_or_404(BatchSession, id=session_id)
    
    if session.zoom_join_url:
        # Create attendance record
        attendance, created = SessionAttendance.objects.get_or_create(
            session=session,
            student=request.user,
            defaults={
                'joined_at': timezone.now(),
                'zoom_user_name': request.user.get_full_name()
            }
        )
        
        if not created and not attendance.joined_at:
            attendance.joined_at = timezone.now()
            attendance.save()
        
        return redirect(session.zoom_join_url)
    else:
        messages.error(request, 'Meeting link not available.')
        return redirect('zoom:session_detail', session_id=session.id)

@login_required
def recording_list(request):
    """List all recordings"""
    recordings = ZoomRecording.objects.select_related('session__batch').order_by('-recording_start')
    
    # Filter by batch
    batch_id = request.GET.get('batch')
    if batch_id:
        recordings = recordings.filter(session__batch_id=batch_id)
    
    batches = Batch.objects.filter(status='active')
    
    context = {
        'recordings': recordings,
        'batches': batches,
        'selected_batch': batch_id,
    }
    
    return render(request, 'zoom/recording_list.html', context)

@login_required
def play_recording(request, recording_id):
    """Play recording"""
    recording = get_object_or_404(ZoomRecording, id=recording_id)
    
    # Increment view count
    recording.increment_view_count()
    
    # Check if user has access
    if request.user.role == 'student':
        # Check if student is enrolled in the batch
        enrolled = recording.session.batch.enrollments.filter(
            student=request.user,
            is_active=True
        ).exists()
        
        if not enrolled:
            messages.error(request, 'You are not enrolled in this batch.')
            return redirect('zoom:recording_list')
    
    if recording.play_url:
        return redirect(recording.play_url)
    elif recording.download_url:
        return redirect(recording.download_url)
    else:
        messages.error(request, 'Recording not available.')
        return redirect('zoom:recording_list')

@csrf_exempt
def zoom_webhook(request):
    """Handle Zoom webhooks"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event_type = data.get('event')
            
            # Log webhook
            ZoomWebhookLog.objects.create(
                event_type=event_type,
                zoom_meeting_id=data.get('payload', {}).get('object', {}).get('id', ''),
                event_data=data
            )
            
            # Process specific events
            if event_type == 'meeting.started':
                handle_meeting_started(data)
            elif event_type == 'meeting.ended':
                handle_meeting_ended(data)
            elif event_type == 'meeting.participant_joined':
                handle_participant_joined(data)
            elif event_type == 'meeting.participant_left':
                handle_participant_left(data)
            elif event_type == 'recording.completed':
                handle_recording_completed(data)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'invalid method'})

def handle_meeting_started(data):
    """Handle meeting started webhook"""
    meeting_id = data['payload']['object']['id']
    try:
        session = BatchSession.objects.get(zoom_meeting_id=meeting_id)
        session.status = 'live'
        session.save()
    except BatchSession.DoesNotExist:
        pass

def handle_meeting_ended(data):
    """Handle meeting ended webhook"""
    meeting_id = str(data['payload']['object']['id'])  # Ensure string
    try:
        session = BatchSession.objects.get(zoom_meeting_id=meeting_id)
        session.status = 'completed'  # Make sure this matches your STATUS_CHOICES
        session.save()
        
        print(f"Session {session.id} marked as completed via webhook")
        
        # Try to fetch recordings
        try:
            from .services import ZoomAPIService
            service = ZoomAPIService()
            service.get_meeting_recordings(meeting_id)
        except Exception as e:
            print(f"Recording fetch failed: {e}")
            
    except BatchSession.DoesNotExist:
        print(f"Session with meeting_id {meeting_id} not found")
    except Exception as e:
        print(f"Error in handle_meeting_ended: {e}")

@login_required
def end_session(request, session_id):
    """Manually end session and mark as completed"""
    session = get_object_or_404(BatchSession, id=session_id)
    
    # Permission check
    if request.user.role == 'instructor' and session.batch.instructor != request.user:
        messages.error(request, 'You can only end your own sessions.')
        return redirect('zoom:session_list')
    
    if request.method == 'POST':
        session.status = 'completed'
        session.save()
        messages.success(request, f'Session "{session.title}" marked as completed!')
        return redirect('zoom:session_detail', session_id=session.id)
    
    # GET request - show confirmation
    context = {'session': session}
    return render(request, 'zoom/confirm_end_session.html', context)

def handle_participant_joined(data):
    """Handle participant joined webhook"""
    # Implementation for tracking participant join
    pass

def handle_participant_left(data):
    """Handle participant left webhook"""
    # Implementation for tracking participant leave
    pass

def handle_recording_completed(data):
    """Handle recording completed webhook"""
    meeting_id = data['payload']['object']['id']
    try:
        session = BatchSession.objects.get(zoom_meeting_id=meeting_id)
        zoom_service = ZoomAPIService()
        zoom_service.get_meeting_recordings(session)
    except:
        pass




# zoom/views.py - Add these views for Zoom Configuration Setup

@login_required
def zoom_config_setup(request):
    """Setup Zoom Configuration - Only for superadmin"""
    
    # Check if user is superadmin
    if request.user.role != 'superadmin':
        messages.error(request, 'Only super admin can configure Zoom settings.')
        return redirect('zoom:dashboard')
    
    # Get existing configuration or create new
    config = ZoomConfiguration.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        try:
            # Get form data
            organization_name = request.POST.get('organization_name', '').strip()
            admin_email = request.POST.get('admin_email', '').strip()
            account_id = request.POST.get('account_id', '').strip()
            client_id = request.POST.get('client_id', '').strip()
            client_secret = request.POST.get('client_secret', '').strip()
            secret_token = request.POST.get('secret_token', '').strip()
            
            # Validate required fields
            if not all([organization_name, admin_email, account_id, client_id, client_secret]):
                messages.error(request, 'Please fill all required fields.')
                return render(request, 'zoom/config_setup.html', {
                    'config': config,
                    'form_data': request.POST
                })
            
            # Validate email format
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(admin_email)
            except ValidationError:
                messages.error(request, 'Please enter a valid email address.')
                return render(request, 'zoom/config_setup.html', {
                    'config': config,
                    'form_data': request.POST
                })
            
            # Update existing or create new configuration
            if config:
                # Update existing
                config.organization_name = organization_name
                config.admin_email = admin_email
                config.account_id = account_id
                config.client_id = client_id
                config.client_secret = client_secret
                config.secret_token = secret_token
                
                # Update meeting settings
                config.default_host_video = request.POST.get('default_host_video') == 'on'
                config.default_participant_video = request.POST.get('default_participant_video') == 'on'
                config.default_join_before_host = request.POST.get('default_join_before_host') == 'on'
                config.default_mute_upon_entry = request.POST.get('default_mute_upon_entry') == 'on'
                config.default_waiting_room = request.POST.get('default_waiting_room') == 'on'
                config.default_auto_recording = request.POST.get('default_auto_recording', 'cloud')
                
                config.save()
                action = "updated"
            else:
                # Create new
                config = ZoomConfiguration.objects.create(
                    organization_name=organization_name,
                    admin_email=admin_email,
                    account_id=account_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    secret_token=secret_token,
                    default_host_video=request.POST.get('default_host_video') == 'on',
                    default_participant_video=request.POST.get('default_participant_video') == 'on',
                    default_join_before_host=request.POST.get('default_join_before_host') == 'on',
                    default_mute_upon_entry=request.POST.get('default_mute_upon_entry') == 'on',
                    default_waiting_room=request.POST.get('default_waiting_room') == 'on',
                    default_auto_recording=request.POST.get('default_auto_recording', 'cloud'),
                    created_by=request.user,
                    is_active=True
                )
                action = "created"
            
            # Test connection automatically
            if request.POST.get('test_connection') == 'on':
                success, message = config.test_connection()
                if success:
                    messages.success(request, f'Configuration {action} successfully! Connection test passed: {message}')
                else:
                    messages.warning(request, f'Configuration {action} but connection test failed: {message}')
            else:
                messages.success(request, f'Configuration {action} successfully!')
            
            return redirect('zoom:config_setup')
            
        except Exception as e:
            messages.error(request, f'Error saving configuration: {str(e)}')
            import logging
            logger = logging.getLogger(__name__)
            logger.exception('Zoom config setup error')
    
    context = {
        'config': config,
        'recording_choices': [
            ('none', 'No Recording'),
            ('local', 'Local Recording'),
            ('cloud', 'Cloud Recording (Recommended)'),
        ]
    }
    
    return render(request, 'zoom/config_setup.html', context)


@login_required
def test_zoom_connection(request):
    """AJAX endpoint to test Zoom connection"""
    
    if request.user.role != 'superadmin':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            config = ZoomConfiguration.get_active_config()
            if not config:
                return JsonResponse({
                    'success': False, 
                    'message': 'No active configuration found'
                })
            
            success, message = config.test_connection()
            
            return JsonResponse({
                'success': success,
                'message': message,
                'test_status': config.test_status,
                'last_test': config.last_test_date.strftime('%Y-%m-%d %H:%M:%S') if config.last_test_date else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Test failed: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required  
def zoom_config_status_page(request):
    """Show Zoom configuration status page"""
    
    configs = ZoomConfiguration.objects.all().order_by('-created_at')
    active_config = ZoomConfiguration.get_active_config()
    
    context = {
        'configs': configs,
        'active_config': active_config,
        'has_config': configs.exists(),
        'is_superadmin': request.user.role == 'superadmin'
    }
    
    return render(request, 'zoom/config_status.html', context)



# Add these missing views to your zoom/views.py file

@login_required
def get_batch_details(request, batch_id):
    """Get batch details for AJAX requests"""
    try:
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Check permission
        if request.user.role == 'instructor' and batch.instructor != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = {
            'id': batch.id,
            'name': batch.name,
            'course_title': batch.course.title,
            'instructor_name': batch.instructor.get_full_name(),
            'max_students': batch.max_students,
            'enrolled_count': batch.get_enrolled_count(),
            'start_date': batch.start_date.strftime('%Y-%m-%d') if batch.start_date else '',
            'end_date': batch.end_date.strftime('%Y-%m-%d') if batch.end_date else '',
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)





# zoom/views.py - Student Views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from datetime import date, timedelta
from courses.models import Batch, BatchEnrollment

@login_required
def student_sessions_browse(request):
    """Browse all available sessions for enrolled batches - Student View"""
    
    if request.user.role != 'student':
        messages.error(request, 'This page is only accessible to students.')
        return redirect('zoom:dashboard')
    
    # Get student's enrolled batches
    enrolled_batches = BatchEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).values_list('batch_id', flat=True)
    
    # Get sessions from enrolled batches
    sessions = BatchSession.objects.filter(
        batch_id__in=enrolled_batches
    ).select_related('batch', 'batch__course', 'created_by')
    
    # Filters
    status_filter = request.GET.get('status', '')
    batch_filter = request.GET.get('batch', '')
    date_filter = request.GET.get('date', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    if batch_filter:
        sessions = sessions.filter(batch_id=batch_filter)
    
    if date_filter == 'today':
        sessions = sessions.filter(scheduled_date=date.today())
    elif date_filter == 'week':
        week_end = date.today() + timedelta(days=7)
        sessions = sessions.filter(scheduled_date__range=[date.today(), week_end])
    elif date_filter == 'month':
        month_end = date.today() + timedelta(days=30)
        sessions = sessions.filter(scheduled_date__range=[date.today(), month_end])
    
    if search:
        sessions = sessions.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(batch__name__icontains=search)
        )
    
    # Separate by status
    upcoming_sessions = sessions.filter(
        status='scheduled',
        scheduled_date__gte=date.today()
    ).order_by('scheduled_date', 'start_time')[:6]
    
    live_sessions = sessions.filter(status='live')
    
    completed_sessions = sessions.filter(
        status='completed'
    ).order_by('-scheduled_date')[:6]
    
    # Get batches for filter
    student_batches = Batch.objects.filter(id__in=enrolled_batches)
    
    # Stats
    total_sessions = sessions.count()
    attended_sessions = SessionAttendance.objects.filter(
        student=request.user,
        session__in=sessions
    ).count()
    
    context = {
        'upcoming_sessions': upcoming_sessions,
        'live_sessions': live_sessions,
        'completed_sessions': completed_sessions,
        'student_batches': student_batches,
        'total_sessions': total_sessions,
        'attended_sessions': attended_sessions,
        'status_filter': status_filter,
        'batch_filter': batch_filter,
        'date_filter': date_filter,
        'search': search,
    }
    
    return render(request, 'zoom/student_sessions_browse.html', context)


@login_required
def student_session_detail(request, session_id):
    """Session detail view for students"""
    
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('zoom:dashboard')
    
    session = get_object_or_404(
        BatchSession.objects.select_related('batch', 'batch__course'),
        id=session_id
    )
    
    # Check if student is enrolled
    is_enrolled = BatchEnrollment.objects.filter(
        student=request.user,
        batch=session.batch,
        is_active=True
    ).exists()
    
    if not is_enrolled:
        messages.error(request, 'You are not enrolled in this batch.')
        return redirect('student_sessions_browse')
    
    # Get attendance record
    attendance = SessionAttendance.objects.filter(
        session=session,
        student=request.user
    ).first()
    
    # Check if can join
    can_join = session.status == 'live' and session.zoom_join_url
    
    context = {
        'session': session,
        'attendance': attendance,
        'can_join': can_join,
        'is_live': session.status == 'live',
        'is_upcoming': session.status == 'scheduled',
        'is_completed': session.status == 'completed',
    }
    
    return render(request, 'zoom/student_session_detail.html', context)


@login_required
def student_recordings(request):
    """View recordings for enrolled courses"""
    
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('zoom:dashboard')
    
    # Get enrolled batches
    enrolled_batches = BatchEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).values_list('batch_id', flat=True)
    
    # Get recordings from those batches
    recordings = ZoomRecording.objects.filter(
        session__batch_id__in=enrolled_batches
    ).select_related('session', 'session__batch').order_by('-recording_start')
    
    # Filters
    batch_filter = request.GET.get('batch', '')
    if batch_filter:
        recordings = recordings.filter(session__batch_id=batch_filter)
    
    student_batches = Batch.objects.filter(id__in=enrolled_batches)
    
    context = {
        'recordings': recordings,
        'student_batches': student_batches,
        'batch_filter': batch_filter,
    }
    
    return render(request, 'zoom/student_recordings.html', context)


@login_required
def student_attendance_history(request):
    """Student's attendance history"""
    
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('zoom:dashboard')
    
    attendance_records = SessionAttendance.objects.filter(
        student=request.user
    ).select_related('session', 'session__batch').order_by('-session__scheduled_date')
    
    # Stats
    total_attended = attendance_records.count()
    
    enrolled_batches = BatchEnrollment.objects.filter(
        student=request.user,
        is_active=True
    ).values_list('batch_id', flat=True)
    
    total_sessions = BatchSession.objects.filter(
        batch_id__in=enrolled_batches,
        status='completed'
    ).count()
    
    attendance_percentage = (total_attended / total_sessions * 100) if total_sessions > 0 else 0
    
    context = {
        'attendance_records': attendance_records,
        'total_attended': total_attended,
        'total_sessions': total_sessions,
        'attendance_percentage': round(attendance_percentage, 1),
    }
    
    return render(request, 'zoom/student_attendance.html', context)