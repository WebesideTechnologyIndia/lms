# webinars/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Webinar, WebinarRegistration, WebinarCategory, WebinarFeedback
from .forms import WebinarRegistrationForm, WebinarForm, WebinarFeedbackForm
import json

User = get_user_model()

# ==================== PUBLIC VIEWS ====================
def webinar_landing(request):
    """Public landing page for webinars"""
    
    # Get upcoming webinars
    upcoming_webinars = Webinar.objects.filter(
        status='upcoming',
        is_active=True,
        scheduled_date__gt=timezone.now()
    ).order_by('scheduled_date')[:6]
    
    # Get featured/recent webinars
    featured_webinars = Webinar.objects.filter(
        is_active=True,
        status__in=['upcoming', 'completed']
    ).order_by('-created_at')[:4]
    
    # Get categories
    categories = WebinarCategory.objects.filter(is_active=True)
    
    # Get stats
    stats = {
        'total_webinars': Webinar.objects.filter(is_active=True).count(),
        'total_attendees': WebinarRegistration.objects.filter(is_active=True).count(),
        'upcoming_webinars': upcoming_webinars.count(),
        'free_webinars': Webinar.objects.filter(webinar_type='free', is_active=True).count(),
    }
    
    # Check if user is logged in and show personalized content
    user_registrations = []
    if request.user.is_authenticated:
        # Get user's registered webinars
        user_registrations = WebinarRegistration.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('webinar')[:3]
    
    context = {
        'upcoming_webinars': upcoming_webinars,
        'featured_webinars': featured_webinars,
        'categories': categories,
        'stats': stats,
        'user_registrations': user_registrations,  # Add user's registrations
    }
    
    return render(request, 'webinars/landing.html', context)


def webinar_list(request):
    """List all webinars with filtering"""
    
    webinars = Webinar.objects.filter(is_active=True)
    
    # Filters
    webinar_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if webinar_type:
        webinars = webinars.filter(webinar_type=webinar_type)
    
    if category_id:
        webinars = webinars.filter(category_id=category_id)
    
    if search:
        webinars = webinars.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(instructor__first_name__icontains=search) |
            Q(instructor__last_name__icontains=search)
        )
    
    if status:
        webinars = webinars.filter(status=status)
    
    # Default ordering
    webinars = webinars.order_by('scheduled_date')
    
    # Pagination
    paginator = Paginator(webinars, 12)
    page = request.GET.get('page')
    webinars = paginator.get_page(page)
    
    # Get categories for filter
    categories = WebinarCategory.objects.filter(is_active=True)
    
    context = {
        'webinars': webinars,
        'categories': categories,
        'current_filters': {
            'type': webinar_type,
            'category': category_id,
            'search': search,
            'status': status,
        }
    }
    
    return render(request, 'webinars/webinar_list.html', context)


def webinar_detail(request, slug):
    """Webinar detail page with registration"""
    
    webinar = get_object_or_404(Webinar, slug=slug, is_active=True)
    
    # Check if user is already registered
    user_registration = None
    if request.user.is_authenticated:
        user_registration = WebinarRegistration.objects.filter(
            webinar=webinar,
            user=request.user,
            is_active=True
        ).first()
    
    # Get related webinars
    related_webinars = Webinar.objects.filter(
        category=webinar.category,
        is_active=True
    ).exclude(id=webinar.id)[:3]
    
    context = {
        'webinar': webinar,
        'user_registration': user_registration,
        'related_webinars': related_webinars,
        'can_register': webinar.is_registration_open(),
    }
    
    return render(request, 'webinars/webinar_detail.html', context)

# webinars/views.py - YE VIEWS ADD/UPDATE KARO

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Webinar, WebinarRegistration
from .forms import WebinarRegistrationForm



def registration_success(request, registration_id):
    """Registration success page with payment status"""
    
    registration = get_object_or_404(WebinarRegistration, id=registration_id)
    
    context = {
        'registration': registration,
        'webinar': registration.webinar,
        'needs_payment': registration.is_payment_required(),
    }
    
    return render(request, 'webinars/registration_success.html', context)



