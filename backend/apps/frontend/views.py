"""
Views for serving frontend website files.
"""
import os
import re
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_control
from django.templatetags.static import static


@csrf_exempt
@cache_control(max_age=3600)  # Cache for 1 hour
def serve_frontend_file(request, file_path='Index.html'):
    """
    Serve frontend HTML files with proper content type and static file handling.
    """
    # Map common paths
    path_mapping = {
        '': 'Index.html',
        'index.html': 'Index.html',
        'Index.html': 'Index.html',
        'services/': 'services.html',
        'services.html': 'services.html',
        'products/': 'Products.html',
        'products.html': 'Products.html',
        'Products.html': 'Products.html',
        'projects/': 'Projects.html',
        'projects.html': 'Projects.html',
        'Projects.html': 'Projects.html',
        'about/': 'About.html',
        'about.html': 'About.html',
        'About.html': 'About.html',
    }
    
    # Get the actual file name
    actual_file = path_mapping.get(file_path, file_path)
    
    # Construct the full path to the frontend file
    frontend_dir = os.path.join(settings.BASE_DIR.parent, 'frontend')
    file_full_path = os.path.join(frontend_dir, actual_file)
    
    # Check if file exists
    if not os.path.exists(file_full_path):
        raise Http404(f"Frontend file not found: {actual_file}")
    
    # Read and serve the file
    try:
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # For HTML files, update static file references to use absolute paths
        if actual_file.endswith('.html'):
            # Replace relative CSS/JS references with absolute static URLs
            content = re.sub(
                r'href="styles\.css"',
                f'href="{request.build_absolute_uri("/static/styles.css")}"',
                content
            )
            content = re.sub(
                r'href="chat\.css"',
                f'href="{request.build_absolute_uri("/static/chat.css")}"',
                content
            )
            content = re.sub(
                r'src="chat\.js"',
                f'src="{request.build_absolute_uri("/static/chat.js")}"',
                content
            )
            content = re.sub(
                r'src="sendemail\.js"',
                f'src="{request.build_absolute_uri("/static/sendemail.js")}"',
                content
            )
            # Fix asset references in Assets folder
            content = re.sub(
                r'src="Assets/([^"]+)"',
                lambda m: f'src="{request.build_absolute_uri(f"/static/Assets/{m.group(1)}")}"',
                content
            )
            content_type = 'text/html'
        elif actual_file.endswith('.css'):
            content_type = 'text/css'
        elif actual_file.endswith('.js'):
            content_type = 'application/javascript'
        else:
            content_type = 'text/plain'
        
        return HttpResponse(content, content_type=content_type)
        
    except Exception as e:
        raise Http404(f"Error reading frontend file: {str(e)}")