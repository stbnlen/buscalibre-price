"""Pruebas para los modelos de datos del tracker."""

import logging

import pytest

from tracker.models import Product


class TestProductCreation:
    """Pruebas para la creación de productos."""

    def test_creacion_correcta(self):
        """Se puede crear un producto correctamente."""
        product = Product(title="Test Book", price=100.0)
        assert product.title == "Test Book"
        assert product.price == 100.0

    def test_titulo_vacio_lanza_error(self):
        """Lanza ValueError si el título está vacío."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Product(title="", price=100.0)

    def test_titulo_solo_espacios_lanza_error(self):
        """Lanza ValueError si el título solo tiene espacios."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Product(title="   ", price=100.0)

    def test_precio_negativo_lanza_error(self):
        """Lanza ValueError si el precio es negativo."""
        with pytest.raises(ValueError, match="negative"):
            Product(title="Book", price=-10.0)

    def test_precio_cero_genera_warning(self, caplog):
        """Genera un warning si el precio es cero."""
        with caplog.at_level(logging.WARNING):
            Product(title="Free Book", price=0.0)
        assert "price of zero" in caplog.text


class TestProductEquality:
    """Pruebas para la igualdad y hashing de productos."""

    def test_igualdad_mismos_datos(self):
        """Dos productos con mismos datos son iguales."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        assert p1 == p2

    def test_desigualdad_distinto_titulo(self):
        """Productos con distinto título no son iguales."""
        p1 = Product(title="Book A", price=50.0)
        p2 = Product(title="Book B", price=50.0)
        assert p1 != p2

    def test_desigualdad_distinto_precio(self):
        """Productos con distinto precio no son iguales."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=60.0)
        assert p1 != p2

    def test_desigualdad_con_otro_tipo(self):
        """Producto no es igual a un objeto de otro tipo."""
        p = Product(title="Book", price=50.0)
        assert p != "Book"

    def test_hash_consistente(self):
        """El hash es consistente con la igualdad."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        assert hash(p1) == hash(p2)

    def test_usable_en_conjunto(self):
        """Los productos se pueden usar en conjuntos."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        p3 = Product(title="Other", price=30.0)
        s = {p1, p2, p3}
        assert len(s) == 2
