import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        # Load from env vars for security
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')

    def send_retention_email(self, from_email, to_email, subject, message):
        """Send real retention email using SMTP."""
        if not self.smtp_user or not self.smtp_pass:
            print("ERROR: SMTP credentials not provided in .env file.")
            print(f"MOCK SEND FAIL -> To: {to_email}\nSubject: {subject}")
            return {
                'success': False, 
                'error': 'Real email failed: SMTP credentials (SMTP_USER/SMTP_PASS) are missing in the .env file. Check the .env.example file for instructions.'
            }

        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Use TLS for security
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            
            # Send
            server.send_message(msg)
            server.quit()
            
            print(f"Email successfully sent to {to_email}")
            return {'success': True}
            
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def generate_email_content(self, customer_name, risk_level, discount_code=None):
        """Auto-generate email based on risk level."""
        subjects = {
            'High': "We Miss You! Exclusive Offer for You Inside 🎁",
            'Medium': "Special Gift Just for You! ✨",
            'Low': "Tips to Get the Most Out of ChurnShield AI"
        }
        
        bodies = {
            'High': f"Hello {customer_name},\n\nWe noticed you haven’t shopped with us in a while and we’d love to have you back! Use code {discount_code or 'BACK20'} for 20% OFF your next order.\n\nRegards,\nChurnShield AI Team",
            'Medium': f"Hello {customer_name},\n\nYou have points waiting to be used! Use code {discount_code or 'LOYAL10'} for 10% OFF your next purchase as a thank you for being with us.\n\nBest,\nChurnShield AI Team",
            'Low': f"Hello {customer_name},\n\nHope you're enjoying our products! We've added some new arrivals just for you. Check them out on our store.\n\nCheers,\nChurnShield AI Team"
        }
        
        return subjects.get(risk_level, "Update from ChurnShield AI"), bodies.get(risk_level, f"Hello {customer_name}, thanks for being a customer!")

if __name__ == "__main__":
    es = EmailService()
