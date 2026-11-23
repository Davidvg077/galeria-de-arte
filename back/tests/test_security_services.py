import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "back"
sys.path.insert(0, str(BACKEND / "services"))
sys.path.insert(0, str(BACKEND / "services" / "works-service"))

from auth_service.models import RegisterRequest
from auth_service.controllers import routes as auth_routes
from email_service import EmailConfigurationError, send_email
from purchase_service.models import CartItem, CheckoutInput, ConfirmInput
from app import ArtistWorkInput
from security import hash_one_time_code, hash_password, hash_token, validate_request_origin, verify_password


class SecurityHelpersTests(unittest.TestCase):
    def test_email_delivery_is_disabled_even_with_smtp_configuration(self):
        with patch.dict(
            "os.environ",
            {
                "SMTP_HOST": "mailpit",
                "SMTP_PORT": "1025",
                "SMTP_FROM": "no-reply@gart-gallery.local",
                "SMTP_STARTTLS": "false",
                "SMTP_USE_SSL": "false",
            },
            clear=False,
        ), self.assertRaisesRegex(EmailConfigurationError, "Modo demostración"):
            send_email("artist@example.com", "Verify", "Your code is 123456")

    def test_password_hash_is_salted_and_verified(self):
        first = hash_password("Correct Horse Battery 42!")
        second = hash_password("Correct Horse Battery 42!")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("Correct Horse Battery 42!", first))
        self.assertFalse(verify_password("wrong password", first))
        self.assertFalse(verify_password("admin123", "admin123"))

    def test_session_and_otp_values_are_only_stored_as_digests(self):
        token = "random-session-or-otp-value"
        self.assertNotEqual(token, hash_token(token))
        self.assertEqual(hash_token(token), hash_token(token))
        with patch.dict("os.environ", {"TOKEN_PEPPER": "first-pepper-value-that-is-at-least-32-chars"}):
            first = hash_one_time_code("042391")
        with patch.dict("os.environ", {"TOKEN_PEPPER": "second-pepper-value-that-is-at-least-32-chars"}):
            second = hash_one_time_code("042391")
        self.assertNotEqual(first, second)

    def test_browser_mutation_rejects_cross_origin(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "https",
                "path": "/api/auth/login",
                "headers": [
                    (b"host", b"gallery.example"),
                    (b"origin", b"https://attacker.example"),
                ],
                "query_string": b"",
                "server": ("gallery.example", 443),
                "client": ("127.0.0.1", 50000),
            }
        )
        with self.assertRaises(HTTPException) as raised:
            validate_request_origin(request)
        self.assertEqual(raised.exception.status_code, 403)

    def test_browser_mutation_accepts_forwarded_host_with_port(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "path": "/api/auth/logout",
                "headers": [
                    (b"host", b"auth-service:3003"),
                    (b"origin", b"http://127.0.0.1:8080"),
                    (b"x-forwarded-host", b"127.0.0.1:8080"),
                    (b"x-forwarded-proto", b"http"),
                ],
                "query_string": b"",
                "server": ("auth-service", 3003),
                "client": ("127.0.0.1", 50000),
            }
        )
        validate_request_origin(request)

    def test_non_browser_mutation_without_origin_is_allowed(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "http",
                "path": "/api/auth/login",
                "headers": [(b"host", b"localhost:8080")],
                "query_string": b"",
                "server": ("localhost", 8080),
                "client": ("127.0.0.1", 50000),
            }
        )
        validate_request_origin(request)


