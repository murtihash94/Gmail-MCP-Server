"""Gmail MCP Server with FastMCP for Databricks Apps"""
from pathlib import Path
import os
import base64
import json
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.responses import FileResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

STATIC_DIR = Path(__file__).parent / "static"

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

# Configuration paths
CONFIG_DIR = Path.home() / '.gmail-mcp'
OAUTH_PATH = os.environ.get('GMAIL_OAUTH_PATH', CONFIG_DIR / 'gcp-oauth.keys.json')
CREDENTIALS_PATH = os.environ.get('GMAIL_CREDENTIALS_PATH', CONFIG_DIR / 'credentials.json')

# Create an MCP server
mcp = FastMCP("Gmail MCP Server on Databricks Apps")

# Global Gmail service
gmail_service = None


def get_gmail_service():
    """Get or create Gmail API service"""
    global gmail_service
    if gmail_service is not None:
        return gmail_service
    
    creds = None
    
    # Load credentials if they exist
    if Path(CREDENTIALS_PATH).exists():
        creds = Credentials.from_authorized_user_file(str(CREDENTIALS_PATH), SCOPES)
    
    # If credentials don't exist or are invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For Databricks Apps, we expect credentials to be pre-configured
            raise RuntimeError(
                "Gmail credentials not found. Please run authentication before deploying."
            )
        
        # Save credentials
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CREDENTIALS_PATH, 'w') as token:
            token.write(creds.to_json())
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service


def extract_email_content(message_part: Dict[str, Any]) -> Dict[str, str]:
    """Recursively extract email body content from MIME message parts"""
    text_content = ''
    html_content = ''
    
    # If the part has a body with data, process it
    if 'body' in message_part and 'data' in message_part['body']:
        content = base64.urlsafe_b64decode(message_part['body']['data']).decode('utf-8', errors='ignore')
        
        mime_type = message_part.get('mimeType', '')
        if mime_type == 'text/plain':
            text_content = content
        elif mime_type == 'text/html':
            html_content = content
    
    # Process nested parts
    if 'parts' in message_part:
        for part in message_part['parts']:
            result = extract_email_content(part)
            if result['text']:
                text_content += result['text']
            if result['html']:
                html_content += result['html']
    
    return {'text': text_content, 'html': html_content}


