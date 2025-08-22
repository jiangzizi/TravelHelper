"""
Enhanced security middleware for TravelHelper
"""
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import time
import hashlib

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""
    
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Add CSP for API responses
        if request.path.startswith('/llm_talk'):
            response['Content-Security-Policy'] = "default-src 'none'; script-src 'none';"
        
        return response

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log suspicious request patterns"""
    
    def process_request(self, request):
        # Log API requests
        if request.path.startswith('/llm_talk'):
            client_ip = self.get_client_ip(request)
            logger.info(f"API request from {client_ip} to {request.path}")
            
            # Check for suspicious patterns
            if request.content_type and 'multipart' in request.content_type:
                logger.warning(f"Suspicious multipart request from {client_ip}")
            
            if request.META.get('CONTENT_LENGTH'):
                content_length = int(request.META['CONTENT_LENGTH'])
                if content_length > 100000:  # 100KB limit
                    logger.warning(f"Large request ({content_length} bytes) from {client_ip}")
                    return JsonResponse({"error": "Request too large"}, status=413)
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

class APISecurityMiddleware(MiddlewareMixin):
    """Enhanced API security measures"""
    
    def process_request(self, request):
        if request.path.startswith('/llm_talk'):
            # Check request method
            if request.method not in ['POST', 'OPTIONS']:
                return JsonResponse({"error": "Method not allowed"}, status=405)
            
            # Basic DDoS protection - track request frequency
            client_ip = self.get_client_ip(request)
            if self.is_suspicious_activity(client_ip):
                logger.warning(f"Blocking suspicious activity from {client_ip}")
                return JsonResponse({"error": "Too many requests"}, status=429)
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def is_suspicious_activity(self, client_ip):
        """Check for suspicious activity patterns"""
        cache_key = f"suspicious_{client_ip}"
        requests_count = cache.get(cache_key, 0)
        
        # More than 20 requests in 10 minutes is suspicious
        if requests_count > 20:
            return True
        
        cache.set(cache_key, requests_count + 1, 600)  # 10 minutes
        return False