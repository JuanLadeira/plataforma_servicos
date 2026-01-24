# Gemini Context: plataforma_de_servicos

## Project Overview

This is a Django-based e-commerce and service platform named `plataforma_de_servicos`. The project is structured into several Django apps, handling different domains of the application. It features a sophisticated inventory management system, product and category management, a shopping cart, user accounts, and a payment system. The project uses Django REST Framework to provide APIs and `django-unfold` for a customized admin experience, including a separate admin site for managers. The frontend leverages `htmx` for dynamic user interactions.

## Core Technologies

- **Backend:** Django, Django REST Framework
- **Frontend:** Django Templates, htmx, Bootstrap, jQuery
- **Database:** (Assumed) PostgreSQL, based on `psycopg2` in `requirements.txt`.
- **Admin:** `django-unfold` for a modern admin interface, with a custom "Gerente" (Manager) site.
- **Testing:** `pytest`, `pytest-django`, `factory-boy`
- **Authentication:** `django-allauth` for user registration, login, and social accounts.

## Application Modules (Apps)

The project is divided into the following Django applications inside the `plataforma_de_servicos` directory:

- **`account`**: Manages user authentication, registration, profile management, password reset, and email verification.
- **`cart`**: Implements the shopping cart functionality using Django sessions. It provides views for adding, deleting, and updating cart items, which are called via `htmx` from the frontend.
- **`produto`**: The primary application for managing products (`Produto`) and categories (`Categoria`). It includes models for product images and provides REST APIs for CRUD operations. It seems to be the more modern replacement for the `store` app.
- **`estoque`**: A comprehensive inventory management system. It handles stock movements like entries (`EstoqueEntrada`) and exits (`EstoqueSaida`) using proxy models. It features a `processar` method to update stock levels and exposes REST APIs for management.
- **`inventario`**: Works with the `estoque` app to manage stock across multiple physical locations (`Inventario`). It tracks the balance of each product per inventory location (`InventarioSaldo`).
- **`payment`**: Handles the checkout process, with models for `ShippingAddress`, `Order`, and `OrderItem`. The templates suggest an integration with PayPal.
- **`core`**: Contains shared components, including a `TimeStampedModel` base class and the definition of the custom `GerenteAdminSite`.
- **`users`**: Defines a custom `User` model that uses email as the primary identifier, along with `Funcionario` (Employee) and `Cliente` (Customer) profile models.
- **`empresa`**: A simple app defining a `Empresa` (Company) model.
- **`servico`**: Appears to be a placeholder or a less developed part of the project, possibly for managing services as opposed to products.
- **`store`**: A legacy or simpler app for products and categories. Some base templates still inherit from `store/base.html`, indicating a potential mix of old and new code.

## Key Features

- **Product Catalog:** Users can browse products, filter by category, and search.
- **Shopping Cart:** Dynamic, session-based cart where users can add, update, and remove products using `htmx` for a smooth UX without full page reloads.
- **User Authentication:** Full user lifecycle management via `django-allauth`, including email verification and password reset.
- **Checkout & Payment:** Multi-step checkout process with shipping address management and payment integration.
- **Inventory Management:** Detailed tracking of product stock across different inventories (locations). Stock levels are automatically updated upon entries and exits.
- **REST APIs:** The application exposes APIs for managing products, categories, and stock movements.
- **Custom Admin Interfaces:**
    - A standard admin site.
    - A specialized `/gerentes` admin site for managers, providing a focused interface for managing products, categories, and inventory, built with `django-unfold`.

## Frontend

- The frontend is built with **Django Templates**.
- **`htmx`** is used extensively for AJAX-powered interactions, such as updating the cart, filtering products, and searching, without writing complex JavaScript.
- Styling is done with **Bootstrap** and custom CSS located in `plataforma_de_servicos/static/css/`.
- The main public-facing templates are located in `plataforma_de_servicos/templates/pages/`.

## Testing

- The testing framework is **`pytest`** with `pytest-django`.
- **`factory-boy`** is used to create model instances for tests (see `tests/factories/`).
- Tests are organized within each app's `tests` directory.
- There are tests for models, API serializers, and views.
- Management commands exist to populate the database with sample data for development and testing (e.g., `produto_create_all`).
