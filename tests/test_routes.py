import re
import pytest

from tests.conftest import get_csrf


class TestAuthRoutes:
    def test_login_page_redirects_when_logged_in(self, auth_client):
        resp = auth_client.get("/login", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    def test_register_and_login(self, app_client):
        resp = app_client.post("/register", data={
            "username": "newuser",
            "password": "password1",
            "password2": "password1",
        }, follow_redirects=False)
        assert resp.status_code == 303

        resp = app_client.post("/login", data={
            "username": "newuser", "password": "password1"
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    def test_login_wrong_password(self, app_client):
        app_client.post("/register", data={
            "username": "user2", "password": "pass123", "password2": "pass123"
        })
        resp = app_client.post("/login", data={
            "username": "user2", "password": "wrongpass"
        })
        assert resp.status_code == 401

    def test_register_duplicate_username(self, app_client):
        data = {"username": "dup", "password": "pass123", "password2": "pass123"}
        app_client.post("/register", data=data)
        resp = app_client.post("/register", data=data)
        assert b"ya est" in resp.content  # "ya está en uso"

    def test_register_password_too_short(self, app_client):
        resp = app_client.post("/register", data={
            "username": "shortpw", "password": "123", "password2": "123"
        })
        assert b"6 caracteres" in resp.content

    def test_register_password_mismatch(self, app_client):
        resp = app_client.post("/register", data={
            "username": "mismatch", "password": "pass123", "password2": "different"
        })
        assert b"no coinciden" in resp.content

    def test_logout_clears_session(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/logout", data={"csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303
        # After logout, index should redirect to login
        resp = auth_client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "login" in resp.headers["location"]


class TestCalculatorRoutes:
    def test_index_requires_auth(self, app_client):
        resp = app_client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "login" in resp.headers["location"]

    def test_index_renders_when_logged_in(self, auth_client):
        resp = auth_client.get("/")
        assert resp.status_code == 200
        assert b"Calc3D" in resp.content

    def test_calculate_returns_result(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/calculate", data={
            "filament_weight": "100",
            "filament_price_kg": "20",
            "print_time": "2",
            "printer_watts": "100",
            "electricity_rate": "0.15",
            "other_costs": "0",
            "quantity": "1",
            "multiplier_preset": "2",
            "csrf_token": csrf,
        })
        assert resp.status_code == 200
        assert b"Resultado" in resp.content or b"result" in resp.content.lower()

    def test_add_and_delete_printer(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/printers/add", data={
            "name": "Ender 3",
            "watts": "200",
            "purchase_price": "300",
            "lifespan_years": "5",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303

    def test_clear_history(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/calculate", data={
            "filament_weight": "50", "filament_price_kg": "20", "print_time": "1",
            "printer_watts": "100", "electricity_rate": "0.15", "other_costs": "0",
            "quantity": "1", "multiplier_preset": "2", "csrf_token": csrf,
        })
        resp = auth_client.post("/clear-history", data={"csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303


class TestCatalogRoutes:
    def test_catalog_page(self, auth_client):
        resp = auth_client.get("/catalog")
        assert resp.status_code == 200

    def test_add_and_list_piece(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/catalog/add", data={"name": "Pieza test", "csrf_token": csrf})
        resp = auth_client.get("/catalog")
        assert b"Pieza test" in resp.content

    def test_edit_piece(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/catalog/add", data={"name": "Original", "csrf_token": csrf})
        resp = auth_client.get("/catalog")
        m = re.search(r'/catalog/delete/(\d+)', resp.text)
        assert m, "Piece ID not found"
        piece_id = m.group(1)
        resp = auth_client.post(f"/catalog/edit/{piece_id}",
                                data={"name": "Editada", "csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303
        resp = auth_client.get("/catalog")
        assert b"Editada" in resp.content

    def test_delete_piece(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/catalog/add", data={"name": "A borrar", "csrf_token": csrf})
        resp = auth_client.get("/catalog")
        m = re.search(r'/catalog/delete/(\d+)', resp.text)
        assert m, "Delete URL not found"
        piece_id = m.group(1)
        resp = auth_client.post(f"/catalog/delete/{piece_id}",
                                data={"csrf_token": csrf}, follow_redirects=False)
        assert resp.status_code == 303


class TestFilamentRoutes:
    def test_filaments_page(self, auth_client):
        resp = auth_client.get("/filaments")
        assert resp.status_code == 200

    def test_add_filament(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/filaments/add", data={
            "brand": "Polymaker",
            "material": "PLA",
            "color": "Black",
            "weight_total_g": "1000",
            "price_per_kg": "22",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303

    def test_edit_filament(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/filaments/add", data={
            "brand": "Bambu", "material": "PLA", "color": "Red",
            "weight_total_g": "1000", "price_per_kg": "30", "csrf_token": csrf,
        })
        resp = auth_client.get("/filaments")
        m = re.search(r'/filaments/delete/(\d+)', resp.text)
        assert m, "Filament ID not found"
        fid = m.group(1)
        resp = auth_client.post(f"/filaments/edit/{fid}", data={
            "brand": "Bambu", "material": "PETG", "color": "Red",
            "weight_total_g": "1000", "weight_remaining_g": "1000",
            "price_per_kg": "32", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303


class TestQuoteRoutes:
    def test_quotes_page(self, auth_client):
        resp = auth_client.get("/quotes")
        assert resp.status_code == 200

    def test_add_quote_redirects_to_detail(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={
            "client_name": "Cliente Test", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert "/quotes/" in resp.headers["location"]

    def test_quote_detail_page(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Ana", "csrf_token": csrf},
                                follow_redirects=False)
        quote_url = resp.headers["location"]
        resp = auth_client.get(quote_url)
        assert resp.status_code == 200
        assert b"Ana" in resp.content

    def test_add_item_to_quote(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Bob", "csrf_token": csrf},
                                follow_redirects=False)
        quote_url = resp.headers["location"]
        quote_id = quote_url.rstrip("/").split("/")[-1]

        resp = auth_client.post(f"/quotes/{quote_id}/add-item", data={
            "description": "Pieza X", "quantity": "2", "unit_price": "15.0",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303

    def test_delete_item_from_quote(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Carl", "csrf_token": csrf},
                                follow_redirects=False)
        quote_id = resp.headers["location"].rstrip("/").split("/")[-1]
        auth_client.post(f"/quotes/{quote_id}/add-item", data={
            "description": "Pieza Y", "quantity": "1", "unit_price": "10.0",
            "csrf_token": csrf,
        })
        resp = auth_client.get(f"/quotes/{quote_id}")
        m = re.search(r'/quotes/\d+/delete-item/(\d+)', resp.text)
        assert m, "Delete item URL not found"
        item_id = m.group(1)
        resp = auth_client.post(f"/quotes/{quote_id}/delete-item/{item_id}",
                                data={"csrf_token": csrf}, follow_redirects=False)
        assert resp.status_code == 303

    def test_update_quote_status(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Carlo", "csrf_token": csrf},
                                follow_redirects=False)
        quote_id = resp.headers["location"].rstrip("/").split("/")[-1]
        resp = auth_client.post(f"/quotes/{quote_id}/update-status",
                                data={"status": "enviado", "csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303

    def test_generate_and_revoke_token(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Dana", "csrf_token": csrf},
                                follow_redirects=False)
        quote_id = resp.headers["location"].rstrip("/").split("/")[-1]

        auth_client.post(f"/quotes/{quote_id}/generate-token",
                         data={"csrf_token": csrf}, follow_redirects=False)
        resp = auth_client.get(f"/quotes/{quote_id}")
        assert b"p/" in resp.content  # public URL shown

        auth_client.post(f"/quotes/{quote_id}/revoke-token",
                         data={"csrf_token": csrf}, follow_redirects=False)
        resp = auth_client.get(f"/quotes/{quote_id}")
        assert b"Generar link" in resp.content or b"generate" in resp.content.lower()

    def test_delete_quote(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Temp", "csrf_token": csrf},
                                follow_redirects=False)
        quote_id = resp.headers["location"].rstrip("/").split("/")[-1]
        resp = auth_client.post(f"/quotes/delete/{quote_id}",
                                data={"csrf_token": csrf}, follow_redirects=False)
        assert resp.status_code == 303


class TestClientRoutes:
    def test_clients_page(self, auth_client):
        resp = auth_client.get("/clients")
        assert resp.status_code == 200

    def test_add_client(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/clients/add", data={"name": "María", "csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303
        resp = auth_client.get("/clients")
        assert b"Mar" in resp.content

    def test_edit_client(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/clients/add", data={"name": "Original Client", "csrf_token": csrf})
        resp = auth_client.get("/clients")
        m = re.search(r'/clients/delete/(\d+)', resp.text)
        assert m, "Client ID not found"
        cid = m.group(1)
        resp = auth_client.post(f"/clients/edit/{cid}",
                                data={"name": "Editado", "csrf_token": csrf},
                                follow_redirects=False)
        assert resp.status_code == 303

    def test_delete_client(self, auth_client):
        csrf = get_csrf(auth_client)
        auth_client.post("/clients/add", data={"name": "A borrar", "csrf_token": csrf})
        resp = auth_client.get("/clients")
        m = re.search(r'/clients/delete/(\d+)', resp.text)
        assert m, "Delete URL not found"
        cid = m.group(1)
        resp = auth_client.post(f"/clients/delete/{cid}",
                                data={"csrf_token": csrf}, follow_redirects=False)
        assert resp.status_code == 303


class TestDashboardRoutes:
    def test_dashboard_page(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.status_code == 200


class TestSettingsRoutes:
    def test_settings_page(self, auth_client):
        resp = auth_client.get("/settings")
        assert resp.status_code == 200

    def test_update_settings(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/settings/update", data={
            "business_name": "Mi Negocio",
            "currency": "USD",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303
        resp = auth_client.get("/settings")
        assert b"Mi Negocio" in resp.content


class TestPublicQuote:
    def test_invalid_token_returns_404(self, app_client):
        resp = app_client.get("/p/nonexistenttoken")
        assert resp.status_code == 404

    def test_public_quote_view(self, auth_client):
        csrf = get_csrf(auth_client)
        resp = auth_client.post("/quotes/add", data={"client_name": "Eve", "csrf_token": csrf},
                                follow_redirects=False)
        quote_id = resp.headers["location"].rstrip("/").split("/")[-1]
        auth_client.post(f"/quotes/{quote_id}/update-status",
                         data={"status": "enviado", "csrf_token": csrf},
                         follow_redirects=False)
        auth_client.post(f"/quotes/{quote_id}/generate-token",
                         data={"csrf_token": csrf}, follow_redirects=False)

        resp = auth_client.get(f"/quotes/{quote_id}")
        content = resp.content.decode()
        m = re.search(r"/p/([A-Za-z0-9_-]+)", content)
        assert m, "Public URL not found in page"
        token = m.group(1)

        resp = auth_client.get(f"/p/{token}")
        assert resp.status_code == 200
        assert b"Eve" in resp.content
