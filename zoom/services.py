# zoom/services.py - Fixed ZoomAPIService with OAuth 2.0

import requests
import base64
import time
from datetime import datetime, timedelta
from django.conf import settings
from .models import ZoomConfiguration, BatchSession, ZoomRecording

class ZoomAPIService:
    """Zoom API Integration Service with OAuth 2.0"""
    
    def __init__(self, config=None):
        """Initialize with specific config or get active one"""
        if config:
            self.config = config
        else:
            self.config = ZoomConfiguration.get_active_config()
        
        if not self.config:
            raise Exception("No active Zoom configuration found! Please configure Zoom settings in admin.")
        
        if not self.config.is_configured:
            raise Exception("Zoom configuration incomplete! Please fill all required fields.")
        
        self.base_url = "https://api.zoom.us/v2"
        self.access_token = None
    
    def get_access_token(self):
        """Get OAuth 2.0 access token - FIXED METHOD"""
        print(f"\n=== GETTING ACCESS TOKEN ===")
        
        if self.access_token:
            print("Using cached access token")
            return self.access_token
        
        try:
            # OAuth 2.0 Server-to-Server flow
            auth_url = "https://zoom.us/oauth/token"
            
            # Encode credentials
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
            
            print(f"Token request URL: {auth_url}")
            print(f"Account ID: {self.config.account_id}")
            print(f"Client ID: {self.config.client_id[:8]}...")
            
            response = requests.post(auth_url, headers=headers, data=data, timeout=30)
            
            print(f"Token response status: {response.status_code}")
            print(f"Token response: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                
                if self.access_token:
                    print(f"SUCCESS: Access token obtained")
                    return self.access_token
                else:
                    raise Exception("No access token in response")
            else:
                error_data = response.json() if response.content else {}
                raise Exception(f"Token request failed: {response.status_code} - {error_data}")
        
        except Exception as e:
            print(f"ERROR getting access token: {e}")
            raise Exception(f"Failed to get access token: {str(e)}")
    
    def get_headers(self):
        """Get common headers for API requests"""
        return {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
    
    def create_meeting(self, session):
        """Create Zoom meeting using OAuth 2.0"""
        print(f"\n=== ZOOM MEETING CREATION DEBUG ===")
        print(f"Session: {session.title}")
        print(f"Batch: {session.batch.name}")
        
        url = f"{self.base_url}/users/me/meetings"
        
        # Manual datetime formatting
        from datetime import datetime
        meeting_datetime = datetime.combine(session.scheduled_date, session.start_time)
        meeting_start_time = meeting_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        
        print(f"Meeting start time: {meeting_start_time}")
        
        # Use dynamic settings from configuration
        meeting_data = {
            'topic': f"{session.batch.name} - {session.title}",
            'type': 2,  # Scheduled meeting
            'start_time': meeting_start_time,
            'duration': session.duration_minutes,
            'timezone': 'Asia/Kolkata',
            'agenda': session.description or f"Session for {session.batch.name}",
            'settings': {
                'host_video': getattr(self.config, 'default_host_video', True),
                'participant_video': getattr(self.config, 'default_participant_video', True),
                'cn_meeting': False,
                'in_meeting': False,
                'join_before_host': getattr(self.config, 'default_join_before_host', True),
                'mute_upon_entry': getattr(self.config, 'default_mute_upon_entry', True),
                'watermark': False,
                'use_pmi': False,
                'approval_type': 2,
                'audio': 'both',
                'auto_recording': getattr(self.config, 'default_auto_recording', 'cloud'),
                'enforce_login': False,
                'registrants_email_notification': True,
                'waiting_room': getattr(self.config, 'default_waiting_room', True),
                'meeting_authentication': False
            }
        }
        
        print(f"Meeting data prepared: {meeting_data}")
        
        try:
            headers = self.get_headers()
            print(f"Request headers: Authorization: Bearer [TOKEN], Content-Type: {headers['Content-Type']}")
            
            response = requests.post(url, json=meeting_data, headers=headers, timeout=30)
            
            print(f"Zoom API Response Status: {response.status_code}")
            print(f"Zoom API Response: {response.text}")
            
            if response.status_code == 201:
                meeting_info = response.json()
                print(f"SUCCESS: Meeting created - ID: {meeting_info.get('id')}")
                
                # Update session with Zoom details
                session.zoom_meeting_id = str(meeting_info['id'])
                session.zoom_meeting_password = meeting_info.get('password', '')
                session.zoom_join_url = meeting_info['join_url']
                session.zoom_start_url = meeting_info['start_url']
                session.save()
                
                print(f"Session updated with Zoom details")
                return True, meeting_info
            else:
                error_msg = f"Failed to create meeting: {response.status_code} - {response.text}"
                print(f"ERROR: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            print(f"EXCEPTION in create_meeting: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def test_connection(self):
        """Test Zoom API connection"""
        try:
            print("\n=== TESTING ZOOM CONNECTION ===")
            
            # Test token generation
            token = self.get_access_token()
            if not token:
                return False, "Failed to get access token"
            
            # Test API call
            url = f"{self.base_url}/users/me"
            headers = self.get_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"Test API call status: {response.status_code}")
            print(f"Test API response: {response.text}")
            
            if response.status_code == 200:
                user_data = response.json()
                return True, f"Connection successful. User: {user_data.get('email', 'Unknown')}"
            else:
                return False, f"API test failed: {response.status_code} - {response.text}"
                
        except Exception as e:
            print(f"Connection test error: {e}")
            return False, f"Connection test failed: {str(e)}"
    
    def update_meeting(self, session):
        """Update existing Zoom meeting"""
        if not session.zoom_meeting_id:
            return False, "No meeting ID found for this session"
        
        url = f"{self.base_url}/meetings/{session.zoom_meeting_id}"
        
        # Manual datetime formatting
        from datetime import datetime
        meeting_datetime = datetime.combine(session.scheduled_date, session.start_time)
        meeting_start_time = meeting_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        
        meeting_data = {
            'topic': f"{session.batch.name} - {session.title}",
            'type': 2,  # Scheduled meeting
            'start_time': meeting_start_time,
            'duration': session.duration_minutes,
            'timezone': 'Asia/Kolkata',
            'agenda': session.description,
            'settings': {
                'host_video': getattr(self.config, 'default_host_video', True),
                'participant_video': getattr(self.config, 'default_participant_video', True),
                'join_before_host': getattr(self.config, 'default_join_before_host', True),
                'mute_upon_entry': getattr(self.config, 'default_mute_upon_entry', True),
                'auto_recording': getattr(self.config, 'default_auto_recording', 'cloud'),
                'waiting_room': getattr(self.config, 'default_waiting_room', True),
            }
        }
        
        try:
            response = requests.patch(url, json=meeting_data, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 204:
                return True, "Meeting updated successfully"
            else:
                return False, f"Failed to update meeting: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Update failed: {str(e)}"
    
    def delete_meeting(self, meeting_id):
        """Delete Zoom meeting"""
        url = f"{self.base_url}/meetings/{meeting_id}"
        
        try:
            response = requests.delete(url, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 204:
                return True, "Meeting deleted successfully"
            else:
                return False, f"Failed to delete meeting: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def get_meeting_details(self, meeting_id):
        """Get Zoom meeting details"""
        url = f"{self.base_url}/meetings/{meeting_id}"
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Failed to get meeting details: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Get details failed: {str(e)}"
    
    def get_user_info(self):
        """Get current Zoom user information"""
        url = f"{self.base_url}/users/me"
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Failed to get user info: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Get user info failed: {str(e)}"
    
    def get_meeting_recordings(self, meeting_id):
        """Get recordings for a specific meeting"""
        url = f"{self.base_url}/meetings/{meeting_id}/recordings"
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                recordings = data.get('recording_files', [])
                return True, recordings
            elif response.status_code == 404:
                return True, []  # No recordings found
            else:
                return False, f"Failed to get recordings: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Get recordings failed: {str(e)}"