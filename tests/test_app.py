def test_forside_svarer_200(client):
    svar = client.get("/")
    assert svar.status_code == 200


def test_flask_cli_finner_appen():
    # Samme oppslag som `flask --app app run` gjør (E1-S01).
    from flask.cli import ScriptInfo

    app = ScriptInfo(app_import_path="app").load_app()
    assert app.test_client().get("/").status_code == 200
