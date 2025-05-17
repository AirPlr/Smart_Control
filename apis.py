import requests
import json
from datetime import datetime
from ollama import chat
from ollama import ChatResponse

BASE_URL = "http://127.0.0.1:5000"

def display_args(args: dict):
    """Print each argument on its own line."""
    if args:
        print("Arguments:")
        for key, value in args.items():
            print(f"  {key}: {value}")
    else:
        print("No arguments provided.")

def query_consultants(filters: dict) -> str:
    """Query consultants with optional filters (e.g. name, position)."""
    resp = requests.get(f"{BASE_URL}/api/consultants", params=filters)
    if resp.ok:
        consultants = resp.json().get("consultants", [])
        return "\n".join(json.dumps(c, indent=2) for c in consultants)
    return "Error querying consultants."

def list_appointments():
    resp = requests.get(f"{BASE_URL}/api/appointments")
    if resp.ok:
        data = resp.json().get("appointments", [])
        return json.dumps(data, indent=2)
    return "Error retrieving appointments."
def get_appointment(appointment_id: str) -> str:
        resp = requests.get(f"{BASE_URL}/api/appointments/{appointment_id}")
        if resp.ok:
            return "Appointment:\n" + json.dumps(resp.json(), indent=2)
        else:
            return "Appointment not found."


def create_appointment(details: dict) -> str:
        # Validate required fields
        for field in ["nome_cliente", "numero_telefono", "data_appuntamento"]:
            if not details.get(field, "").strip():
                return f"Missing required field: {field}"
        # Ensure default values if not provided
        details["indirizzo"] = details.get("indirizzo", "").strip()
        details["note"] = details.get("note", "").strip()
        details["tipologia"] = details.get("tipologia", "").strip()
        details["stato"] = details.get("stato", "").strip()
        details["nominativi_raccolti"] = int(details.get("nominativi_raccolti", 0))
        details["appuntamenti_personali"] = int(details.get("appuntamenti_personali", 0))
        details["venduto"] = str(details.get("venduto", "false")).strip().lower() == "true"
        details["data_richiamo"] = details.get("data_richiamo") or None

        # Optional: convert consultants string to list of ints if provided
        consultants = details.get("consultants")
        if consultants and isinstance(consultants, str):
            details["consultants"] = [int(cid) for cid in consultants.split(",") if cid.strip().isdigit()]

        resp = requests.post(f"{BASE_URL}/api/appointments", json=details)
        if resp.ok or resp.status_code == 201:
            result = resp.json()
            return "Appointment created. ID: " + str(result.get("id"))
        else:
            return "Error creating appointment: " + str(resp.json())


def update_appointment(appointment_id: str, updates: dict) -> str:
        # Retrieve current appointment data
        current_resp = requests.get(f"{BASE_URL}/api/appointments/{appointment_id}")
        if not current_resp.ok:
            return "Appointment not found."

        current = current_resp.json()
        # Use updates; if a field is not provided in updates, keep current value.
        data = {}
        for field in ['nome_cliente', 'indirizzo', 'numero_telefono', 'note', 'tipologia', 'stato']:
            if field in updates and updates[field].strip():
                data[field] = updates[field].strip()
        for field in ['nominativi_raccolti', 'appuntamenti_personali']:
            if field in updates and str(updates[field]).strip():
                try:
                    data[field] = int(updates[field])
                except ValueError:
                    return f"Invalid integer for {field}."
        if "venduto" in updates:
            val = str(updates["venduto"]).strip().lower()
            if val in ["true", "false"]:
                data["venduto"] = val == "true"
        if "data_appuntamento" in updates and updates["data_appuntamento"].strip():
            data["data_appuntamento"] = updates["data_appuntamento"].strip()
        if "data_richiamo" in updates:
            data["data_richiamo"] = updates["data_richiamo"].strip() or None
        if "consultants" in updates and updates["consultants"]:
            # Expecting a comma separated string or a list of ints.
            if isinstance(updates["consultants"], str):
                data["consultants"] = [int(cid) for cid in updates["consultants"].split(",") if cid.strip().isdigit()]
            elif isinstance(updates["consultants"], list):
                data["consultants"] = updates["consultants"]

        resp = requests.put(f"{BASE_URL}/api/appointments/{appointment_id}", json=data)
        if resp.ok:
            return "Appointment updated."
        else:
            return "Error updating appointment: " + str(resp.json())


def delete_appointment(appointment_id: str) -> str:
        resp = requests.delete(f"{BASE_URL}/api/appointments/{appointment_id}")
        if resp.ok:
            return "Appointment deleted."
        else:
            return "Error deleting appointment."


def list_consultants() -> str:
        resp = requests.get(f"{BASE_URL}/api/consultants")
        if resp.ok:
            consultants = resp.json().get("consultants", [])
            results = []
            for cons in consultants:
                results.append(json.dumps(cons, indent=2))
            return "Consultants:\n" + "\n".join(results)
        else:
            return "Error retrieving consultants."


