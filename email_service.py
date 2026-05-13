import requests
from flask import current_app


def send_verification_email(recipient_email, recipient_name, verification_url):
    api_key = current_app.config["BREVO_API_KEY"]
    sender_email = current_app.config["BREVO_SENDER_EMAIL"]
    sender_name = current_app.config["BREVO_SENDER_NAME"]

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #1a73e8; padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0;">Delpy EDU</h1>
        </div>
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
            <h2 style="color: #333;">Benvenuto, {recipient_name}!</h2>
            <p style="color: #555; line-height: 1.6;">
                Grazie per aver registrato la tua scuola su Delpy EDU.
                Per completare la registrazione, verifica il tuo indirizzo email cliccando sul pulsante qui sotto.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}"
                   style="background: #1a73e8; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold;">
                    Verifica Email
                </a>
            </div>
            <p style="color: #888; font-size: 13px;">
                Il link scade tra 24 ore. Se non hai richiesto la registrazione, ignora questa email.
            </p>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
            <p style="color: #aaa; font-size: 12px; text-align: center;">
                Delpy EDU &mdash; Piattaforma educativa per le scuole
            </p>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient_email, "name": recipient_name}],
        "subject": "Verifica la tua email - Delpy EDU",
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers=headers,
        timeout=10,
    )
    return response.status_code == 201


def send_welcome_email(recipient_email, recipient_name, school_name, temp_password):
    api_key = current_app.config["BREVO_API_KEY"]
    sender_email = current_app.config["BREVO_SENDER_EMAIL"]
    sender_name = current_app.config["BREVO_SENDER_NAME"]
    base_url = current_app.config["BASE_URL"]

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #1a73e8; padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0;">Delpy EDU</h1>
        </div>
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">
            <h2 style="color: #333;">Ciao, {recipient_name}!</h2>
            <p style="color: #555; line-height: 1.6;">
                Il tuo account su <strong>Delpy EDU</strong> per la scuola <strong>{school_name}</strong> è stato creato.
            </p>
            <div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 20px; margin: 20px 0;">
                <p style="margin: 0 0 8px 0; color: #555;"><strong>Email:</strong> {recipient_email}</p>
                <p style="margin: 0; color: #555;"><strong>Password temporanea:</strong> {temp_password}</p>
            </div>
            <p style="color: #555;">Accedi e cambia la password al primo accesso.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{base_url}/login"
                   style="background: #1a73e8; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold;">
                    Accedi ora
                </a>
            </div>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
            <p style="color: #aaa; font-size: 12px; text-align: center;">
                Delpy EDU &mdash; Piattaforma educativa per le scuole
            </p>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient_email, "name": recipient_name}],
        "subject": f"Benvenuto su Delpy EDU - {school_name}",
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers=headers,
        timeout=10,
    )
    return response.status_code == 201
