from .models import SiteConfiguration

def site_config(request):
    config = SiteConfiguration.objects.first()
    return {'site_config': config}
