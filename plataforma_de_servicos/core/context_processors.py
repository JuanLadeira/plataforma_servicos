from plataforma_de_servicos.core.models import SiteConfig


def site_config(request):
    """
    Context processor que disponibiliza as configurações do site em todos os templates.
    Uso nos templates: {{ site_config.site_name }}, {{ site_config.hero_title }}, etc.
    """
    return {"site_config": SiteConfig.get_config()}
