import json
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional Ollama integration
try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
    OLLAMA_MODEL = "gpt-oss:20b"
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available - ticket enrichment will be limited")


def get_ollama_client():
    """Initialize and return Ollama client"""
    if not OLLAMA_AVAILABLE:
        return None
    if not settings.OLLAMA_API_KEY:
        return None
    return Client(
        host="https://ollama.com",
        headers={'Authorization': 'Bearer ' + settings.OLLAMA_API_KEY}
    )


def process_ticket_in_background(db: Session, ticket_id: UUID, tenant_id: UUID):
    """
    Background task to enrich ticket with AI-generated content
    - Generate title from description
    - Generate summary from description
    - Translate description
    - Detect and assign appropriate category
    - Update ticket with these values
    """
    from app.crud import ticket as crud_ticket
    from app.crud import category as crud_category
    
    try:
        # Get the ticket
        ticket = crud_ticket.get_ticket_by_id_in_tenant(db, ticket_id, tenant_id)
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            return
        
        if not ticket.description:
            logger.warning(f"Ticket {ticket_id} has no description to process")
            return
        
        logger.info(f"Processing ticket {ticket_id}")
        
        # Get all categories for the tenant
        categories = crud_category.get_categories_by_tenant(db, tenant_id, skip=0, limit=100)
        
        # Try to enrich with AI
        enriched_data = {}
        
        if OLLAMA_AVAILABLE:
            ai_result = generate_ticket_insights(
                ticket.description,
                categories=categories
            )
            if ai_result:
                enriched_data['title'] = ai_result.get('Title')
                enriched_data['summary'] = ai_result.get('Summary')
                enriched_data['translation'] = ai_result.get('TranslatedText')
                
                # Assign category if detected
                if ai_result.get('CategoryName') and categories:
                    matched_category = next(
                        (cat for cat in categories if cat.name.lower() == ai_result.get('CategoryName', '').lower()),
                        None
                    )
                    if matched_category:
                        enriched_data['category_id'] = matched_category.id
                        logger.info(f"Assigned category '{matched_category.name}' (ID: {matched_category.id}) to ticket {ticket_id}")
        
        # Update ticket if we have enriched data
        if enriched_data:
            from app.schemas.ticket import TicketUpdate
            update_data = TicketUpdate(**enriched_data)
            crud_ticket.update_ticket(db, ticket_id, tenant_id, update_data)
            logger.info(f"Ticket {ticket_id} enriched successfully")
        
    except Exception as e:
        logger.error(f"Error processing ticket {ticket_id}: {str(e)}")


def generate_ticket_insights(description: str, target_language: str = "Arabic", categories=None) -> Optional[Dict[str, Any]]:
    """
    Generate title, summary, translation, and category suggestion using Ollama
    """
    if not OLLAMA_AVAILABLE:
        logger.warning("Ollama not available - skipping AI enrichment")
        return None
    
    client = get_ollama_client()
    if not client:
        logger.warning("Ollama client not initialized - skipping AI enrichment")
        return None
    
    # Format categories for the prompt
    category_list = ""
    if categories:
        category_list = "\n".join([f"- {cat.name}" for cat in categories])
        category_instruction = f"""
"Category": "<choose the most appropriate category name from the list below that fits this ticket. Choose EXACTLY one name from the list. If none fit perfectly, choose the closest match>",

AVAILABLE CATEGORIES:
{category_list}
"""
    else:
        category_instruction = ""
    
    prompt_content = f"""
You are an AI system specialized in processing customer support tickets.

Read the provided ticket description and produce ONE valid JSON object.

OUTPUT FORMAT (STRICT):
Return ONLY a valid JSON object with these keys:
"Title": "<short, descriptive title (max 10 words)>",
"Summary": "<1-2 sentences describing the core issue>",
"TranslatedText": "<description translated to {target_language}>",{category_instruction}

RULES:
- Output MUST be valid JSON only
- Do NOT include markdown blocks
- Do NOT include any text other than the JSON object

TICKET DESCRIPTION:
{description}
"""

    try:
        messages = [
            {
                'role': 'user',
                'content': prompt_content
            },
        ]
        
        resp_text = ""
        for part in client.chat(OLLAMA_MODEL, messages=messages, stream=True):
            resp_text += part['message']['content']
        
        logger.info(f"Ollama response: {resp_text[:200]}...")
        
        resp_json = json.loads(resp_text)
        return {
            "Title": resp_json.get("Title"),
            "Summary": resp_json.get("Summary"),
            "TranslatedText": resp_json.get("TranslatedText"),
            "CategoryName": resp_json.get("Category"),
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Ollama JSON response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        return None


def get_gemini_result(ticket, departments, target_language="Arabic"):
    """Legacy function - kept for backward compatibility"""
    # Note: Keep the prompt variable name or rename to 'prompt_text' for clarity
    prompt_content = f"""
            ROLE:
            You are an AI system specialized in classifying customer support emails into structured support tickets.

            OBJECTIVE:
            Read the provided email body and produce EXACTLY ONE valid JSON object that conforms strictly to the schema and rules below.

            OUTPUT FORMAT (STRICT):
            Return only a single JSON object with the following keys:
            
            "Title": "<short, descriptive title (max 10 words)>",
            "Summary": "<1–2 concise sentences describing the core issue>",
            "OriginalLanguageText": "<email body exactly as provided, unchanged>",
            "TranslatedText": "<email body translated into the target language>",
            "Department": "<one of the most relevant department from the allowed department list>",
            "Priority": "<low | medium | high>"
            
            ALLOWED VALUES:
            - Department MUST be exactly one of: {departments}
            - Priority MUST be one of: low, medium, high (lowercase only)

            TRANSLATION RULES:
            - Target translation language: {target_language}

            STRICT RULES:
            - Output MUST be valid JSON.
            - Do NOT include markdown blocks (like ```json).
            - Do NOT include any text other than the JSON object.

            EMAIL BODY:
            {ticket}
            """

    if not OLLAMA_AVAILABLE:
        return None
        
    client = get_ollama_client()
    if not client:
        return None
    
    messages = [
        {
            'role': 'user',
            'content': prompt_content
        },
    ]

    try:
        resp_text = ""
        for part in client.chat(OLLAMA_MODEL, messages=messages, stream=True):
            resp_text += part['message']['content']

        resp_json = json.loads(resp_text)
        result = {
            "email_body": ticket,
            "Title": resp_json.get("Title"),
            "Summary": resp_json.get("Summary"),
            "TranslatedText": resp_json.get("TranslatedText"),
            "Language": target_language,
            "Department": resp_json.get("Department"),
            "Priority": resp_json.get("Priority")
        }
        return result
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON response")
        return None
