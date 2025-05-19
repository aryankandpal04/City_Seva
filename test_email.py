import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys

def send_test_email(recipient_email, smtp_server, smtp_port, username, password, use_tls=True):
    """Send a simple test email with vibrant colors to troubleshoot email clients"""
    
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'CitySeva - Color Test Email'
    msg['From'] = username
    msg['To'] = recipient_email
    
    # Create the plain text version
    text = """
    This is a test email from CitySeva.
    If you're seeing this text, your email client doesn't support HTML emails.
    """
    
    # Create the HTML version with different color approaches
    html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>CitySeva Color Test</title>
    </head>
    <body bgcolor="#ffffff">
        <table width="100%" bgcolor="#f0f8ff" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td align="center" valign="top" style="padding: 20px;">
                    <table width="600" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td align="center" bgcolor="#00bfff" height="80">
                                <font color="#ffffff" size="5" face="Arial, sans-serif"><b>CitySeva Color Test</b></font>
                            </td>
                        </tr>
                        <tr>
                            <td align="left" bgcolor="#ffffff" style="padding: 20px; border: 1px solid #e0f7fa;">
                                <h2>Testing Different Color Methods</h2>
                                
                                <h3>1. Using bgcolor HTML attribute:</h3>
                                <table width="100%" cellpadding="10" cellspacing="0" border="0">
                                    <tr bgcolor="#00bfff">
                                        <td><font color="#ffffff">This row uses bgcolor attribute (skyblue)</font></td>
                                    </tr>
                                </table>
                                <br />
                                
                                <h3>2. Using font color attribute:</h3>
                                <font color="#00bfff" size="4">This text uses font color attribute (skyblue)</font><br />
                                <br />
                                
                                <h3>3. Using style attribute:</h3>
                                <div style="background-color: #00bfff; color: white; padding: 10px;">
                                    This div uses style attribute (skyblue background)
                                </div>
                                <br />
                                
                                <h3>4. With !important:</h3>
                                <div style="background-color: #00bfff !important; color: white !important; padding: 10px;">
                                    This div uses !important (skyblue background)
                                </div>
                                <br />
                                
                                <h3>5. Named colors:</h3>
                                <table width="100%" cellpadding="10" cellspacing="0" border="0">
                                    <tr bgcolor="skyblue">
                                        <td><font color="white">This uses named color skyblue</font></td>
                                    </tr>
                                </table>
                                <br />
                                
                                <h3>6. Basic table with border:</h3>
                                <table width="100%" cellpadding="5" cellspacing="0" border="1" bordercolor="#00bfff">
                                    <tr>
                                        <td><font color="#00bfff">Simple bordered table</font></td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" bgcolor="#e0f7fa" height="50">
                                <font color="#0288d1" size="2">CitySeva Email Test</font>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Attach parts to message
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Setup SMTP server connection
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        # Login if credentials provided
        if username and password:
            server.login(username, password)
        
        # Send the email
        server.sendmail(username, recipient_email, msg.as_string())
        server.quit()
        
        print(f"Test email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) < 6:
        print("Usage: python test_email.py recipient_email smtp_server smtp_port username password [use_tls(0/1)]")
        print("Example: python test_email.py test@example.com smtp.gmail.com 587 your_email@gmail.com your_password 1")
        sys.exit(1)
    
    # Get arguments
    recipient = sys.argv[1]
    smtp_server = sys.argv[2]
    smtp_port = int(sys.argv[3])
    username = sys.argv[4]
    password = sys.argv[5]
    
    # Get optional TLS setting
    use_tls = True
    if len(sys.argv) > 6:
        use_tls = bool(int(sys.argv[6]))
    
    # Send the test email
    send_test_email(recipient, smtp_server, smtp_port, username, password, use_tls) 