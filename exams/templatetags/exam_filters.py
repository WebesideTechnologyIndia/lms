# exams/templatetags/exam_filters.py

from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """
    Template filter to look up a dictionary value by key.
    Usage: {{ responses|lookup:question.id }}
    """
    if dictionary is None:
        return None
    
    # Handle different types of keys
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    
    # If it's not a dict, try to convert key to string and look up
    try:
        return dictionary.get(str(key))
    except (AttributeError, TypeError):
        return None

@register.filter
def chr(value):
    """
    Convert integer to character (for option labels A, B, C, D)
    Usage: {{ forloop.counter|add:64|chr }}
    """
    try:
        return chr(int(value))
    except (ValueError, TypeError):
        return ''

@register.filter
def add(value, arg):
    """
    Add the arg to the value.
    Usage: {{ forloop.counter|add:64 }}
    """
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def sub(value, arg):
    """
    Subtract the arg from the value.
    Usage: {{ total|sub:completed }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def mul(value, arg):
    """
    Multiply the value by arg.
    Usage: {{ percentage|mul:3.2673 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    """
    Divide the value by arg.
    Usage: {{ correct|mul:100|div:total }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return value

@register.filter
def get_item(dictionary, key):
    """
    Alternative lookup filter for dictionaries.
    Usage: {{ dict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def range_filter(value):
    """
    Create a range for iteration in templates.
    Usage: {% for i in total_questions|range_filter %}
    """
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def percentage(value, total):
    """
    Calculate percentage.
    Usage: {{ correct_answers|percentage:total_questions }}
    """
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def time_format(seconds):
    """
    Format seconds into HH:MM:SS format.
    Usage: {{ time_spent|time_format }}
    """
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00:00"

@register.filter
def is_answered(responses, question_id):
    """
    Check if a question is answered.
    Usage: {% if responses|is_answered:question.id %}
    """
    if responses is None:
        return False
    
    answer = responses.get(question_id) if isinstance(responses, dict) else None
    if answer is None:
        return False
    
    # For MCQ, check if option is selected
    if isinstance(answer, (int, str)) and str(answer).strip():
        return True
    
    # For text answers, check if not empty
    if isinstance(answer, str) and answer.strip():
        return True
    
    return False

@register.filter
def filesizeformat_mb(bytes_value):
    """
    Format file size in MB.
    Usage: {{ file.size|filesizeformat_mb }}
    """
    try:
        bytes_value = float(bytes_value)
        mb = bytes_value / (1024 * 1024)
        if mb < 0.1:
            return f"{(bytes_value / 1024):.1f} KB"
        else:
            return f"{mb:.1f} MB"
    except (ValueError, TypeError):
        return "0 MB"

@register.filter
def default_if_none_or_empty(value, default):
    """
    Return default if value is None or empty.
    Usage: {{ value|default_if_none_or_empty:"No answer" }}
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return value

@register.simple_tag
def exam_progress_percentage(answered, total):
    """
    Calculate exam progress percentage.
    Usage: {% exam_progress_percentage answered_count total_questions %}
    """
    try:
        if int(total) == 0:
            return 0
        return round((int(answered) / int(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.simple_tag
def exam_time_remaining(start_time, total_minutes):
    """
    Calculate remaining time for exam.
    Usage: {% exam_time_remaining attempt.started_at exam.total_exam_time_minutes %}
    """
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        now = timezone.now()
        elapsed = now - start_time
        total_duration = timedelta(minutes=int(total_minutes))
        remaining = total_duration - elapsed
        
        if remaining.total_seconds() <= 0:
            return 0
        
        return int(remaining.total_seconds())
    except (ValueError, TypeError):
        return 0

@register.inclusion_tag('exam/partials/question_navigator.html')
def question_navigator(questions, responses=None, current_question=1):
    """
    Render question navigator component.
    Usage: {% question_navigator questions responses current_question %}
    """
    question_status = []
    for question in questions:
        is_answered = False
        if responses and isinstance(responses, dict):
            answer = responses.get(question.id)
            is_answered = answer is not None and str(answer).strip()
        
        question_status.append({
            'question': question,
            'is_answered': is_answered,
            'is_current': question.order == current_question
        })
    
    return {
        'question_status': question_status,
        'total_questions': len(questions)
    }

@register.filter
def json_script_safe(value):
    """
    Safely convert Python object to JSON for use in JavaScript.
    Usage: {{ responses|json_script_safe }}
    """
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return mark_safe('{}')

@register.filter
def yesno_custom(value, arg="Yes,No,Maybe"):
    """
    Custom yes/no filter with default values.
    Usage: {{ boolean_value|yesno_custom:"Yes,No" }}
    """
    bits = arg.split(',')
    if len(bits) < 2:
        return value
    
    if value is True:
        return bits[0]
    elif value is False:
        return bits[1]
    elif value is None and len(bits) >= 3:
        return bits[2]
    else:
        return value

@register.filter
def selectattr(objects, attr_name):
    """
    Filter objects that have a truthy attribute.
    Usage: {{ responses|selectattr:"is_correct_answer" }}
    """
    try:
        return [obj for obj in objects if getattr(obj, attr_name, False)]
    except (TypeError, AttributeError):
        return []

@register.filter
def rejectattr(objects, attr_name):
    """
    Filter objects that don't have a truthy attribute.
    Usage: {{ responses|rejectattr:"is_correct_answer" }}
    """
    try:
        return [obj for obj in objects if not getattr(obj, attr_name, False)]
    except (TypeError, AttributeError):
        return []

@register.filter
def to_list(value):
    """
    Convert queryset or other iterable to list.
    Usage: {{ queryset|to_list }}
    """
    try:
        return list(value)
    except (TypeError, AttributeError):
        return []

@register.filter
def count_correct_answers(responses):
    """
    Count correct MCQ responses.
    Usage: {{ mcq_responses|count_correct_answers }}
    """
    try:
        count = 0
        for response in responses:
            if hasattr(response, 'is_correct') and response.is_correct():
                count += 1
            elif hasattr(response, 'is_correct_answer') and response.is_correct_answer:
                count += 1
        return count
    except (TypeError, AttributeError):
        return 0

@register.filter
def count_incorrect_answers(responses):
    """
    Count incorrect MCQ responses (answered but wrong).
    Usage: {{ mcq_responses|count_incorrect_answers }}
    """
    try:
        count = 0
        for response in responses:
            if hasattr(response, 'selected_option') and response.selected_option:
                if hasattr(response, 'is_correct') and not response.is_correct():
                    count += 1
                elif hasattr(response, 'is_correct_answer') and not response.is_correct_answer:
                    count += 1
        return count
    except (TypeError, AttributeError):
        return 0

@register.filter
def count_unanswered(responses):
    """
    Count unanswered MCQ responses.
    Usage: {{ mcq_responses|count_unanswered }}
    """
    try:
        count = 0
        for response in responses:
            if hasattr(response, 'selected_option') and not response.selected_option:
                count += 1
        return count
    except (TypeError, AttributeError):
        return 0

@register.filter
def list_length(value):
    """
    Get length of a list or queryset.
    Usage: {{ some_list|list_length }}
    """
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0