def get_consultant(consultant_id: str) -> str:
        resp = requests.get(f"{BASE_URL}/api/consultants/{consultant_id}")
        if resp.ok:
            return "Consultant:\n" + json.dumps(resp.json(), indent=2)
        else:
            return "Consultant not found."


def create_consultant(details: dict) -> str:
        for field in ["nome", "posizione"]:
            if not details.get(field, "").strip():
                return f"Missing required field: {field}"
        details["residency"] = details.get("residency", "").strip()
        details["phone"] = details.get("phone", "").strip()
        details["email"] = details.get("email", "").strip()
        details["CF"] = details.get("CF", "").strip()
        # Convert responsabile_id to int if provided and valid
        resp_id = details.get("responsabile_id")
        if resp_id and str(resp_id).isdigit():
            details["responsabile_id"] = int(resp_id)
        else:
            details["responsabile_id"] = None

        resp = requests.post(f"{BASE_URL}/api/consultants", json=details)
        if resp.ok or resp.status_code == 201:
            result = resp.json()
            return "Consultant created. ID: " + str(result.get("id"))
        else:
            return "Error creating consultant: " + str(resp.json())


def update_consultant(consultant_id: str, updates: dict) -> str:
        current_resp = requests.get(f"{BASE_URL}/api/consultants/{consultant_id}")
        if not current_resp.ok:
            return "Consultant not found."

        current = current_resp.json()
        data = {}
        for field in ['nome', 'posizione', 'residency', 'phone', 'email', 'CF']:
            if field in updates and updates[field].strip():
                data[field] = updates[field].strip()
        if "responsabile_id" in updates and str(updates["responsabile_id"]).strip():
            try:
                data["responsabile_id"] = int(updates["responsabile_id"])
            except ValueError:
                return "Invalid responsabile_id."

        resp = requests.put(f"{BASE_URL}/api/consultants/{consultant_id}", json=data)
        if resp.ok:
            return "Consultant updated."
        else:
            return "Error updating consultant: " + str(resp.json())


def delete_consultant(consultant_id: str) -> str:
        resp = requests.delete(f"{BASE_URL}/api/consultants/{consultant_id}")
        if resp.ok:
            return "Consultant deleted."
        else:
            return "Error deleting consultant."

def show_help():
    print("""
Commands:
  help                                 Show this help message.
  list appointments                    List all appointments.
  get appointment                      Get appointment details by ID.
  create appointment                   Create a new appointment.
  update appointment                   Update an existing appointment.
  delete appointment                   Delete an appointment by ID.
  list consultants                     List all consultants.
  get consultant                       Get consultant details by ID.
  create consultant                    Create a new consultant.
  update consultant                    Update an existing consultant.
  delete consultant                    Delete a consultant by ID.
  quit                                 Exit the chatbot.
""")

def interpret_command(message: str) -> str:
    """Ask the LLM to return only a command from user input."""
    system_prompt = (
        "You are a command parser. The user may describe an action in natural language. "
        "Return ONLY the command that matches it from the following list:\n"
        "- list appointments\n"
        "- get appointment\n"
        "- create appointment\n"
        "- update appointment\n"
        "- delete appointment\n"
        "- list consultants\n"
        "- get consultant\n"
        "- create consultant\n"
        "- update consultant\n"
        "- delete consultant\n"
        "- help\n"
        "- quit\n"
        "Return only one line, exactly the command string."
    )
    response: ChatResponse = chat(
        model="llama3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    )
    return response['message']['content'].strip()


def extract_arguments(command: str, message: str) -> dict:
    """Uses LLM to extract arguments needed for the command."""
    system_prompt = (
        f"You are an assistant that extracts parameters for the command: {command}. "
        "Given the user's message, return a JSON object with only the needed arguments. "
        "Examples:\n"
        "- If command is 'get appointment', extract {\"appointment_id\": \"123\"}\n"
        "- If command is 'create consultant', extract all relevant fields\n"
        "- If not enough info is provided, return an empty object {}\n"
        "Return only valid JSON."
    )

    response: ChatResponse = chat(
        model="llama3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    )

    try:
        return json.loads(response["message"]["content"])
    except json.JSONDecodeError:
        return {}

def chat_server(message: str) -> str:
    """Invia il messaggio al chatbot remoto tramite l'endpoint /chat"""
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={"message": message})
        if resp.ok:
            return resp.json().get("response", "")
        return f"Error contacting chatbot: {resp.status_code}"
    except Exception as e:
        return f"Request error: {e}"

def main():
    print("Welcome to the Appointment and Consultant Smart Management System!")
    print("The assistant is ready. Type 'help' to see available commands via chatbot.\n")

    while True:
        user_input = input("You: ")
        if not user_input.strip():
            continue
        # Invia la query al chatbot remoto
        response = chat_server(user_input)
        print(response)
        # Esci se il chatbot termina la sessione
        if response.lower().startswith("session ended") or response.lower().startswith("goodbye"):
            break

if __name__ == "__main__":
    main()