# webinars/views.py - YE VIEWS UPDATE KARO

def webinar_register(request, slug):
    """Register for webinar with correct user role logic"""
    
    webinar = get_object_or_404(Webinar, slug=slug, is_active=True)
    
    if not webinar.is_registration_open():
        messages.error(request, 'Registration is closed for this webinar.')
        return redirect('webinars:webinar_detail', slug=slug)
    
    if request.method == 'POST':
        form = WebinarRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Check if email is already registered
                if WebinarRegistration.objects.filter(
                    webinar=webinar,
                    email=form.cleaned_data['email'],
                    is_active=True
                ).exists():
                    messages.error(request, 'This email is already registered for this webinar.')
                    return redirect('webinars:webinar_detail', slug=slug)
                
                # Create registration
                registration = WebinarRegistration.create_registration(
                    webinar=webinar,
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    company=form.cleaned_data.get('company', ''),
                    designation=form.cleaned_data.get('designation', ''),
                )
                
                # Update webinar stats
                webinar.total_registrations = webinar.get_registration_count()
                webinar.save(update_fields=['total_registrations'])
                
                # Show appropriate message based on webinar type
                if webinar.webinar_type == 'free':
                    messages.success(request, 
                        f'Successfully registered for FREE webinar: {webinar.title}! '
                        f'You now have Student access. Check your email for webinar details.'
                    )
                else:
                    messages.info(request, 
                        f'Registration created for PAID webinar: {webinar.title} (₹{webinar.price}). '
                        f'Complete payment to upgrade to Webinar User and confirm registration.'
                    )
                
                return redirect('webinars:registration_success', registration_id=registration.id)
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                return redirect('webinars:webinar_detail', slug=slug)
    else:
        # Pre-fill form if user is logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
        form = WebinarRegistrationForm(initial=initial_data)
    
    context = {
        'webinar': webinar,
        'form': form,
    }
    
    return render(request, 'webinars/register.html', context)


def confirm_payment(request, registration_id):
    """Student confirms their payment for PAID webinar"""
    
    registration = get_object_or_404(WebinarRegistration, id=registration_id)
    
    # Check access
    if request.user.is_authenticated:
        is_owner = registration.user == request.user
        is_admin = request.user.role in ['superadmin', 'instructor']
        
        if not (is_owner or is_admin):
            messages.error(request, 'Access denied.')
            return redirect('webinars:webinar_list')
    else:
        # Allow non-logged in users to confirm payment using email verification
        email_from_session = request.session.get('registration_email')
        if email_from_session != registration.email:
            messages.error(request, 'Please login or verify your email to confirm payment.')
            return redirect('login')
    
    if registration.payment_status == 'paid':
        messages.info(request, 'Payment already confirmed.')
        return redirect('webinars:registration_success', registration_id=registration_id)
    
    if request.method == 'POST':
        # Confirm payment
        user_upgraded = registration.confirm_payment()
        
        if user_upgraded:
            messages.success(request, 
                'Payment confirmed! Your account has been upgraded to Webinar User. '
                'You now have access to premium webinar features.'
            )
        else:
            messages.success(request, 'Payment confirmed successfully!')
        
        return redirect('webinars:registration_success', registration_id=registration_id)
    
    context = {
        'registration': registration,
        'webinar': registration.webinar,
    }
    
    return render(request, 'webinars/confirm_payment.html', context)


@login_required
def admin_mark_payment(request, registration_id):
    """Admin marks registration payment as completed"""
    
    # Only admin/instructor can access
    if request.user.role not in ['superadmin', 'instructor']:
        messages.error(request, 'Access denied.')
        return redirect('webinars:webinar_list')
    
    registration = get_object_or_404(WebinarRegistration, id=registration_id)
    
    if request.method == 'POST':
        user_upgraded = registration.confirm_payment()
        
        if user_upgraded:
            messages.success(request, 
                f'Payment marked as completed for {registration.get_full_name()}. '
                f'User upgraded from Student to Webinar User (Premium).'
            )
        else:
            messages.success(request, 
                f'Payment marked as completed for {registration.get_full_name()}.'
            )
        
        # Redirect back to admin registrations page
        return redirect('webinars:admin_all_registrations')
    
    context = {
        'registration': registration,
        'webinar': registration.webinar,
    }
    
    return render(request, 'webinars/admin_mark_payment.html', context)



