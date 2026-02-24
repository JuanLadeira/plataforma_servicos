"""
Temas pré-definidos para personalização do site.

Cada tema define cores e estilos que são aplicados na interface do site.
"""

from dataclasses import dataclass


@dataclass
class Theme:
    """Configuração de um tema."""

    name: str
    display_name: str
    description: str
    # Cores principais
    primary_color: str  # Cor principal (botões, links, destaques)
    secondary_color: str  # Cor secundária (textos secundários, bordas)
    accent_color: str  # Cor de destaque (badges, alertas positivos)
    # Cores de fundo
    bg_color: str  # Fundo principal
    bg_secondary_color: str  # Fundo secundário (cards, seções)
    # Cores de texto
    text_color: str  # Texto principal
    text_muted_color: str  # Texto secundário
    # Navbar
    navbar_bg: str  # Fundo do navbar
    navbar_text: str  # Texto do navbar
    # Footer
    footer_bg: str  # Fundo do footer
    footer_text: str  # Texto do footer
    # Estilo do tema
    style: str  # "light" ou "dark"


# =============================================================================
# TEMAS PRÉ-DEFINIDOS
# =============================================================================

THEMES = {
    "default": Theme(
        name="default",
        display_name="Padrão",
        description="Tema clássico azul, clean e profissional",
        primary_color="#0ea5e9",  # Sky blue
        secondary_color="#64748b",  # Slate
        accent_color="#f59e0b",  # Amber
        bg_color="#ffffff",
        bg_secondary_color="#f8fafc",
        text_color="#1e293b",
        text_muted_color="#64748b",
        navbar_bg="#ffffff",
        navbar_text="#1e293b",
        footer_bg="#1e293b",
        footer_text="#f8fafc",
        style="light",
    ),
    "dark": Theme(
        name="dark",
        display_name="Escuro",
        description="Tema escuro elegante, ideal para tecnologia e modernidade",
        primary_color="#3b82f6",  # Blue
        secondary_color="#6b7280",  # Gray
        accent_color="#10b981",  # Emerald
        bg_color="#111827",
        bg_secondary_color="#1f2937",
        text_color="#f9fafb",
        text_muted_color="#9ca3af",
        navbar_bg="#1f2937",
        navbar_text="#f9fafb",
        footer_bg="#030712",
        footer_text="#d1d5db",
        style="dark",
    ),
    "nature": Theme(
        name="nature",
        display_name="Natureza",
        description="Tons verdes naturais, perfeito para produtos orgânicos e sustentáveis",
        primary_color="#16a34a",  # Green
        secondary_color="#65a30d",  # Lime
        accent_color="#ca8a04",  # Yellow
        bg_color="#ffffff",
        bg_secondary_color="#f0fdf4",
        text_color="#14532d",
        text_muted_color="#4d7c0f",
        navbar_bg="#166534",
        navbar_text="#ffffff",
        footer_bg="#14532d",
        footer_text="#dcfce7",
        style="light",
    ),
    "luxury": Theme(
        name="luxury",
        display_name="Luxo",
        description="Dourado e preto, sofisticação para produtos premium",
        primary_color="#d4af37",  # Gold
        secondary_color="#1a1a1a",  # Black
        accent_color="#b8860b",  # Dark golden
        bg_color="#0a0a0a",
        bg_secondary_color="#1a1a1a",
        text_color="#fafafa",
        text_muted_color="#a3a3a3",
        navbar_bg="#0a0a0a",
        navbar_text="#d4af37",
        footer_bg="#000000",
        footer_text="#d4af37",
        style="dark",
    ),
    "energy": Theme(
        name="energy",
        display_name="Energia",
        description="Laranja vibrante, transmite dinamismo e entusiasmo",
        primary_color="#ea580c",  # Orange
        secondary_color="#dc2626",  # Red
        accent_color="#facc15",  # Yellow
        bg_color="#ffffff",
        bg_secondary_color="#fff7ed",
        text_color="#1c1917",
        text_muted_color="#78716c",
        navbar_bg="#ea580c",
        navbar_text="#ffffff",
        footer_bg="#431407",
        footer_text="#fed7aa",
        style="light",
    ),
    "axe": Theme(
        name="axe",
        display_name="Axé",
        description="Roxo e dourado, inspirado nas religiões de matriz africana",
        primary_color="#7c3aed",  # Violet
        secondary_color="#d4af37",  # Gold
        accent_color="#fbbf24",  # Amber
        bg_color="#faf5ff",
        bg_secondary_color="#f3e8ff",
        text_color="#2e1065",
        text_muted_color="#6b21a8",
        navbar_bg="#5b21b6",
        navbar_text="#ffffff",
        footer_bg="#2e1065",
        footer_text="#e9d5ff",
        style="light",
    ),
    "ocean": Theme(
        name="ocean",
        display_name="Oceano",
        description="Azul turquesa, sensação de frescor e tranquilidade",
        primary_color="#0891b2",  # Cyan
        secondary_color="#0e7490",  # Dark cyan
        accent_color="#06b6d4",  # Light cyan
        bg_color="#ffffff",
        bg_secondary_color="#ecfeff",
        text_color="#164e63",
        text_muted_color="#0e7490",
        navbar_bg="#0e7490",
        navbar_text="#ffffff",
        footer_bg="#164e63",
        footer_text="#cffafe",
        style="light",
    ),
    "rose": Theme(
        name="rose",
        display_name="Rosa",
        description="Rosa elegante, feminino e moderno",
        primary_color="#db2777",  # Pink
        secondary_color="#be185d",  # Dark pink
        accent_color="#f472b6",  # Light pink
        bg_color="#ffffff",
        bg_secondary_color="#fdf2f8",
        text_color="#831843",
        text_muted_color="#9d174d",
        navbar_bg="#be185d",
        navbar_text="#ffffff",
        footer_bg="#831843",
        footer_text="#fbcfe8",
        style="light",
    ),
    "earth": Theme(
        name="earth",
        display_name="Terra",
        description="Tons terrosos, aconchegante e rústico",
        primary_color="#a16207",  # Brown/amber
        secondary_color="#78350f",  # Dark brown
        accent_color="#d97706",  # Amber
        bg_color="#fffbeb",
        bg_secondary_color="#fef3c7",
        text_color="#451a03",
        text_muted_color="#78350f",
        navbar_bg="#78350f",
        navbar_text="#fef3c7",
        footer_bg="#451a03",
        footer_text="#fde68a",
        style="light",
    ),
    "minimal": Theme(
        name="minimal",
        display_name="Minimalista",
        description="Preto e branco, design limpo e focado no conteúdo",
        primary_color="#18181b",  # Zinc 900
        secondary_color="#71717a",  # Zinc 500
        accent_color="#a1a1aa",  # Zinc 400
        bg_color="#ffffff",
        bg_secondary_color="#fafafa",
        text_color="#18181b",
        text_muted_color="#71717a",
        navbar_bg="#ffffff",
        navbar_text="#18181b",
        footer_bg="#18181b",
        footer_text="#fafafa",
        style="light",
    ),
    "gatopreto": Theme(
        name="gatopreto",
        display_name="Gato Preto",
        description="Tema escuro elegante com dourado, perfeito para lojas de artigos religiosos",
        primary_color="#c9a227",  # Dourado rico e vibrante
        secondary_color="#8b7355",  # Bronze suave
        accent_color="#e8d5a3",  # Dourado claro/champagne
        bg_color="#0d0d0d",  # Preto profundo
        bg_secondary_color="#1a1a1a",  # Cinza muito escuro para cards
        text_color="#f5f5f5",  # Branco suave (menos agressivo)
        text_muted_color="#a8a8a8",  # Cinza médio para boa leitura
        navbar_bg="#0d0d0d",  # Preto profundo
        navbar_text="#c9a227",  # Dourado
        footer_bg="#050505",  # Preto quase absoluto
        footer_text="#c9a227",  # Dourado
        style="dark",
    ),
    "mystic": Theme(
        name="mystic",
        display_name="Místico",
        description="Roxo profundo com dourado, atmosfera espiritual e misteriosa",
        primary_color="#c084fc",  # Purple light
        secondary_color="#d4af37",  # Gold
        accent_color="#fbbf24",  # Amber
        bg_color="#1e1b2e",  # Dark purple
        bg_secondary_color="#2d2640",  # Purple dark
        text_color="#f5f3ff",  # Light purple
        text_muted_color="#a78bfa",  # Violet
        navbar_bg="#13111c",  # Very dark purple
        navbar_text="#c084fc",  # Purple light
        footer_bg="#0c0a14",  # Almost black purple
        footer_text="#c084fc",  # Purple light
        style="dark",
    ),
}

# Choices para o campo de seleção no modelo
THEME_CHOICES = [(key, theme.display_name) for key, theme in THEMES.items()]


def get_theme(theme_name: str) -> Theme:
    """Retorna o tema pelo nome. Se não existir, retorna o padrão."""
    return THEMES.get(theme_name, THEMES["default"])


def get_theme_css_vars(theme_name: str) -> dict:
    """Retorna as variáveis CSS para um tema."""
    theme = get_theme(theme_name)
    return {
        "--color-primary": theme.primary_color,
        "--color-secondary": theme.secondary_color,
        "--color-accent": theme.accent_color,
        "--color-bg": theme.bg_color,
        "--color-bg-secondary": theme.bg_secondary_color,
        "--color-text": theme.text_color,
        "--color-text-muted": theme.text_muted_color,
        "--color-navbar-bg": theme.navbar_bg,
        "--color-navbar-text": theme.navbar_text,
        "--color-footer-bg": theme.footer_bg,
        "--color-footer-text": theme.footer_text,
    }
