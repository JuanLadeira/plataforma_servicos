from django.core.validators import RegexValidator
from django.db import models


class TipoIsolamento(models.TextChoices):
    """Tipos de isolamento de dados para multitenancy."""

    COMPARTILHADO = "COMPARTILHADO", "Banco Compartilhado (Padrão)"
    DEDICADO = "DEDICADO", "Banco Dedicado (Schema PostgreSQL)"


class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    email = models.EmailField()
    imo = models.CharField(max_length=100)
    foto = models.ImageField(upload_to="empresas/", blank=True, null=True)

    # Campos para customizar os endpoints dos portais administrativos
    admin_url = models.CharField(
        max_length=50,
        default="gerentes",
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9-]+$',
                message='Use apenas letras minúsculas, números e hífens.',
            ),
        ],
        help_text="Endpoint do painel de gerentes (ex: 'gerentes' → /gerentes/). "
                  "Use apenas letras minúsculas, números e hífens.",
        verbose_name="URL do Portal de Gerentes",
    )
    vendedor_url = models.CharField(
        max_length=50,
        default="vendedores",
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9-]+$',
                message='Use apenas letras minúsculas, números e hífens.',
            ),
        ],
        help_text="Endpoint do painel de vendedores (ex: 'vendedores' → /vendedores/). "
                  "Use apenas letras minúsculas, números e hífens.",
        verbose_name="URL do Portal de Vendedores",
    )

    # ========================================
    # Personalização da UI do Admin
    # ========================================
    admin_title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Título do Admin",
        help_text="Título exibido no cabeçalho do painel administrativo. Se vazio, usa o nome da empresa.",
    )
    admin_subtitle = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Subtítulo do Admin",
        help_text="Subtítulo exibido abaixo do título no painel administrativo.",
    )
    admin_logo = models.ImageField(
        upload_to="empresas/logos/",
        blank=True,
        null=True,
        verbose_name="Logo do Admin",
        help_text="Logo exibido no cabeçalho do painel (recomendado: 180x40px).",
    )
    admin_favicon = models.ImageField(
        upload_to="empresas/favicons/",
        blank=True,
        null=True,
        verbose_name="Favicon",
        help_text="Ícone exibido na aba do navegador (recomendado: 32x32px).",
    )

    # Cores do tema
    primary_color = models.CharField(
        max_length=7,
        default="#0ea5e9",
        verbose_name="Cor Primária",
        help_text="Cor principal do tema (hex). Ex: #0ea5e9 (azul)",
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Use formato hexadecimal. Ex: #0ea5e9',
            ),
        ],
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#64748b",
        verbose_name="Cor Secundária",
        help_text="Cor secundária do tema (hex). Ex: #64748b (cinza)",
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Use formato hexadecimal. Ex: #64748b',
            ),
        ],
    )
    accent_color = models.CharField(
        max_length=7,
        default="#f59e0b",
        verbose_name="Cor de Destaque",
        help_text="Cor para elementos de destaque (hex). Ex: #f59e0b (amarelo)",
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Use formato hexadecimal. Ex: #f59e0b',
            ),
        ],
    )
    sidebar_style = models.CharField(
        max_length=10,
        choices=[
            ("light", "Claro"),
            ("dark", "Escuro"),
        ],
        default="dark",
        verbose_name="Estilo do Sidebar",
        help_text="Tema do menu lateral.",
    )

    # Textos personalizados
    welcome_message = models.TextField(
        blank=True,
        verbose_name="Mensagem de Boas-vindas",
        help_text="Mensagem exibida na página inicial do admin.",
    )
    footer_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Texto do Rodapé",
        help_text="Texto exibido no rodapé do admin. Ex: '© 2024 Sua Empresa'",
    )

    # ========================================
    # Isolamento de Dados (Banco Dedicado)
    # ========================================
    tipo_isolamento = models.CharField(
        max_length=20,
        choices=TipoIsolamento.choices,
        default=TipoIsolamento.COMPARTILHADO,
        verbose_name="Tipo de Isolamento de Dados",
        help_text=(
            "Compartilhado: dados filtrados por empresa na mesma tabela (padrão). "
            "Dedicado: schema PostgreSQL exclusivo para maior isolamento."
        ),
    )
    schema_name = models.CharField(
        max_length=63,  # Limite do PostgreSQL para identificadores
        blank=True,
        null=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-z][a-z0-9_]*$",
                message="Schema deve iniciar com letra minúscula e conter apenas letras, números e underscore.",
            ),
        ],
        verbose_name="Nome do Schema",
        help_text="Nome do schema PostgreSQL. Auto-gerado a partir do slug se não informado.",
    )
    schema_criado = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="Schema Provisionado",
        help_text="Indica se o schema PostgreSQL foi criado.",
    )
    schema_criado_em = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name="Data de Criação do Schema",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_admin_url(self):
        """Retorna a URL completa do portal de gerentes."""
        return f"/{self.admin_url}/"

    def get_vendedor_url(self):
        """Retorna a URL completa do portal de vendedores."""
        return f"/{self.vendedor_url}/"

    def get_admin_title(self):
        """Retorna o título do admin (personalizado ou nome da empresa)."""
        return self.admin_title or self.nome

    def get_theme_colors(self):
        """Retorna as cores do tema como dicionário."""
        return {
            "primary": self.primary_color,
            "secondary": self.secondary_color,
            "accent": self.accent_color,
        }

    # ========================================
    # Métodos de Isolamento de Dados
    # ========================================
    def gerar_schema_name(self):
        """Gera nome do schema a partir do slug."""
        return f"tenant_{self.slug.replace('-', '_').lower()}"

    @property
    def usa_banco_dedicado(self):
        """Verifica se empresa usa banco dedicado E schema está provisionado."""
        return (
            self.tipo_isolamento == TipoIsolamento.DEDICADO
            and self.schema_criado
        )

    @property
    def database_alias(self):
        """Retorna o alias do banco a ser usado pelo router."""
        if self.usa_banco_dedicado:
            return f"tenant_{self.schema_name}"
        return "default"
