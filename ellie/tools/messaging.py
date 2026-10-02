"""Messaging and automation tools for WhatsApp via Ellie."""
import time
import logging
import urllib.parse
import webbrowser
from ellie.tools import register

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.PAUSE = 0.5  # Crucial for reliability during automation
except ImportError:
    logger.warning("pyautogui not installed; messaging tools may fail.")

def send_whatsapp(step: dict) -> str:
    """
    Prepare a WhatsApp message to be sent.
    Flow:
    1. Construct WhatsApp Web URL
    2. Open in browser
    3. Wait for page load
    4. If contact name provided, use pyautogui to search and select contact
    5. Type the message
    6. Return confirmation prompt (DO NOT SEND YET)
    """
    try:
        number = step.get('number', '')
        contact_name = step.get('name', '')
        message = step.get('message', '')
        
        if not message:
            return "Error: No message content provided."

        if number:
            url = f"https://web.whatsapp.com/send?phone={number}"
        else:
            url = "https://web.whatsapp.com/"
        
        webbrowser.open(url)
        time.sleep(5) # Wait for page load
        
        if not number and contact_name:
            # Assuming search bar shortcut (ctrl+alt+/) or UI layout
            pyautogui.hotkey('ctrl', 'alt', '/')
            time.sleep(1)
            pyautogui.write(contact_name, interval=0.02)
            time.sleep(2)
            pyautogui.press('enter')
            time.sleep(2)
        
        # Type the actual message
        pyautogui.write(message, interval=0.02)
        
        return "Message typed. Awaiting confirmation to send."
    except Exception as e:
        logger.error(f"Error in send_whatsapp: {e}")
        return f"Error in send_whatsapp: {e}"

def confirm_and_send(step: dict) -> str:
    """Confirm and send the typed WhatsApp message."""
    try:
        pyautogui.press('enter')
        return "Message sent!"
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return f"Error sending message: {e}"

def await_confirmation(step: dict) -> str:
    """Return the prompt text for confirmation flow."""
    return step.get('prompt', "Are you sure you want to send this message?")

def search_contact(step: dict) -> str:
    """Search for a contact in WhatsApp Web."""
    try:
        contact_name = step.get('name')
        if not contact_name:
            return "Error: No contact name provided."
        
        pyautogui.hotkey('ctrl', 'alt', '/')
        time.sleep(1)
        pyautogui.write(contact_name, interval=0.02)
        time.sleep(2)
        pyautogui.press('enter')
        return f"Opened chat with {contact_name}"
    except Exception as e:
        logger.error(f"Error searching contact: {e}")
        return f"Error searching contact: {e}"

# Register messaging tools
register('send_whatsapp', send_whatsapp)
register('confirm_and_send', confirm_and_send)
register('await_confirmation', await_confirmation)
register('search_contact', search_contact)
