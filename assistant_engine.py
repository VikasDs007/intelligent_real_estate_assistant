import logging
import re
from difflib import get_close_matches
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

import utils
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

logger = logging.getLogger(__name__)

CLIENT_ID_PATTERN = re.compile(r"CL-\d+", re.IGNORECASE)
PROPERTY_ID_PATTERN = re.compile(r"[A-Z]+-PROP-\d+", re.IGNORECASE)


def is_ai_enabled() -> bool:
    return bool(AI_API_KEY)


def detect_intent(query: str) -> str:
    text = query.lower()

    if any(term in text for term in ["follow-up", "follow up", "task", "tasks", "due", "deadline"]):
        return "tasks"
    if any(term in text for term in ["recommend", "suggest properties", "property matches", "best matches"]):
        return "recommendations"
    if any(term in text for term in ["client", "lead", "crm", "status", "profile"]):
        return "client"
    if any(term in text for term in ["market", "trend", "inventory", "price", "locality"]):
        return "market"
    if any(term in text for term in ["property", "listing", "home", "apartment", "office", "bungalow"]):
        return "property"
    if any(term in text for term in ["summary", "overview", "what is happening", "what's happening"]):
        return "overview"
    return "general"


def _clean_query_fragment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" :-,\n\t")


def _resolve_client_reference(reference_text: str) -> Optional[str]:
    clients_df = utils.get_all_clients_df()
    if clients_df.empty or 'client_id' not in clients_df.columns:
        return None

    match = CLIENT_ID_PATTERN.search(reference_text)
    if match:
        client_id = match.group(0).upper()
        if client_id in clients_df['client_id'].astype(str).str.upper().values:
            return clients_df[clients_df['client_id'].astype(str).str.upper() == client_id].iloc[0]['client_id']

    lower_text = reference_text.lower()
    if 'name' in clients_df.columns:
        name_matches = clients_df[clients_df['name'].astype(str).str.lower().str.contains(lower_text, na=False)]
        if not name_matches.empty:
            return name_matches.iloc[0]['client_id']

        client_names = clients_df['name'].astype(str).tolist()
        close_names = get_close_matches(reference_text, client_names, n=1, cutoff=0.5)
        if close_names:
            matched_row = clients_df[clients_df['name'].astype(str) == close_names[0]]
            if not matched_row.empty:
                return matched_row.iloc[0]['client_id']

        tokens = [token for token in re.split(r"\s+", lower_text) if len(token) >= 3]
        if tokens:
            token_mask = pd.Series(False, index=clients_df.index)
            for token in tokens:
                token_mask = token_mask | clients_df['name'].astype(str).str.lower().str.contains(token, na=False)
            token_matches = clients_df[token_mask]
            if not token_matches.empty:
                return token_matches.iloc[0]['client_id']

    return None


def _resolve_property_reference(reference_text: str) -> Optional[str]:
    properties_df = utils.get_all_properties_df()
    if properties_df.empty or 'property_id' not in properties_df.columns:
        return None

    match = PROPERTY_ID_PATTERN.search(reference_text)
    if match:
        property_id = match.group(0).upper()
        if property_id in properties_df['property_id'].astype(str).str.upper().values:
            return properties_df[properties_df['property_id'].astype(str).str.upper() == property_id].iloc[0]['property_id']

    if 'propertytype' in properties_df.columns and 'arealocality' in properties_df.columns:
        text = reference_text.lower()
        candidates = properties_df[
            properties_df['propertytype'].astype(str).str.lower().str.contains(text, na=False) |
            properties_df['arealocality'].astype(str).str.lower().str.contains(text, na=False)
        ]
        if not candidates.empty:
            return candidates.iloc[0]['property_id']

    return None


def _parse_due_date(query: str) -> date:
    text = query.lower()
    if "today" in text:
        return date.today()
    if "tomorrow" in text:
        return date.today() + timedelta(days=1)
    in_days_match = re.search(r"in\s+(\d+)\s+days?", text)
    if in_days_match:
        return date.today() + timedelta(days=int(in_days_match.group(1)))
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today() + timedelta(days=1)


