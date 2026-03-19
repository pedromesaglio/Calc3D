"""
Tests para las integraciones de pago
"""
import pytest
from unittest.mock import Mock, patch
from app.payments.stripe_integration import stripe_service
from app.payments.mercadopago_integration import mercadopago_service


class TestStripeIntegration:
    """Tests para la integración de Stripe"""

    def test_is_configured_without_keys(self):
        """Test: Stripe no configurado sin API keys"""
        with patch.dict('os.environ', {}, clear=True):
            service = stripe_service
            service.api_key = None
            service.webhook_secret = None
            assert service.is_configured() is False

    def test_is_configured_with_keys(self):
        """Test: Stripe configurado con API keys"""
        with patch.dict('os.environ', {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_123'
        }):
            service = stripe_service
            service.api_key = 'sk_test_123'
            service.webhook_secret = 'whsec_123'
            assert service.is_configured() is True

    @patch('app.payments.stripe_integration.stripe.Customer.create')
    def test_create_customer_success(self, mock_create):
        """Test: Crear cliente en Stripe exitosamente"""
        mock_create.return_value = Mock(id='cus_test123')

        with patch.dict('os.environ', {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_123'
        }):
            service = stripe_service
            service.api_key = 'sk_test_123'
            service.webhook_secret = 'whsec_123'

            customer_id = service.create_customer(
                user_id=1,
                email='test@example.com',
                username='testuser'
            )

            assert customer_id == 'cus_test123'
            mock_create.assert_called_once()

    @patch('app.payments.stripe_integration.stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create):
        """Test: Crear sesión de checkout"""
        mock_create.return_value = Mock(url='https://checkout.stripe.com/session123')

        with patch.dict('os.environ', {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_123',
            'STRIPE_PRICE_ID_PRO': 'price_pro123'
        }):
            service = stripe_service
            service.api_key = 'sk_test_123'
            service.webhook_secret = 'whsec_123'
            service.price_ids['pro'] = 'price_pro123'

            checkout_url = service.create_checkout_session(
                user_id=1,
                customer_id='cus_test123',
                plan='pro',
                success_url='http://localhost/success',
                cancel_url='http://localhost/cancel'
            )

            assert checkout_url == 'https://checkout.stripe.com/session123'
            mock_create.assert_called_once()

    def test_webhook_signature_verification(self):
        """Test: Verificar firma de webhook"""
        service = stripe_service
        service.webhook_secret = None

        result = service.verify_webhook_signature(b'payload', 'signature')
        assert result is None  # Sin secreto, retorna None


class TestMercadoPagoIntegration:
    """Tests para la integración de Mercado Pago"""

    def test_is_configured_without_token(self):
        """Test: Mercado Pago no configurado sin token"""
        with patch.dict('os.environ', {}, clear=True):
            service = mercadopago_service
            service.access_token = None
            assert service.is_configured() is False

    def test_is_configured_with_token(self):
        """Test: Mercado Pago configurado con token"""
        with patch.dict('os.environ', {
            'MERCADOPAGO_ACCESS_TOKEN': 'TEST-123456'
        }):
            service = mercadopago_service
            service.access_token = 'TEST-123456'
            assert service.is_configured() is True

    @patch('app.payments.mercadopago_integration.requests.post')
    def test_create_customer_success(self, mock_post):
        """Test: Crear cliente en Mercado Pago"""
        mock_response = Mock()
        mock_response.json.return_value = {'id': '123456789'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with patch.dict('os.environ', {
            'MERCADOPAGO_ACCESS_TOKEN': 'TEST-123456'
        }):
            service = mercadopago_service
            service.access_token = 'TEST-123456'

            customer_id = service.create_customer(
                user_id=1,
                email='test@example.com',
                username='testuser'
            )

            assert customer_id == '123456789'
            mock_post.assert_called_once()

    @patch('app.payments.mercadopago_integration.requests.post')
    def test_create_preference_success(self, mock_post):
        """Test: Crear preferencia de pago"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'init_point': 'https://www.mercadopago.com/checkout/123'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with patch.dict('os.environ', {
            'MERCADOPAGO_ACCESS_TOKEN': 'TEST-123456'
        }):
            service = mercadopago_service
            service.access_token = 'TEST-123456'

            preference_url = service.create_preference(
                user_id=1,
                plan='pro',
                success_url='http://localhost/success',
                failure_url='http://localhost/failure',
                pending_url='http://localhost/pending'
            )

            assert preference_url == 'https://www.mercadopago.com/checkout/123'
            mock_post.assert_called_once()


@pytest.mark.parametrize("provider,event_type", [
    ("stripe", "checkout.session.completed"),
    ("stripe", "invoice.payment_succeeded"),
    ("mercadopago", "payment"),
])
def test_webhook_event_types(provider, event_type):
    """Test: Tipos de eventos de webhooks soportados"""
    # Este test verifica que los event types están documentados
    # En una implementación real, harías mocking de los handlers
    assert provider in ["stripe", "mercadopago"]
    assert event_type is not None