class RequestModelsTests(unittest.TestCase):
    def test_artist_work_input_limits_publication_controls(self):
        work = ArtistWorkInput(title="Mi obra", status="published")
        self.assertEqual(work.status, "published")
        with self.assertRaises(Exception):
            ArtistWorkInput(
                title="Mi obra",
                status="published",
                owner_user_id=99,
                artist_id=1,
                available=False,
                moderation_status="rejected",
            )

    def test_registration_requires_strong_password_and_email(self):
        with self.assertRaises(Exception):
            RegisterRequest(username="gallery_user", email="user@example.com", password="short")
        model = RegisterRequest(
            username="gallery_user",
            email="user@example.com",
            phone="+573001234567",
            password="long-unique-password",
            confirm_password="long-unique-password",
        )
        self.assertEqual(model.email, "user@example.com")
        self.assertNotIn("role", model.model_dump())
        with self.assertRaises(Exception):
            RegisterRequest(
                username="gallery_user",
                email="user@example.com",
                phone="+573001234567",
                password="long-unique-password",
                confirm_password="different-password",
            )

    def test_registration_ignores_client_supplied_roles(self):
        for role in ("ARTISTA", "ADMIN"):
            with self.subTest(role=role):
                model = RegisterRequest(
                    username="gallery_user",
                    email="user@example.com",
                    phone="+573001234567",
                    password="long-unique-password",
                    confirm_password="long-unique-password",
                    role=role,
                )
                self.assertNotIn("role", model.model_dump())

    def test_cart_does_not_accept_client_supplied_price(self):
        cart_item = CartItem(work_id=1, quantity=1, unit_price=1)
        self.assertFalse(hasattr(cart_item, "unit_price"))
        with self.assertRaises(Exception):
            CheckoutInput(items=[{"work_id": 1, "quantity": 1, "unit_price": 1}])

    def test_purchase_confirmation_requires_six_digit_code(self):
        self.assertEqual(ConfirmInput(code="042391").code, "042391")
        with self.assertRaises(Exception):
            ConfirmInput(code="not-a-code")


class DemoFlowTests(unittest.TestCase):
    def test_email_otp_is_demo_only_and_database_stores_its_hash(self):
        connection_context = MagicMock()
        db = connection_context.__enter__.return_value
        db.execute.return_value.fetchone.return_value = None
        user = {"id": 7, "email": "user@example.com", "email_verified": False}
        with patch.object(auth_routes, "connection", return_value=connection_context), \
             patch.object(auth_routes, "_new_email_code", return_value="042391"), \
             patch.object(auth_routes, "hash_one_time_code", return_value="stored-digest"):
            result = auth_routes.request_email_verification(user)

        self.assertEqual(result["mode"], "demo")
        self.assertEqual(result["demo_code"], "042391")
        self.assertIn("Modo demostración", result["message"])
        self.assertIn("stored-digest", db.execute.call_args_list[-1].args[1])

    def test_phone_otp_uses_demo_mode_and_artist_role_requires_both_verifications(self):
        context = MagicMock()
        context.__enter__.return_value.execute.return_value.fetchone.return_value = None
        with patch.object(auth_routes, "connection", return_value=context), \
             patch.object(auth_routes, "_new_email_code", return_value="314159"), \
             patch.object(auth_routes, "hash_one_time_code", return_value="phone-digest"):
            result = auth_routes.request_phone_verification(
                {"id": 8, "phone": "+573001234567", "phone_verified": False}
            )
        self.assertEqual(result["mode"], "demo")
        self.assertEqual(result["demo_code"], "314159")
        self.assertIn("SMS", result["message"])

        for user in (
            {"id": 8, "role": "VISITANTE", "email_verified": False, "phone_verified": True, "permissions": []},
            {"id": 8, "role": "VISITANTE", "email_verified": True, "phone_verified": False, "permissions": []},
        ):
            with self.subTest(user=user), self.assertRaises(HTTPException) as raised:
                auth_routes.request_artist_role(user)
            self.assertEqual(raised.exception.status_code, 403)

    def test_verified_visitor_can_be_promoted_only_to_artist(self):
        connection_context = MagicMock()
        db = connection_context.__enter__.return_value
        db.execute.return_value.fetchone.return_value = {
            "id": 9,
            "username": "verified_user",
            "email": "user@example.com",
            "phone": "+573001234567",
            "email_verified": True,
            "phone_verified": True,
            "role": "ARTISTA",
            "permissions": ["works:read", "works:submit"],
            "active": True,
        }
        user = {
            "id": 9,
            "role": "VISITANTE",
            "email_verified": True,
            "phone_verified": True,
            "permissions": ["works:read"],
        }
        with patch.object(auth_routes, "connection", return_value=connection_context):
            result = auth_routes.request_artist_role(user)

        self.assertEqual(result["user"]["role"], "ARTISTA")
        self.assertIn("works:submit", result["user"]["permissions"])
        self.assertIn("SET role = 'ARTISTA'", db.execute.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