def _extract_text_after_keywords(query: str, keywords: List[str]) -> str:
    lower_query = query.lower()
    for keyword in keywords:
        index = lower_query.find(keyword)
        if index != -1:
            remainder = query[index + len(keyword):]
            if ":" in remainder:
                remainder = remainder.split(":", 1)[1]
            return _clean_query_fragment(remainder)
    if ":" in query:
        return _clean_query_fragment(query.split(":", 1)[1])
    return _clean_query_fragment(query)


def handle_chat_request(
    query: str,
    selected_client_id: Optional[str] = None,
    selected_property_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_query = query.strip()
    lower_query = normalized_query.lower()

    resolved_client_id = _resolve_client_reference(normalized_query) or selected_client_id
    resolved_property_id = _resolve_property_reference(normalized_query) or selected_property_id

    if any(term in lower_query for term in ["add note", "save note", "log note", "note to", "note for"]):
        target_client_id = _resolve_client_reference(normalized_query) or selected_client_id
        if not target_client_id:
            return {
                "intent": "client_note",
                "answer": "Tell me which client to save the note for, for example: add note for CL-1001: call tomorrow.",
                "suggested_actions": ["Add a note for a client", "Select a client from the sidebar"],
                "context": build_context(selected_client_id, selected_property_id),
                "used_ai": False,
                "action": None,
            }
        note_text = _extract_text_after_keywords(normalized_query, ["add note", "save note", "log note", "note to", "note for"])
        if note_text.lower().startswith(target_client_id.lower()):
            note_text = _clean_query_fragment(note_text[len(target_client_id):])
        save_client_note(target_client_id, note_text)
        client_context = build_context(target_client_id, resolved_property_id)
        return {
            "intent": "client_note",
            "answer": f"Saved the note for {target_client_id}.",
            "suggested_actions": ["Show the client profile", "Create a follow-up task", "Add another note"],
            "context": client_context,
            "used_ai": False,
            "action": {"type": "focus_client", "client_id": target_client_id},
        }

    if any(term in lower_query for term in ["create task", "add task", "schedule task", "follow up", "follow-up", "remind me"]):
        target_client_id = _resolve_client_reference(normalized_query) or selected_client_id
        if not target_client_id:
            return {
                "intent": "task_create",
                "answer": "Tell me which client the task is for, for example: create task for CL-1001 tomorrow: call back.",
                "suggested_actions": ["Choose a client", "Create a follow-up task"],
                "context": build_context(selected_client_id, selected_property_id),
                "used_ai": False,
                "action": None,
            }
        description = _extract_text_after_keywords(normalized_query, ["create task", "add task", "schedule task", "follow up", "follow-up", "remind me"])
        due_date = _parse_due_date(normalized_query)
        task_type = "Follow-up"
        if "site visit" in lower_query:
            task_type = "Site Visit"
        elif "negotiation" in lower_query or "negotiate" in lower_query:
            task_type = "Negotiation"
        create_follow_up_task(
            client_id=target_client_id,
            task_description=description,
            due_date=due_date,
            property_id=resolved_property_id,
            task_type=task_type,
            details=description,
        )
        return {
            "intent": "task_create",
            "answer": f"Created a {task_type.lower()} task for {target_client_id} due {due_date.isoformat()}.",
            "suggested_actions": ["Open the task page", "Add a note for the same client", "Show the related property"],
            "context": build_context(target_client_id, resolved_property_id),
            "used_ai": False,
            "action": {"type": "focus_client", "client_id": target_client_id},
        }

    if any(term in lower_query for term in ["show", "open", "fetch", "focus"]):
        if resolved_client_id and any(term in lower_query for term in ["show", "open", "fetch", "focus", "client", "details"]):
            return {
                "intent": "client",
                "answer": f"Opening client {resolved_client_id}.",
                "suggested_actions": ["Review recommendations", "Add a note", "Create a task"],
                "context": build_context(resolved_client_id, resolved_property_id),
                "used_ai": False,
                "action": {"type": "focus_client", "client_id": resolved_client_id},
            }

        if resolved_property_id and any(term in lower_query for term in ["show", "open", "fetch", "focus", "property", "listing", "details"]):
            return {
                "intent": "property",
                "answer": f"Opening property {resolved_property_id}.",
                "suggested_actions": ["Compare against client requirements", "Find related clients"],
                "context": build_context(resolved_client_id, resolved_property_id),
                "used_ai": False,
                "action": {"type": "focus_property", "property_id": resolved_property_id},
            }

    return generate_assistant_reply(normalized_query, resolved_client_id, resolved_property_id)


def _df_to_records(df: pd.DataFrame, columns: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    existing_columns = [column for column in columns if column in df.columns]
    if not existing_columns:
        return []
    return df[existing_columns].head(limit).to_dict(orient="records")


def build_context(
    selected_client_id: Optional[str] = None,
    selected_property_id: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    clients_df = utils.get_all_clients_df()
    properties_df = utils.get_all_properties_df()
    tasks_df = utils.get_all_tasks()

    overview = {
        "total_clients": int(len(clients_df)),
        "total_properties": int(len(properties_df)),
        "high_priority_clients": int(clients_df['status'].isin(["Negotiating", "Site Visit Planned"]).sum()) if 'status' in clients_df.columns else 0,
        "new_leads": int(clients_df['status'].eq("New").sum()) if 'status' in clients_df.columns else 0,
        "pending_tasks": int(tasks_df['status'].eq("Pending").sum()) if 'status' in tasks_df.columns else 0,
    }

    top_clients = pd.DataFrame()
    if not clients_df.empty:
        try:
            top_clients = utils.get_clients_with_scores().head(limit)
        except Exception:
            top_clients = clients_df.head(limit)

    pending_tasks = pd.DataFrame()
    if not tasks_df.empty and 'status' in tasks_df.columns:
        pending_tasks = tasks_df[tasks_df['status'] == 'Pending'].copy()
        if 'due_date' in pending_tasks.columns:
            pending_tasks['due_date_sort'] = pd.to_datetime(pending_tasks['due_date'], errors='coerce')
            pending_tasks = pending_tasks.sort_values(by=['due_date_sort', 'task_id'], na_position='last')

    selected_client = None
    if selected_client_id and not clients_df.empty and 'client_id' in clients_df.columns:
        client_rows = clients_df[clients_df['client_id'] == selected_client_id]
        if not client_rows.empty:
            selected_client = client_rows.iloc[0].to_dict()
            latest_event = utils.get_latest_client_event(selected_client_id)
            if latest_event is not None:
                selected_client['latest_event'] = latest_event.to_dict() if hasattr(latest_event, 'to_dict') else latest_event
            try:
                selected_client['recommendations'] = utils.get_recommendations(selected_client_id).get('recommendations', [])
            except Exception as exc:
                logger.debug("Recommendation lookup failed for client_id=%s: %s", selected_client_id, exc)
                selected_client['recommendations'] = []

    selected_property = None
    if selected_property_id and not properties_df.empty and 'property_id' in properties_df.columns:
        property_rows = properties_df[properties_df['property_id'] == selected_property_id]
        if not property_rows.empty:
            selected_property = property_rows.iloc[0].to_dict()

    context = {
        "overview": overview,
        "top_clients": _df_to_records(top_clients, ['client_id', 'name', 'status', 'lookingfor', 'score', 'rating', 'phone'], limit),
        "pending_tasks": _df_to_records(pending_tasks, ['task_id', 'client_id', 'client_name', 'task_description', 'due_date', 'status', 'property_id'], limit),
        "selected_client": selected_client,
        "selected_property": selected_property,
        "sample_properties": _df_to_records(properties_df, ['property_id', 'listingtype', 'propertytype', 'arealocality', 'askingprice', 'monthlyrent'], limit),
    }
    return context


def _format_context_summary(context: Dict[str, Any]) -> str:
    overview = context['overview']
    lines = [
        f"Clients: {overview['total_clients']}",
        f"Properties: {overview['total_properties']}",
        f"High-priority clients: {overview['high_priority_clients']}",
        f"New leads: {overview['new_leads']}",
        f"Pending tasks: {overview['pending_tasks']}",
    ]

    if context.get('selected_client'):
        selected_client = context['selected_client']
        lines.append("")
        lines.append(f"Selected client: {selected_client.get('client_id')} - {selected_client.get('name')}")
        lines.append(f"Status: {selected_client.get('status')}")
        lines.append(f"Requirements: {selected_client.get('requirements')}")
        latest_event = selected_client.get('latest_event')
        if latest_event:
            lines.append(f"Latest event: {latest_event}")
        recommendations = selected_client.get('recommendations') or []
        if recommendations:
            lines.append("Recommended properties:")
            for item in recommendations[:3]:
                lines.append(
                    f"- {item.get('property_id')} | {item.get('propertytype')} | {item.get('arealocality')}"
                )

    if context.get('selected_property'):
        selected_property = context['selected_property']
        lines.append("")
        lines.append(f"Selected property: {selected_property.get('property_id')}")
        lines.append(
            f"{selected_property.get('propertytype')} in {selected_property.get('arealocality')} ({selected_property.get('listingtype')})"
        )

    if context.get('pending_tasks'):
        lines.append("")
        lines.append("Pending tasks:")
        for task in context['pending_tasks'][:3]:
            lines.append(
                f"- {task.get('task_description')} | {task.get('client_name', task.get('client_id'))} | due {task.get('due_date')}"
            )

    return "\n".join(lines)


def _suggest_actions(intent: str, context: Dict[str, Any]) -> List[str]:
    suggestions = []

    if intent in {"overview", "general"}:
        suggestions.extend([
            "Ask for today's follow-up priorities",
            "Request a summary of pending tasks",
            "Ask for market trends or property hotspots",
        ])
    if context.get('selected_client'):
        suggestions.extend([
            "Show matching properties for this client",
            "Summarize the client's latest activity",
            "Suggest the next follow-up step",
        ])
    if context.get('selected_property'):
        suggestions.extend([
            "Compare this property against client requirements",
            "Explain why this property is a good match",
        ])
    if intent == "tasks":
        suggestions.extend([
            "List overdue tasks first",
            "Highlight clients with site visits planned",
        ])
    if intent == "recommendations":
        suggestions.extend([
            "Show the best match for the selected client",
            "Explain budget and BHK fit",
        ])
    if intent == "market":
        suggestions.extend([
            "Summarize property supply by locality",
            "Show the most active listing trends",
        ])

    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)
    return unique_suggestions[:5]


def _generate_local_reply(query: str, context: Dict[str, Any]) -> str:
    intent = detect_intent(query)
    overview = context['overview']
    lines = []

    if intent == "tasks":
        lines.append(
            f"You have {overview['pending_tasks']} pending tasks, including {overview['high_priority_clients']} high-priority clients to keep moving."
        )
        if context.get('pending_tasks'):
            lines.append("Top pending tasks:")
            for task in context['pending_tasks'][:3]:
                lines.append(
                    f"- {task.get('task_description')} (due {task.get('due_date')})"
                )
    elif intent == "recommendations":
        selected_client = context.get('selected_client')
        if selected_client:
            recommendations = selected_client.get('recommendations') or []
            if recommendations:
                lines.append(
                    f"I found {len(recommendations)} matching properties for {selected_client.get('name')}."
                )
                top = recommendations[0]
                lines.append(
                    f"Best match: {top.get('property_id')} in {top.get('arealocality')} ({top.get('propertytype')})."
                )
            else:
                lines.append(
                    f"I could not find a close match for {selected_client.get('name')} right now."
                )
        else:
            lines.append("Select a client first and I will generate tailored property matches.")
    elif intent == "client":
        selected_client = context.get('selected_client')
        if selected_client:
            lines.append(
                f"{selected_client.get('name')} is currently marked as {selected_client.get('status')}."
            )
            lines.append(f"Requirements: {selected_client.get('requirements')}")
            latest_event = selected_client.get('latest_event')
            if latest_event:
                lines.append(f"Latest activity: {latest_event}")
        else:
            lines.append(
                f"There are {overview['total_clients']} clients in the system, including {overview['high_priority_clients']} high-priority leads."
            )
    elif intent == "property":
        selected_property = context.get('selected_property')
        if selected_property:
            price = selected_property.get('askingprice') or selected_property.get('monthlyrent')
            lines.append(
                f"{selected_property.get('propertytype')} in {selected_property.get('arealocality')} is listed as {selected_property.get('listingtype')}."
            )
            if price:
                lines.append(f"Price: {utils.format_indian_currency(price)}")
        else:
            lines.append(
                f"The inventory currently has {overview['total_properties']} properties across the database."
            )
    elif intent == "market":
        lines.append(
            f"The dashboard currently tracks {overview['total_properties']} properties and {overview['total_clients']} clients."
        )
        if context.get('sample_properties'):
            top = context['sample_properties'][0]
            lines.append(
                f"Sample listing: {top.get('propertytype')} in {top.get('arealocality')} ({top.get('listingtype')})."
            )
    elif intent == "overview":
        lines.append(
            f"You have {overview['total_clients']} clients, {overview['total_properties']} properties, and {overview['pending_tasks']} pending tasks."
        )
        lines.append(
            f"High-priority clients: {overview['high_priority_clients']} | New leads: {overview['new_leads']}"
        )
    else:
        lines.append(
            f"I can help with clients, properties, tasks, and market summaries. Right now the system has {overview['total_clients']} clients and {overview['total_properties']} properties."
        )

    if context.get('selected_client') and intent not in {"recommendations", "client"}:
        selected_client = context['selected_client']
        lines.append("")
        lines.append(
            f"For {selected_client.get('name')}, the next best action is to review recent notes and follow up based on the current status."
        )
        if selected_client.get('recommendations'):
            lines.append(
                f"I can also surface {len(selected_client.get('recommendations'))} property matches for this client."
            )

    return "\n".join(lines)


def generate_assistant_reply(
    query: str,
    selected_client_id: Optional[str] = None,
    selected_property_id: Optional[str] = None,
) -> Dict[str, Any]:
    context = build_context(selected_client_id, selected_property_id)
    intent = detect_intent(query)
    local_reply = _generate_local_reply(query, context)
    llm_reply = None

    if is_ai_enabled():
        try:
            llm_reply = _call_ai_model(query, context)
        except Exception as exc:
            logger.warning("AI model request failed, falling back to local reply: %s", exc)

    reply_text = llm_reply or local_reply
    return {
        "intent": intent,
        "answer": reply_text,
        "suggested_actions": _suggest_actions(intent, context),
        "context": context,
        "used_ai": bool(llm_reply),
    }


def save_client_note(client_id: str, note: str) -> Dict[str, Any]:
    clean_note = note.strip()
    if not clean_note:
        raise ValueError("Note cannot be empty.")
    utils.add_communication_note(client_id, clean_note)
    return {
        "client_id": client_id,
        "note": clean_note,
        "status": "saved",
    }


def create_follow_up_task(
    client_id: str,
    task_description: str,
    due_date: date,
    property_id: Optional[str] = None,
    task_type: str = "Follow-up",
    details: Optional[str] = None,
) -> Dict[str, Any]:
    clean_description = task_description.strip()
    if not clean_description:
        raise ValueError("Task description cannot be empty.")
    utils.add_task(
        client_id=client_id,
        task_type=task_type,
        task_description=clean_description,
        due_date=due_date.isoformat(),
        property_id=property_id,
        details=details,
    )
    return {
        "client_id": client_id,
        "property_id": property_id,
        "task_type": task_type,
        "task_description": clean_description,
        "due_date": due_date.isoformat(),
        "status": "created",
    }


def _call_ai_model(query: str, context: Dict[str, Any]) -> Optional[str]:
    base_url = AI_BASE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    system_prompt = (
        "You are an intelligent real estate assistant for an agent-facing CRM. "
        "Use only the provided context when possible. Be concise, practical, and action-oriented. "
        "If the user asks for next steps, recommend the most relevant follow-up actions."
    )
    user_payload = {
        "query": query,
        "context": context,
        "instructions": [
            "Summarize the most relevant facts first.",
            "Include actionable next steps when possible.",
            "Call out if the user should select a client or property first.",
        ],
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_payload}"},
            ],
            "temperature": 0.2,
        },
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None
