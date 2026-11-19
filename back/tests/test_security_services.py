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
from email_service import send_email
from purchase_service.models import CartItem, CheckoutInput, ConfirmInput
from app import ArtistWorkInput
from security import hash_one_time_code, hash_password, hash_token, validate_request_origin, verify_password


class SecurityHelpersTests(unittest.TestCase):
    def test_local_smtp_can_send_without_starttls(self):
        smtp = MagicMock()
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp
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
        ), patch("email_service.smtplib.SMTP", return_value=smtp_context):
            send_email("artist@example.com", "Verify", "Your code is 123456")
        smtp.starttls.assert_not_called()
        smtp.send_message.assert_called_once()

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
            password="long-unique-password",
        )
        self.assertEqual(model.email, "user@example.com")

    def test_cart_does_not_accept_client_supplied_price(self):
        cart_item = CartItem(work_id=1, quantity=1, unit_price=1)
        self.assertFalse(hasattr(cart_item, "unit_price"))
        with self.assertRaises(Exception):
            CheckoutInput(items=[{"work_id": 1, "quantity": 1, "unit_price": 1}])

    def test_purchase_confirmation_requires_six_digit_code(self):
        self.assertEqual(ConfirmInput(code="042391").code, "042391")
        with self.assertRaises(Exception):
            ConfirmInput(code="not-a-code")


if __name__ == "__main__":
    unittest.main()
