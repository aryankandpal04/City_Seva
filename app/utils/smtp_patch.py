"""
Patch for flask_mailman SMTP backend to work with Python 3.12
"""
import importlib
import types
import inspect
import logging
import socket

logger = logging.getLogger(__name__)

def patch_flask_mailman():
    """
    Patch the Flask-Mailman SMTP backend to fix compatibility issues with Python 3.12
    by removing keyfile and certfile parameters that cause errors.
    """
    try:
        # Import the SMTP backend module
        from flask_mailman.backends import smtp
        
        # Get the original open method
        original_open = smtp.EmailBackend.open
        
        # Define a new open method that wraps the original but fixes the starttls call
        def patched_open(self):
            """
            Patched version of smtp.EmailBackend.open that handles
            compatibility with Python 3.12
            """
            if self.connection:
                # Nothing to do if the connection is already open.
                return False

            # Use empty connection_params - don't rely on local_hostname
            connection_params = {}
            
            # Only add timeout if it exists
            if hasattr(self, 'timeout') and self.timeout is not None:
                connection_params['timeout'] = self.timeout
            
            try:
                self.connection = self.connection_class(
                    self.host, self.port, **connection_params)

                # TLS/SSL are mutually exclusive, so only attempt TLS over
                # non-secure connections.
                if hasattr(self, 'use_ssl') and hasattr(self, 'use_tls'):
                    if not self.use_ssl and self.use_tls:
                        try:
                            # Patched starttls call - no params
                            self.connection.starttls()
                        except Exception as e:
                            logger.warning(
                                f"Failed to establish a TLS connection: {e}. "
                                "Attempting to continue without TLS."
                            )
                
                if hasattr(self, 'username') and hasattr(self, 'password'):
                    if self.username and self.password:
                        self.connection.login(self.username, self.password)
                
                return True
            except Exception as e:
                logger.error(f"Error connecting to SMTP server: {e}")
                if hasattr(self, 'fail_silently') and self.fail_silently:
                    return False
                raise
        
        # Replace the original method with our patched version
        smtp.EmailBackend.open = patched_open
        
        logger.info("Successfully patched Flask-Mailman SMTP backend for Python 3.12 compatibility")
        return True
    except Exception as e:
        logger.error(f"Failed to patch Flask-Mailman SMTP backend: {e}")
        return False 