from plataforma_de_servicos.core.models import SiteConfig


def site_config(request):
    """
    Context processor que disponibiliza as configurações do site em todos os templates.
    Uso nos templates: {{ site_config.site_name }}, {{ site_config.hero_title }}, etc.

    O tenant é obtido do request (definido pelo TenantMiddleware).
    """
    tenant = getattr(request, "tenant", None)
    config = SiteConfig.get_config(empresa=tenant)
    theme = config.get_theme()
    theme_css_vars = config.get_theme_css_vars()

    # Converte as variáveis CSS para uma string inline
    css_vars_string = "; ".join(f"{k}: {v}" for k, v in theme_css_vars.items())

    return {
        "site_config": config,
        "theme": theme,
        "theme_css_vars": css_vars_string,
        "is_dark_theme": theme.style == "dark",
    }