def extract_attachments(message_part: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract attachment information from message parts"""
    attachments = []
    
    filename = message_part.get('filename', '')
    if filename and 'body' in message_part and 'attachmentId' in message_part['body']:
        attachments.append({
            'id': message_part['body']['attachmentId'],
            'filename': filename,
            'mimeType': message_part.get('mimeType', 'application/octet-stream'),
            'size': message_part['body'].get('size', 0)
        })
    
    # Process nested parts
    if 'parts' in message_part:
        for part in message_part['parts']:
            attachments.extend(extract_attachments(part))
    
    return attachments


def create_message_with_attachment(to: List[str], subject: str, body: str,
                                   cc: Optional[List[str]] = None,
                                   bcc: Optional[List[str]] = None,
                                   attachments: Optional[List[str]] = None) -> str:
    """Create a MIME message with optional attachments"""
    message = MIMEMultipart()
    message['to'] = ', '.join(to)
    message['subject'] = subject
    
    if cc:
        message['cc'] = ', '.join(cc)
    if bcc:
        message['bcc'] = ', '.join(bcc)
    
    # Add body
    message.attach(MIMEText(body, 'plain'))
    
    # Add attachments
    if attachments:
        for file_path in attachments:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Attachment not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={Path(file_path).name}'
            )
            message.attach(part)
    
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


# Tools

@mcp.tool()
def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    mimeType: str = "text/plain",
    htmlBody: Optional[str] = None,
    attachments: Optional[list[str]] = None
) -> str:
    """Send an email via Gmail
    
    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body content (plain text or used when htmlBody not provided)
        cc: List of CC recipients (optional)
        bcc: List of BCC recipients (optional)
        mimeType: Email content type (text/plain, text/html, or multipart/alternative)
        htmlBody: HTML version of email body (optional)
        attachments: List of file paths to attach (optional)
    """
    try:
        service = get_gmail_service()
        
        # Create message based on type
        if attachments or mimeType == 'multipart/alternative':
            raw = create_message_with_attachment(to, subject, body, cc, bcc, attachments)
        else:
            message = MIMEText(htmlBody if mimeType == 'text/html' and htmlBody else body, 
                             'html' if mimeType == 'text/html' else 'plain')
            message['to'] = ', '.join(to)
            message['subject'] = subject
            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return f"Email sent successfully! Message ID: {send_message['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def draft_email(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    mimeType: str = "text/plain",
    htmlBody: Optional[str] = None,
    attachments: Optional[list[str]] = None
) -> str:
    """Create a draft email in Gmail
    
    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body content
        cc: List of CC recipients (optional)
        bcc: List of BCC recipients (optional)
        mimeType: Email content type
        htmlBody: HTML version of email body (optional)
        attachments: List of file paths to attach (optional)
    """
    try:
        service = get_gmail_service()
        
        # Create message
        if attachments or mimeType == 'multipart/alternative':
            raw = create_message_with_attachment(to, subject, body, cc, bcc, attachments)
        else:
            message = MIMEText(htmlBody if mimeType == 'text/html' and htmlBody else body,
                             'html' if mimeType == 'text/html' else 'plain')
            message['to'] = ', '.join(to)
            message['subject'] = subject
            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw}}
        ).execute()
        
        return f"Draft created successfully! Draft ID: {draft['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def read_email(messageId: str) -> str:
    """Read the content of a specific email by ID
    
    Args:
        messageId: The ID of the email to read
    """
    try:
        service = get_gmail_service()
        message = service.users().messages().get(
            userId='me',
            id=messageId,
            format='full'
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        
        # Extract content
        content = extract_email_content(message['payload'])
        
        # Extract attachments
        attachments = extract_attachments(message['payload'])
        
        # Build response
        result = f"Subject: {headers.get('Subject', 'N/A')}\n"
        result += f"From: {headers.get('From', 'N/A')}\n"
        result += f"To: {headers.get('To', 'N/A')}\n"
        result += f"Date: {headers.get('Date', 'N/A')}\n\n"
        result += content['text'] if content['text'] else content['html']
        
        if attachments:
            result += f"\n\nAttachments ({len(attachments)}):\n"
            for att in attachments:
                size_kb = att['size'] / 1024
                result += f"- {att['filename']} ({att['mimeType']}, {size_kb:.0f} KB, ID: {att['id']})\n"
        
        return result
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def search_emails(query: str, maxResults: int = 10) -> str:
    """Search for emails using Gmail search syntax
    
    Args:
        query: Gmail search query (e.g., "from:example@example.com after:2024/01/01")
        maxResults: Maximum number of results to return (default: 10)
    """
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=maxResults
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return "No messages found."
        
        result = f"Found {len(messages)} message(s):\n\n"
        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            result += f"ID: {msg['id']}\n"
            result += f"Subject: {headers.get('Subject', 'N/A')}\n"
            result += f"From: {headers.get('From', 'N/A')}\n"
            result += f"Date: {headers.get('Date', 'N/A')}\n\n"
        
        return result
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def modify_email(
    messageId: str,
    addLabelIds: Optional[list[str]] = None,
    removeLabelIds: Optional[list[str]] = None
) -> str:
    """Modify labels on an email (move to folders, mark read/unread, etc.)
    
    Args:
        messageId: The ID of the email to modify
        addLabelIds: List of label IDs to add (optional)
        removeLabelIds: List of label IDs to remove (optional)
    """
    try:
        service = get_gmail_service()
        
        body = {}
        if addLabelIds:
            body['addLabelIds'] = addLabelIds
        if removeLabelIds:
            body['removeLabelIds'] = removeLabelIds
        
        message = service.users().messages().modify(
            userId='me',
            id=messageId,
            body=body
        ).execute()
        
        return f"Email modified successfully! Message ID: {message['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def delete_email(messageId: str) -> str:
    """Permanently delete an email
    
    Args:
        messageId: The ID of the email to delete
    """
    try:
        service = get_gmail_service()
        service.users().messages().delete(userId='me', id=messageId).execute()
        return f"Email deleted successfully! Message ID: {messageId}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def list_email_labels() -> str:
    """Retrieve all available Gmail labels (system and user-defined)"""
    try:
        service = get_gmail_service()
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        if not labels:
            return "No labels found."
        
        result = "Available labels:\n\n"
        for label in labels:
            result += f"ID: {label['id']}\n"
            result += f"Name: {label['name']}\n"
            result += f"Type: {label.get('type', 'user')}\n\n"
        
        return result
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def batch_modify_emails(
    messageIds: list[str],
    addLabelIds: Optional[list[str]] = None,
    removeLabelIds: Optional[list[str]] = None,
    batchSize: int = 50
) -> str:
    """Modify labels for multiple emails in efficient batches
    
    Args:
        messageIds: List of email IDs to modify
        addLabelIds: List of label IDs to add (optional)
        removeLabelIds: List of label IDs to remove (optional)
        batchSize: Number of emails to process in each batch (default: 50)
    """
    try:
        service = get_gmail_service()
        
        body = {'ids': messageIds}
        if addLabelIds:
            body['addLabelIds'] = addLabelIds
        if removeLabelIds:
            body['removeLabelIds'] = removeLabelIds
        
        service.users().messages().batchModify(userId='me', body=body).execute()
        
        return f"Successfully modified {len(messageIds)} email(s)"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def batch_delete_emails(messageIds: list[str], batchSize: int = 50) -> str:
    """Permanently delete multiple emails in efficient batches
    
    Args:
        messageIds: List of email IDs to delete
        batchSize: Number of emails to process in each batch (default: 50)
    """
    try:
        service = get_gmail_service()
        service.users().messages().batchDelete(
            userId='me',
            body={'ids': messageIds}
        ).execute()
        
        return f"Successfully deleted {len(messageIds)} email(s)"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def create_label(
    name: str,
    messageListVisibility: str = "show",
    labelListVisibility: str = "labelShow"
) -> str:
    """Create a new Gmail label
    
    Args:
        name: Name for the new label
        messageListVisibility: Message list visibility (show/hide)
        labelListVisibility: Label list visibility (labelShow/labelShowIfUnread/labelHide)
    """
    try:
        service = get_gmail_service()
        
        label = {
            'name': name,
            'messageListVisibility': messageListVisibility,
            'labelListVisibility': labelListVisibility
        }
        
        created_label = service.users().labels().create(
            userId='me',
            body=label
        ).execute()
        
        return f"Label created successfully!\nID: {created_label['id']}\nName: {created_label['name']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def update_label(
    id: str,
    name: Optional[str] = None,
    messageListVisibility: Optional[str] = None,
    labelListVisibility: Optional[str] = None
) -> str:
    """Update an existing Gmail label
    
    Args:
        id: ID of the label to update
        name: New name for the label (optional)
        messageListVisibility: Message list visibility (optional)
        labelListVisibility: Label list visibility (optional)
    """
    try:
        service = get_gmail_service()
        
        label = {}
        if name:
            label['name'] = name
        if messageListVisibility:
            label['messageListVisibility'] = messageListVisibility
        if labelListVisibility:
            label['labelListVisibility'] = labelListVisibility
        
        updated_label = service.users().labels().update(
            userId='me',
            id=id,
            body=label
        ).execute()
        
        return f"Label updated successfully!\nID: {updated_label['id']}\nName: {updated_label['name']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def delete_label(id: str) -> str:
    """Delete a Gmail label
    
    Args:
        id: ID of the label to delete
    """
    try:
        service = get_gmail_service()
        service.users().labels().delete(userId='me', id=id).execute()
        return f"Label deleted successfully! Label ID: {id}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def get_or_create_label(
    name: str,
    messageListVisibility: str = "show",
    labelListVisibility: str = "labelShow"
) -> str:
    """Get an existing label by name or create it if it doesn't exist
    
    Args:
        name: Name of the label to get or create
        messageListVisibility: Message list visibility (show/hide)
        labelListVisibility: Label list visibility (labelShow/labelShowIfUnread/labelHide)
    """
    try:
        service = get_gmail_service()
        
        # Try to find existing label
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        for label in labels:
            if label['name'] == name:
                return f"Label found!\nID: {label['id']}\nName: {label['name']}"
        
        # Create new label if not found
        label = {
            'name': name,
            'messageListVisibility': messageListVisibility,
            'labelListVisibility': labelListVisibility
        }
        
        created_label = service.users().labels().create(
            userId='me',
            body=label
        ).execute()
        
        return f"Label created!\nID: {created_label['id']}\nName: {created_label['name']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def download_attachment(
    messageId: str,
    attachmentId: str,
    savePath: str = ".",
    filename: Optional[str] = None
) -> str:
    """Download an email attachment to the local filesystem
    
    Args:
        messageId: The ID of the email containing the attachment
        attachmentId: The attachment ID
        savePath: Directory to save the file (default: current directory)
        filename: Custom filename (optional, uses original if not provided)
    """
    try:
        service = get_gmail_service()
        
        # Get attachment
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=messageId,
            id=attachmentId
        ).execute()
        
        # Decode attachment data
        file_data = base64.urlsafe_b64decode(attachment['data'])
        
        # Get original filename if not provided
        if not filename:
            message = service.users().messages().get(
                userId='me',
                id=messageId,
                format='full'
            ).execute()
            attachments = extract_attachments(message['payload'])
            for att in attachments:
                if att['id'] == attachmentId:
                    filename = att['filename']
                    break
            
            if not filename:
                filename = f"attachment_{attachmentId}"
        
        # Save file
        save_dir = Path(savePath)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return f"Attachment downloaded successfully to: {file_path}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def create_filter(criteria: dict, action: dict) -> str:
    """Create a new Gmail filter with custom criteria and actions
    
    Args:
        criteria: Filter criteria (e.g., {"from": "example@example.com"})
        action: Filter action (e.g., {"addLabelIds": ["Label_123"], "removeLabelIds": ["INBOX"]})
    """
    try:
        service = get_gmail_service()
        
        filter_content = {
            'criteria': criteria,
            'action': action
        }
        
        created_filter = service.users().settings().filters().create(
            userId='me',
            body=filter_content
        ).execute()
        
        return f"Filter created successfully! Filter ID: {created_filter['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def list_filters() -> str:
    """Retrieve all Gmail filters"""
    try:
        service = get_gmail_service()
        results = service.users().settings().filters().list(userId='me').execute()
        filters = results.get('filter', [])
        
        if not filters:
            return "No filters found."
        
        result = f"Found {len(filters)} filter(s):\n\n"
        for f in filters:
            result += f"ID: {f['id']}\n"
            result += f"Criteria: {json.dumps(f.get('criteria', {}), indent=2)}\n"
            result += f"Action: {json.dumps(f.get('action', {}), indent=2)}\n\n"
        
        return result
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def get_filter(filterId: str) -> str:
    """Get details of a specific Gmail filter
    
    Args:
        filterId: The ID of the filter to retrieve
    """
    try:
        service = get_gmail_service()
        filter_data = service.users().settings().filters().get(
            userId='me',
            id=filterId
        ).execute()
        
        result = f"Filter ID: {filter_data['id']}\n"
        result += f"Criteria: {json.dumps(filter_data.get('criteria', {}), indent=2)}\n"
        result += f"Action: {json.dumps(filter_data.get('action', {}), indent=2)}\n"
        
        return result
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def delete_filter(filterId: str) -> str:
    """Delete a Gmail filter
    
    Args:
        filterId: The ID of the filter to delete
    """
    try:
        service = get_gmail_service()
        service.users().settings().filters().delete(
            userId='me',
            id=filterId
        ).execute()
        
        return f"Filter deleted successfully! Filter ID: {filterId}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


@mcp.tool()
def create_filter_from_template(template: str, parameters: dict) -> str:
    """Create a filter using pre-defined templates for common scenarios
    
    Args:
        template: Template name (fromSender, withSubject, withAttachments, largeEmails, containingText, mailingList)
        parameters: Template-specific parameters
    """
    try:
        service = get_gmail_service()
        
        # Define filter based on template
        criteria = {}
        action = {}
        
        if template == 'fromSender':
            criteria['from'] = parameters['senderEmail']
            action['addLabelIds'] = parameters.get('labelIds', [])
            if parameters.get('archive', False):
                action['removeLabelIds'] = ['INBOX']
        
        elif template == 'withSubject':
            criteria['subject'] = parameters['subjectText']
            action['addLabelIds'] = parameters.get('labelIds', [])
            if not parameters.get('markAsRead', True):
                action['removeLabelIds'] = action.get('removeLabelIds', []) + ['UNREAD']
        
        elif template == 'withAttachments':
            criteria['hasAttachment'] = True
            action['addLabelIds'] = parameters.get('labelIds', [])
        
        elif template == 'largeEmails':
            criteria['size'] = parameters['sizeInBytes']
            criteria['sizeComparison'] = 'larger'
            action['addLabelIds'] = parameters.get('labelIds', [])
        
        elif template == 'containingText':
            criteria['query'] = parameters['searchText']
            action['addLabelIds'] = parameters.get('labelIds', [])
            if parameters.get('markImportant', False):
                action['addLabelIds'] = action.get('addLabelIds', []) + ['IMPORTANT']
        
        elif template == 'mailingList':
            criteria['query'] = f'list:{parameters["listIdentifier"]}'
            action['addLabelIds'] = parameters.get('labelIds', [])
            if parameters.get('archive', False):
                action['removeLabelIds'] = ['INBOX']
        
        else:
            return f"Unknown template: {template}"
        
        # Create filter
        filter_content = {
            'criteria': criteria,
            'action': action
        }
        
        created_filter = service.users().settings().filters().create(
            userId='me',
            body=filter_content
        ).execute()
        
        return f"Filter created from template '{template}'! Filter ID: {created_filter['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as error:
        return f"Error: {str(error)}"


# Create the streamable HTTP app for MCP
mcp_app = mcp.streamable_http_app()

# Create FastAPI app
app = FastAPI(
    lifespan=lambda _: mcp.session_manager.run(),
)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the index page"""
    return FileResponse(STATIC_DIR / "index.html")


# Mount the MCP app
app.mount("/", mcp_app)
