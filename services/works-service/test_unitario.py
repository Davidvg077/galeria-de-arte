import unittest
from pydantic import ValidationError
from app import WorkInput


class TestWorkInput(unittest.TestCase):

    def test_titulo_vacio_rechazado(self):
        with self.assertRaises(ValidationError):
            WorkInput(title="")

    def test_precio_negativo_rechazado(self):
        with self.assertRaises(ValidationError):
            WorkInput(
                title="Paisaje",
                price=-100
            )

    def test_obra_valida_aceptada(self):
        obra = WorkInput(
            title="Paisaje de prueba",
            price=100000
        )

        self.assertEqual(obra.title, "Paisaje de prueba")
        self.assertEqual(obra.price, 100000)


if __name__ == "__main__":
    unittest.main()