import os
import re
from datetime import datetime
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import gettext as _


class CustomLogViewerView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'log_viewer_custom/logs.html'
    context_object_name = 'log_entries'
    paginate_by = 50

    def test_func(self):
        # Only superusers can access logs
        if not self.request.user.is_authenticated:
            return False
        if not self.request.user.is_superuser:
            return False
        return True

    def get_queryset(self):
        log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'log.log')
        
        # If log file doesn't exist or is empty, create sample logs
        if not os.path.exists(log_file_path) or os.path.getsize(log_file_path) == 0:
            self.create_sample_logs()
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Parse log entries
            log_entries = []
            for line in lines:
                entry = self.parse_log_line(line.strip())
                if entry:
                    log_entries.append(entry)
            
            # Reverse to show newest first
            reversed_entries = list(reversed(log_entries))
            

            
            return reversed_entries
            
        except Exception as e:
            return []

    def create_sample_logs(self):
        """Create sample log entries for demonstration"""
        import logging
        
        # Configure logger to write to file
        log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'log.log')
        
        # Create sample log entries
        sample_logs = [
            "INFO 2025-08-21 23:18:14,123 Application started successfully",
            "DEBUG 2025-08-21 23:18:15,456 Database connection established",
            "WARNING 2025-08-21 23:18:16,789 Low disk space detected",
            "ERROR 2025-08-21 23:18:17,012 Failed to connect to external API",
            "CRITICAL 2025-08-21 23:18:18,345 System memory critical",
            "INFO 2025-08-21 23:18:19,678 User login successful",
            "DEBUG 2025-08-21 23:18:20,901 Cache cleared successfully",
            "WARNING 2025-08-21 23:18:21,234 Rate limit approaching",
            "ERROR 2025-08-21 23:18:22,567 Database query timeout",
            "INFO 2025-08-21 23:18:23,890 Backup completed successfully",
        ]
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as file:
                for log_entry in sample_logs:
                    file.write(log_entry + '\n')
        except Exception as e:
            pass

    def parse_log_line(self, line):
        """Parse a log line and extract timestamp, level, and message"""
        if not line.strip():
            return None
        
        # Pattern for Django logging format: {levelname} {asctime} {message}
        # Updated to handle various timestamp formats
        patterns = [
            # Django format: INFO 2025-08-21 23:19:23,058 Message
            r'^(\w+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(.+)$',
            # Django format without milliseconds: INFO 2025-08-21 23:18:14 Message
            r'^(\w+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.+)$',
            # Alternative format: [2025-08-21 23:18:14] INFO: Message
            r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.+)$',
            # Simple format: INFO: Message
            r'^(\w+):\s+(.+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    if pattern == patterns[1]:  # Alternative format
                        timestamp_str, level, message = groups
                    else:  # Standard format
                        level, timestamp_str, message = groups
                    
                    try:
                        # Try to parse timestamp
                        if ':' in timestamp_str and '-' in timestamp_str:
                            if ',' in timestamp_str:
                                # Handle milliseconds format: 2025-08-21 23:19:23,058
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            else:
                                # Handle format without milliseconds: 2025-08-21 23:18:14
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        else:
                            timestamp = datetime.now()
                        
                        return {
                            'timestamp': timestamp,
                            'level': level.upper(),
                            'message': message.strip(),
                            'raw_line': line
                        }
                    except ValueError as e:
                        # If timestamp parsing fails, use current time
                        return {
                            'timestamp': datetime.now(),
                            'level': level.upper(),
                            'message': message.strip(),
                            'raw_line': line
                        }
                elif len(groups) == 2:  # Simple format
                    level, message = groups
                    return {
                        'timestamp': datetime.now(),
                        'level': level.upper(),
                        'message': message.strip(),
                        'raw_line': line
                    }
        
        # If parsing fails, return as INFO level
        return {
            'timestamp': datetime.now(),
            'level': 'INFO',
            'message': line.strip(),
            'raw_line': line
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add level filtering
        level_filter = self.request.GET.get('level', '')
        context['level_filter'] = level_filter
        
        # Filter by level if specified
        if level_filter:
            context['log_entries'] = [
                entry for entry in context['log_entries'] 
                if entry['level'] == level_filter.upper()
            ]
        
        # Add level options for filter
        context['level_options'] = [
            {'value': '', 'label': _('All Levels')},
            {'value': 'DEBUG', 'label': 'DEBUG'},
            {'value': 'INFO', 'label': 'INFO'},
            {'value': 'WARNING', 'label': 'WARNING'},
            {'value': 'ERROR', 'label': 'ERROR'},
            {'value': 'CRITICAL', 'label': 'CRITICAL'},
        ]
        
        # Add level badge mapping
        context['level_badge_map'] = {
            'DEBUG': 'bg-secondary',
            'INFO': 'bg-info',
            'WARNING': 'bg-warning',
            'ERROR': 'bg-danger',
            'CRITICAL': 'bg-dark',
        }
        
        # Add level icon mapping
        context['level_icon_map'] = {
            'DEBUG': 'bi-bug',
            'INFO': 'bi-info-circle',
            'WARNING': 'bi-exclamation-triangle',
            'ERROR': 'bi-exclamation-octagon',
            'CRITICAL': 'bi-x-octagon',
        }
        
        return context


def logs_json_view(request):
    """JSON endpoint for AJAX log loading"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required. Please log in.'}, status=403)
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Superuser privileges required to access logs.'}, status=403)
    
    log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'log.log')
    
    # Create sample logs if file doesn't exist or is empty
    if not os.path.exists(log_file_path) or os.path.getsize(log_file_path) == 0:
        CustomLogViewerView().create_sample_logs()
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Parse and filter logs
        log_entries = []
        view = CustomLogViewerView()
        for line in lines:
            entry = view.parse_log_line(line.strip())
            if entry:
                log_entries.append(entry)
        
        # Reverse to show newest first
        log_entries = list(reversed(log_entries))
        
        # Apply level filter if specified
        level_filter = request.GET.get('level', '')
        if level_filter:
            log_entries = [
                entry for entry in log_entries 
                if entry['level'] == level_filter.upper()
            ]
        
        # Check if this is a download request
        download = request.GET.get('download', '').lower() == 'true'
        if download:
            # Return all entries for download
            formatted_entries = []
            for entry in log_entries:
                formatted_entries.append({
                    'timestamp': entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'level': entry['level'],
                    'message': entry['message'],
                    'raw_line': entry['raw_line']
                })
            
            return JsonResponse({
                'logs': formatted_entries,
                'total': len(formatted_entries),
            })
        
        # Normal pagination
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        
        paginator = Paginator(log_entries, per_page)
        page_obj = paginator.get_page(page)
        
        # Format entries for JSON
        formatted_entries = []
        for entry in page_obj:
            formatted_entries.append({
                'timestamp': entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'level': entry['level'],
                'message': entry['message'],
                'raw_line': entry['raw_line']
            })
        
        # Calculate level statistics
        level_counts = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
        for entry in log_entries:
            level = entry['level']
            if level in level_counts:
                level_counts[level] += 1
        
        return JsonResponse({
            'logs': formatted_entries,
            'total': paginator.count,
            'pages': paginator.num_pages,
            'current_page': page,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'level_counts': level_counts,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