# ==================== ADMIN VIEWS ====================
# done
@login_required
def admin_webinar_dashboard(request):
    """Admin dashboard for webinars"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    # Get stats
    total_webinars = Webinar.objects.filter(is_active=True).count()
    upcoming_webinars = Webinar.objects.filter(
        status='upcoming',
        scheduled_date__gt=timezone.now()
    ).count()
    total_registrations = WebinarRegistration.objects.filter(is_active=True).count()
    completed_webinars = Webinar.objects.filter(status='completed').count()
    
    # Get recent webinars
    recent_webinars = Webinar.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # Get recent registrations
    recent_registrations = WebinarRegistration.objects.filter(
        is_active=True
    ).select_related('webinar', 'user').order_by('-registered_at')[:10]
    
    context = {
        'total_webinars': total_webinars,
        'upcoming_webinars': upcoming_webinars,
        'total_registrations': total_registrations,
        'completed_webinars': completed_webinars,
        'recent_webinars': recent_webinars,
        'recent_registrations': recent_registrations,
    }
    
    return render(request, 'webinars/admin/dashboard.html', context)


@login_required
def admin_manage_webinars(request):
    """Manage all webinars"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    webinars = Webinar.objects.filter(is_active=True)
    
    # Filter by instructor role
    if request.user.role == 'instructor':
        webinars = webinars.filter(instructor=request.user)
    
    # Search and filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    webinar_type = request.GET.get('type', '')
    
    if search:
        webinars = webinars.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status:
        webinars = webinars.filter(status=status)
    
    if webinar_type:
        webinars = webinars.filter(webinar_type=webinar_type)
    
    # Add registration count
    webinars = webinars.annotate(
        registration_count=Count('registrations', filter=Q(registrations__is_active=True))
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(webinars, 15)
    page = request.GET.get('page')
    webinars = paginator.get_page(page)
    
    context = {
        'webinars': webinars,
        'search': search,
        'status': status,
        'webinar_type': webinar_type,
    }
    
    return render(request, 'webinars/admin/manage_webinars.html', context)


@login_required
def admin_create_webinar(request):
    """Create new webinar"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    if request.method == 'POST':
        form = WebinarForm(request.POST, request.FILES)
        
        # Debug: Print form data and errors
        print("=== FORM DEBUG ===")
        print("Form Data:", request.POST)
        print("Form Files:", request.FILES)
        print("Form is valid:", form.is_valid())
        
        if not form.is_valid():
            print("Form Errors:", form.errors)
            print("Non-field errors:", form.non_field_errors())
            for field, errors in form.errors.items():
                print(f"Field '{field}' errors: {errors}")
        
        if form.is_valid():
            webinar = form.save(commit=False)
            webinar.created_by = request.user
            
            # Set instructor for instructors
            if request.user.role == 'instructor':
                webinar.instructor = request.user
            
            try:
                webinar.save()
                messages.success(request, f'Webinar "{webinar.title}" created successfully!')
                return redirect('webinars:admin_manage_webinars')
            except Exception as e:
                print("Save Error:", str(e))
                messages.error(request, f'Error saving webinar: {str(e)}')
        else:
            # Add form errors to messages for display
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = WebinarForm()
        # Pre-fill instructor for instructor role
        if request.user.role == 'instructor':
            form.fields['instructor'].initial = request.user
    
    context = {
        'form': form,
        'title': 'Create New Webinar',
    }
    
    return render(request, 'webinars/admin/webinar_form.html', context)


@login_required
def admin_edit_webinar(request, webinar_id):
    """Edit webinar"""
    
    webinar = get_object_or_404(Webinar, id=webinar_id)
    
    # Check permissions
    if request.user.role == 'instructor' and webinar.instructor != request.user:
        messages.error(request, "You can only edit your own webinars!")
        return redirect('webinars:admin_manage_webinars')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    if request.method == 'POST':
        form = WebinarForm(request.POST, request.FILES, instance=webinar)
        if form.is_valid():
            webinar = form.save()
            messages.success(request, f'Webinar "{webinar.title}" updated successfully!')
            return redirect('webinars:admin_manage_webinars')
    else:
        form = WebinarForm(instance=webinar)
    
    context = {
        'form': form,
        'webinar': webinar,
        'title': f'Edit: {webinar.title}',
    }
    
    return render(request, 'webinars/admin/webinar_form.html', context)


@login_required
def admin_webinar_registrations(request, webinar_id):
    """View webinar registrations"""
    
    webinar = get_object_or_404(Webinar, id=webinar_id)
    
    # Check permissions
    if request.user.role == 'instructor' and webinar.instructor != request.user:
        messages.error(request, "Access denied!")
        return redirect('webinars:admin_manage_webinars')
    elif request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    registrations = webinar.registrations.filter(is_active=True).select_related('user')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.select_related('webinar', 'user').order_by('-registered_at')
    
    # Pagination
    paginator = Paginator(registrations, 25)
    page = request.GET.get('page')
    registrations = paginator.get_page(page)
    
    # Get webinars for filter
    if request.user.role == 'instructor':
        webinars = Webinar.objects.filter(instructor=request.user, is_active=True)
    else:
        webinars = Webinar.objects.filter(is_active=True)
    
    context = {
        'registrations': registrations,
        'webinars': webinars,
        'search': search,
        'webinar_id': webinar_id,
        
    }
    
    return render(request, 'webinars/admin/all_registrations.html', context)


# ==================== USER DASHBOARD VIEWS ====================

@login_required
def my_webinars(request):
    """User's registered webinars"""
    
    if request.user.role not in ['student', 'webinar_user']:
        return redirect('webinars:webinar_landing')
    
    # Get user's registrations
    registrations = request.user.webinar_registrations.filter(
        is_active=True
    ).select_related('webinar').order_by('-registered_at')
    
    # Separate upcoming and past webinars
    upcoming_registrations = []
    past_registrations = []
    
    for reg in registrations:
        if reg.webinar.scheduled_date > timezone.now():
            upcoming_registrations.append(reg)
        else:
            past_registrations.append(reg)
    
    context = {
        'upcoming_registrations': upcoming_registrations,
        'past_registrations': past_registrations,
    }
    
    return render(request, 'webinars/my_webinars.html', context)


@login_required 
def webinar_feedback(request, webinar_id):
    """Submit feedback for attended webinar"""
    
    webinar = get_object_or_404(Webinar, id=webinar_id)
    
    # Check if user attended the webinar
    registration = get_object_or_404(
        WebinarRegistration,
        webinar=webinar,
        user=request.user,
        is_active=True
    )
    
    # Check if webinar is completed
    if webinar.status != 'completed':
        messages.error(request, 'Feedback can only be submitted for completed webinars.')
        return redirect('webinars:my_webinars')
    
    # Check if feedback already exists
    existing_feedback = WebinarFeedback.objects.filter(
        webinar=webinar,
        attendee=request.user
    ).first()
    
    if request.method == 'POST':
        form = WebinarFeedbackForm(request.POST, instance=existing_feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.webinar = webinar
            feedback.attendee = request.user
            feedback.save()
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('webinars:my_webinars')
    else:
        form = WebinarFeedbackForm(instance=existing_feedback)
    
    context = {
        'webinar': webinar,
        'form': form,
        'is_edit': existing_feedback is not None,
    }
    
    return render(request, 'webinars/feedback.html', context)


# ==================== UTILITY VIEWS ====================

@csrf_exempt
@login_required
def update_registration_status(request, registration_id):
    """Update registration status (AJAX)"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        registration = get_object_or_404(WebinarRegistration, id=registration_id)
        
        # Check permissions
        if (request.user.role == 'instructor' and 
            registration.webinar.instructor != request.user):
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        # Validate status
        valid_statuses = [choice[0] for choice in WebinarRegistration.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        
        registration.status = new_status
        registration.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def webinar_analytics(request, webinar_id):
    """Webinar analytics for admin/instructor"""
    
    webinar = get_object_or_404(Webinar, id=webinar_id)
    
    # Check permissions
    if (request.user.role == 'instructor' and webinar.instructor != request.user) or \
       request.user.role not in ['superadmin', 'instructor']:
        messages.error(request, "Access denied!")
        return redirect('webinars:admin_manage_webinars')
    
    # Get registration stats
    registrations = webinar.registrations.filter(is_active=True)
    
    stats = {
        'total_registrations': registrations.count(),
        'attended': registrations.filter(status='attended').count(),
        'no_show': registrations.filter(status='no_show').count(),
        'cancelled': registrations.filter(status='cancelled').count(),
    }
    
    # Calculate rates
    if stats['total_registrations'] > 0:
        stats['attendance_rate'] = round(
            (stats['attended'] / stats['total_registrations']) * 100, 1
        )
        stats['no_show_rate'] = round(
            (stats['no_show'] / stats['total_registrations']) * 100, 1
        )
    else:
        stats['attendance_rate'] = 0
        stats['no_show_rate'] = 0
    
    # Get feedback stats
    feedback = webinar.feedback.all()
    
    if feedback.exists():
        avg_ratings = {
            'content': round(feedback.aggregate(
                avg=models.Avg('content_rating')
            )['avg'] or 0, 1),
            'instructor': round(feedback.aggregate(
                avg=models.Avg('instructor_rating')
            )['avg'] or 0, 1),
            'overall': round(feedback.aggregate(
                avg=models.Avg('overall_rating')
            )['avg'] or 0, 1),
        }
        recommendation_rate = round(
            (feedback.filter(would_recommend=True).count() / feedback.count()) * 100, 1
        )
    else:
        avg_ratings = {'content': 0, 'instructor': 0, 'overall': 0}
        recommendation_rate = 0
    
    # Registration timeline (last 30 days)
    from datetime import datetime, timedelta
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    registration_timeline = registrations.filter(
        registered_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('registered_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    context = {
        'webinar': webinar,
        'stats': stats,
        'avg_ratings': avg_ratings,
        'recommendation_rate': recommendation_rate,
        'total_feedback': feedback.count(),
        'registration_timeline': list(registration_timeline),
    }
    
    return render(request, 'webinars/admin/webinar_analytics.html', context)


def api_upcoming_webinars(request):
    """API endpoint for upcoming webinars"""
    
    webinars = Webinar.objects.filter(
        status='upcoming',
        is_active=True,
        scheduled_date__gt=timezone.now()
    ).order_by('scheduled_date')[:10]
    
    data = []
    for webinar in webinars:
        data.append({
            'id': webinar.id,
            'title': webinar.title,
            'scheduled_date': webinar.scheduled_date.isoformat(),
            'duration_minutes': webinar.duration_minutes,
            'webinar_type': webinar.webinar_type,
            'price': float(webinar.price),
            'available_spots': webinar.get_available_spots(),
            'instructor': webinar.instructor.get_full_name(),
            'url': webinar.get_absolute_url(),
        })
    
    return JsonResponse({'webinars': data})


# ==================== AUTOMATIC USER TYPE UPGRADE ====================

def upgrade_webinar_user_to_student(user):
    """
    Upgrade webinar_user to student when they enroll in paid course
    This function should be called from course enrollment process
    """
    if user.role == 'webinar_user':
        user.role = 'student'
        user.save(update_fields=['role'])
        
        # Log the upgrade
        from userss.models import UserActivityLog
        UserActivityLog.objects.create(
            user=user,
            action='role_upgraded',
            description=f'User role upgraded from webinar_user to student'
        )
        
        return True
    return False.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(company__icontains=search)
        )
    
    # Status filter
    status = request.GET.get('status', '')
    if status:
        registrations = registrations.filter(status=status)
    
    registrations = registrations.order_by('-registered_at')
    
    # Pagination
    paginator = Paginator(registrations, 20)
    page = request.GET.get('page')
    registrations = paginator.get_page(page)
    
    context = {
        'webinar': webinar,
        'registrations': registrations,
        'search': search,
        'status': status,
    }
    
    return render(request, 'webinars/admin/webinar_registrations.html', context)


# webinars/views.py - YE MISSING VIEWS ADD KARO

@login_required
def admin_delete_registration(request, registration_id):
    """Delete registration (Admin only)"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        registration = get_object_or_404(WebinarRegistration, id=registration_id)
        
        # Check permissions for instructor
        if (request.user.role == 'instructor' and 
            registration.webinar.instructor != request.user):
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        # Store info before deletion
        participant_name = registration.get_full_name()
        webinar_title = registration.webinar.title
        
        # Delete registration
        registration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Registration for {participant_name} deleted successfully from {webinar_title}'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required 
def admin_send_reminder(request, registration_id):
    """Send individual reminder email"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        registration = get_object_or_404(WebinarRegistration, id=registration_id)
        
        # Check permissions for instructor
        if (request.user.role == 'instructor' and 
            registration.webinar.instructor != request.user):
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        try:
            # Send reminder email
            send_webinar_reminder_email(registration)
            
            # Update reminder sent status
            registration.reminder_sent = True
            registration.reminder_sent_at = timezone.now()
            registration.save(update_fields=['reminder_sent', 'reminder_sent_at'])
            
            return JsonResponse({
                'success': True,
                'message': f'Reminder sent to {registration.email}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to send reminder: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def admin_bulk_update_status(request):
    """Bulk update registration status"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            registration_ids = data.get('registration_ids', [])
            new_status = data.get('status')
            
            if not registration_ids:
                return JsonResponse({'success': False, 'message': 'No registrations selected'})
            
            # Validate status
            valid_statuses = [choice[0] for choice in WebinarRegistration.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'message': 'Invalid status'})
            
            # Get registrations
            registrations = WebinarRegistration.objects.filter(id__in=registration_ids)
            
            # Filter by instructor permissions
            if request.user.role == 'instructor':
                registrations = registrations.filter(webinar__instructor=request.user)
            
            # Update status
            updated_count = registrations.update(status=new_status)
            
            return JsonResponse({
                'success': True,
                'message': f'Updated {updated_count} registrations to {new_status}',
                'count': updated_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def admin_bulk_send_reminders(request):
    """Send bulk reminder emails"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            registration_ids = data.get('registration_ids', [])
            
            if not registration_ids:
                return JsonResponse({'success': False, 'message': 'No registrations selected'})
            
            # Get registrations
            registrations = WebinarRegistration.objects.filter(id__in=registration_ids)
            
            # Filter by instructor permissions
            if request.user.role == 'instructor':
                registrations = registrations.filter(webinar__instructor=request.user)
            
            # Send reminders
            sent_count = 0
            for registration in registrations:
                try:
                    send_webinar_reminder_email(registration)
                    registration.reminder_sent = True
                    registration.reminder_sent_at = timezone.now()
                    registration.save(update_fields=['reminder_sent', 'reminder_sent_at'])
                    sent_count += 1
                except Exception as e:
                    print(f"Failed to send reminder to {registration.email}: {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'Reminders sent to {sent_count} participants',
                'count': sent_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def send_webinar_reminder_email(registration):
    """Send webinar reminder email"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    webinar = registration.webinar
    
    subject = f"Reminder: {webinar.title} - Tomorrow!"
    
    webinar_link_text = (
        f"Join link: {webinar.webinar_link}" 
        if webinar.webinar_link 
        else "Join link will be shared shortly before the webinar."
    )
    
    message = f"""
Dear {registration.get_full_name()},

This is a friendly reminder about your upcoming webinar:

Webinar: {webinar.title}
Date & Time: {webinar.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}
Duration: {webinar.duration_minutes} minutes
Instructor: {webinar.instructor.get_full_name()}

{webinar_link_text}

We're excited to see you there!

Best regards,
LMS Team
"""
    
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [registration.email],
        fail_silently=False,
    )


# Add Payment Filter Support in admin_all_registrations
@login_required
def admin_all_registrations(request):
    """View all webinar registrations with payment filter"""
    
    if request.user.role not in ['superadmin', 'instructor']:
        return redirect('webinars:webinar_landing')
    
    registrations = WebinarRegistration.objects.filter(is_active=True)
    
    # Filter by instructor
    if request.user.role == 'instructor':
        registrations = registrations.filter(webinar__instructor=request.user)
    
    # Search and filters
    search = request.GET.get('search', '')
    webinar_id = request.GET.get('webinar', '')
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')  # Add payment status filter
    
    if search:
        registrations = registrations.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(webinar__title__icontains=search)
        )
    
    if webinar_id:
        registrations = registrations.filter(webinar_id=webinar_id)
    
    if status:
        registrations = registrations.filter(status=status)
    
    if payment_status:
        registrations = registrations.filter(payment_status=payment_status)
    
    # Order by registration date
    registrations = registrations.select_related('webinar', 'user').order_by('-registered_at')
    
    # Pagination
    paginator = Paginator(registrations, 20)
    page = request.GET.get('page')
    registrations = paginator.get_page(page)
    
    # Get webinars for filter dropdown
    if request.user.role == 'instructor':
        webinars = Webinar.objects.filter(instructor=request.user, is_active=True)
    else:
        webinars = Webinar.objects.filter(is_active=True)
    
    # Get stats for dashboard cards including payment stats
    all_registrations = WebinarRegistration.objects.filter(is_active=True)
    if request.user.role == 'instructor':
        all_registrations = all_registrations.filter(webinar__instructor=request.user)
    
    stats = {
        'attended_count': all_registrations.filter(status='attended').count(),
        'no_show_count': all_registrations.filter(status='no_show').count(),
        'cancelled_count': all_registrations.filter(status='cancelled').count(),
        'paid_count': all_registrations.filter(payment_status='paid').count(),
        'pending_payment_count': all_registrations.filter(payment_status='pending').count(),
    }
    
    context = {
        'registrations': registrations,
        'webinars': webinars,
        'search': search,
        'webinar_id': webinar_id,
        'status': status,
        'payment_status': payment_status,  # Add to context
        **stats,  # Add stats to context
    }
    
    return render(request, 'webinars/admin/all_registrations.html', context)
# Add this to your webinars/views.py

def simple_landing(request):
    """Simple test landing page with registration form"""
    
    # Get upcoming webinars for display
    upcoming_webinars = Webinar.objects.filter(
        status='upcoming',
        is_active=True,
        scheduled_date__gt=timezone.now()
    ).order_by('scheduled_date')[:6]
    
    # Get stats
    stats = {
        'total_webinars': Webinar.objects.filter(is_active=True).count(),
        'total_attendees': WebinarRegistration.objects.filter(is_active=True).count(),
        'upcoming_webinars': upcoming_webinars.count(),
        'free_webinars': Webinar.objects.filter(webinar_type='free', is_active=True).count(),
    }
    
    context = {
        'webinars': upcoming_webinars,
        'stats': stats,
    }
    
    return render(request, 'webinars/simple_landing.html', context)


# Update your API settings in api_views.py:
API_KEYS = {
    'external_website_1': 'test-api-key-12345',  # Use this for testing
    'external_website_2': 'another-secret-key',
    # Add more as needed
}

# Also add this AJAX view for direct testing:
@csrf_exempt
def ajax_register(request):
    """AJAX endpoint for testing registration from landing page"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        data = json.loads(request.body)
        
        # Directly call registration logic without API authentication for testing
        webinar = get_object_or_404(Webinar, id=data['webinar_id'], is_active=True)
        
        if not webinar.is_registration_open():
            return JsonResponse({
                'success': False,
                'error': 'Registration is closed for this webinar'
            })
        
        # Check if email already registered
        if WebinarRegistration.objects.filter(
            webinar=webinar,
            email=data['email'].lower(),
            is_active=True
        ).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email already registered for this webinar'
            })
        
        # Create registration with auto user creation
        registration = WebinarRegistration.create_registration(
            webinar=webinar,
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data.get('phone_number', ''),
            company=data.get('company', ''),
            designation=data.get('designation', '')
        )
        
        # Update webinar stats
        webinar.total_registrations = webinar.get_registration_count()
        webinar.save(update_fields=['total_registrations'])
        
        return JsonResponse({
            'success': True,
            'message': 'Registration successful',
            'registration_id': registration.id,
            'login_details': {
                'email': registration.user.email,
                'username': registration.user.username,
                'login_url': f"{request.scheme}://{request.get_host()}/login/",
                'webinar_access_url': f"{request.scheme}://{request.get_host()}/webinars/my-webinars/"
            },
            'webinar_details': {
                'title': webinar.title,
                'scheduled_date': webinar.scheduled_date.isoformat(),
                'duration_minutes': webinar.duration_minutes
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




# Add this to your webinars/views.py

@login_required
def admin_manage_categories(request):
    """Manage webinar categories"""
    
    if request.user.role not in ['superadmin']:  # Only superadmin can manage categories
        return redirect('webinars:admin_webinar_dashboard')
    
    categories = WebinarCategory.objects.all().order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Add active webinars count to each category
    from django.db.models import Count, Q
    categories = categories.annotate(
        active_webinars_count=Count(
            'webinars', 
            filter=Q(webinars__is_active=True)
        )
    )
    
    # Pagination
    paginator = Paginator(categories, 20)
    page = request.GET.get('page')
    categories = paginator.get_page(page)
    
    context = {
        'categories': categories,
        'search': search,
    }
    
    return render(request, 'webinars/admin/manage_categories.html', context)


@login_required
def admin_edit_category(request, category_id):
    """Edit category"""
    
    if request.user.role not in ['superadmin']:
        return redirect('webinars:admin_webinar_dashboard')
    
    category = get_object_or_404(WebinarCategory, id=category_id)
    
    # Add active webinars count for stats
    from django.db.models import Count, Q
    category.active_webinars_count = category.webinars.filter(is_active=True).count()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            messages.error(request, 'Category name is required.')
        elif WebinarCategory.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            messages.error(request, 'Category with this name already exists.')
        else:
            category.name = name
            category.description = description
            category.is_active = is_active
            category.save()
            messages.success(request, f'Category "{name}" updated successfully!')
            return redirect('webinars:admin_manage_categories')
    
    context = {
        'category': category,
        'title': f'Edit: {category.name}'
    }
    
    return render(request, 'webinars/admin/category_form.html', context)


@login_required
def admin_create_category(request):
    """Create new category"""
    
    if request.user.role not in ['superadmin']:
        return redirect('webinars:admin_webinar_dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Category name is required.')
        elif WebinarCategory.objects.filter(name__iexact=name).exists():
            messages.error(request, 'Category with this name already exists.')
        else:
            WebinarCategory.objects.create(
                name=name,
                description=description
            )
            messages.success(request, f'Category "{name}" created successfully!')
            return redirect('webinars:admin_manage_categories')
    
    return render(request, 'webinars/admin/category_form.html', {
        'title': 'Create New Category'
    })




@login_required
def admin_delete_category(request, category_id):
    """Delete category"""
    
    if request.user.role not in ['superadmin']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if request.method == 'POST':
        category = get_object_or_404(WebinarCategory, id=category_id)
        
        # Check if category has webinars
        webinar_count = category.webinars.filter(is_active=True).count()
        if webinar_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete category. {webinar_count} webinars are using this category.'
            })
        
        category_name = category.name
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" deleted successfully!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})