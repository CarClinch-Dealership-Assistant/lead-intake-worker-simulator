import json
import uuid
import random
import os
import sys
from datetime import datetime, timezone
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

# Service Bus
SERVICE_BUS_CONNECTION_STR = os.getenv("SERVICE_BUS_CONNECTION_STR")
QUEUE_NAME = "leads"

# Cosmos DB
ENDPOINT = os.getenv("COSMOS_ENDPOINT")
KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "CarClinchDB")

# initialize Cosmos Client
try:
    cosmos_client = CosmosClient(ENDPOINT, KEY, request_timeout=60)
    db = cosmos_client.get_database_client(COSMOS_DB_NAME)
    vehicle_container = db.get_container_client("vehicles")
    dealer_container = db.get_container_client("dealerships")
    lead_container = db.get_container_client("leads")
    conversation_container = db.get_container_client("conversations") # ADDED
except Exception as e:
    print(f"[WARNING] Failed to initialize Cosmos DB client. Check connection endpoint and key. Error: {e}")
    sys.exit(1)

EDGE_CASES = [
    "I'd like to test drive it tomorrow at 4:30 PM.",
    "I can swing by around 2 on Friday.",
    "Are you free tomorrow morning?",
    "I'll be there between 3 and 5 PM on April 20th.",
    "What do you have open sometime this month?",
    "I'm out of town, but I can come in anytime after May 10th.",
    "I want to test drive between May 1st and May 20th.",
    "Let's do November 31st at 10 AM.",
    "Can I come in on February 29th at 1 PM?",
    "Can I come in next Tuesday or Wednesday at 4?",
    "Can we do 2 PM tomorrow? Also, what is your absolute lowest cash price?",
    "Actually, I'd rather look at the 2021 Honda Civic you have instead of the Ford. Are you free Friday at 5?",
    "I might want to come look at it sometime soon.",
    "Yeah, maybe.",
    "I'm busy this week. What do you have for next Monday or Tuesday morning?",
    "Stop asking me about the morning. I already told you I work until 5. Is there a real person I can talk to?",
    "Is this car still available?",
    "Does this vehicle come with Apple CarPlay and heated seats?",
    "Is this a good car for a student budget?",
    "Is this car good on gas? I have a long commute.",
    "Is this car good for rural driving in the snow?",
    "What kind of interest rate can I get if my credit score is around 680?",
    "I want to trade in my 2016 Honda Accord. How much will you give me for it?",
    "I know the listed price is $22,000, but would you take $19,500 cash today?",
    "What is your absolute lowest out-the-door price?",
    "I actually want to look at a Toyota RAV4. Do you have any?",
    "What are your hours this weekend?",
    "Can I just drop by after I get off work around 6?",
    "I want to see it, but I need to check my schedule first.",
    "Does it have a backup camera? If so, I'd like to schedule a test drive for Saturday at 11 AM.",
    "Is it an automatic? Also, are you free next Thursday afternoon to show it to me?"
]

def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def get_live_vehicle_and_dealership():
    try:
        vehicles = list(vehicle_container.query_items(
            query="SELECT TOP 100 * FROM c",
            enable_cross_partition_query=True
        ))
        
        if not vehicles:
            raise Exception("No vehicles found in the database!")
            
        vehicle = random.choice(vehicles)
        dealer_id = vehicle.get("dealerId")
        
        if not dealer_id:
            raise Exception(f"Vehicle {vehicle.get('id')} has no associated dealerId!")

        dealership = dealer_container.read_item(item=dealer_id, partition_key=dealer_id)
        return vehicle, dealership
        
    except exceptions.CosmosResourceNotFoundError:
        raise Exception("Dealership or Vehicle not found in database.")
    except Exception as e:
        raise Exception(f"Database query failed: {e}")

def generate_notes(custom_note=None):
    if custom_note:
        return custom_note
    return random.choice(EDGE_CASES)

def process_lead(fname, lname, email, phone, custom_note=None):
    note_text = generate_notes(custom_note)
    current_time = datetime.now(timezone.utc).isoformat()
    
    new_note = {
        "text": note_text,
        "timestamp": current_time
    }
    
    try:
        query = "SELECT * FROM leads l WHERE l.email = @email"
        parameters = [{"name": "@email", "value": email.lower()}]
        existing_leads = list(lead_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        if existing_leads:
            lead = existing_leads[0]
            if "notes" not in lead or not isinstance(lead["notes"], list):
                lead["notes"] = []
                
            lead["notes"].append(new_note)
            lead_container.replace_item(item=lead['id'], body=lead) 
            print(f"\n[*] DB WRITE: Updated existing lead ({email})")
            return lead
        else:
            lead = {
                "id": new_id("lead"),
                "fname": fname,
                "lname": lname,
                "email": email.lower(),
                "phone": phone,
                "status": 0,
                "notes": [new_note],
                "timestamp": current_time,
            }
            lead_container.create_item(body=lead) 
            print(f"\n[*] DB WRITE: Created new lead ({email})")
            return lead
            
    except Exception as e:
        raise Exception(f"Failed to process lead in Cosmos DB: {e}")

def create_conversation(lead_id, vehicle_id, dealer_id):
    """Creates a new conversation document in Cosmos DB to tie the records together."""
    try:
        conv_id = new_id("conv")
        conv_doc = {
            "id": conv_id,
            "leadId": lead_id,
            "vehicleId": vehicle_id,
            "dealerId": dealer_id,
            "status": 1,  # 1 = active
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        conversation_container.create_item(body=conv_doc)
        print(f"[*] DB WRITE: Created conversation ({conv_id})")
        return conv_doc
        
    except Exception as e:
        raise Exception(f"Failed to create conversation in Cosmos DB: {e}")

def publish_to_service_bus(payload):
    client = ServiceBusClient.from_connection_string(conn_str=SERVICE_BUS_CONNECTION_STR)
    sender = client.get_queue_sender(queue_name=QUEUE_NAME)

    with sender:
        message = ServiceBusMessage(json.dumps(payload))
        sender.send_messages(message)

    print(f"[*] QUEUE: Published payload to Service Bus")
    print(f"    - Lead ID: {payload['lead']['id']}")
    print(f"    - Vehicle: {payload['vehicle'].get('year')} {payload['vehicle'].get('make')} {payload['vehicle'].get('model')}")
    print(f"    - Note:    '{payload['lead']['notes']}'\n")

def run_interactive():
    print("==================================================")
    print("  Lead Intake Simulator (Live DB Connection)")
    print("==================================================")
    
    print("Enter Lead Information (Press ENTER to use random defaults):")
    def_fname = random.choice(["John", "Alice", "Maria", "David"])
    def_lname = random.choice(["Doe", "Smith", "Lee", "Patel"])
    
    fname = input(f"First Name [{def_fname}]: ").strip() or def_fname
    lname = input(f"Last Name [{def_lname}]: ").strip() or def_lname
    email = input(f"Email [{fname.lower()}.{lname.lower()}@example.com]: ").strip() or f"{fname.lower()}.{lname.lower()}@example.com"
    phone = input(f"Phone [555-000-0000]: ").strip() or f"555-{random.randint(100,999)}-{random.randint(1000,9999)}"

    print("\n--------------------------------------------------")
    print("- Press [ENTER] to send a random edge case")
    print("- Type a custom message to send a specific scenario")
    print("- Type 'q' to quit")
    print("--------------------------------------------------\n")

    while True:
        try:
            user_input = input("Lead notes (or Enter for random): ").strip()
            
            if user_input.lower() == 'q':
                print("Exiting...")
                break
                
            custom_note = user_input if user_input else None

            # fetch live vehicle and dealership from Cosmos DB
            vehicle, dealership = get_live_vehicle_and_dealership()
            
            # process lead (create or update in DB)
            lead = process_lead(fname, lname, email, phone, custom_note)
            
            # create conversation document to tie them together
            conversation = create_conversation(lead["id"], vehicle["id"], dealership["id"])

            # assemble payload
            payload = {
                "lead": {
                    "id": lead['id'],
                    "fname": lead['fname'],
                    "lname": lead['lname'],
                    "email": lead['email'],
                    "phone": lead['phone'],
                    "status": lead['status'],
                    "notes": lead.get('notes', [])[-1]['text'] if lead.get('notes') else "",
                    "timestamp": lead['timestamp']
                },
                "vehicle": {
                    "id": vehicle['id'],
                    "status": vehicle.get('status'),
                    "year": vehicle.get('year'),
                    "make": vehicle.get('make'),
                    "model": vehicle.get('model'),
                    "trim": vehicle.get('trim'),
                    "mileage": vehicle.get('mileage'),
                    "transmission": vehicle.get('transmission'),
                    "comments": vehicle.get('comments')
                },
                "dealership": {
                    "id": dealership['id'],
                    "name": dealership.get('name'),
                    "email": dealership.get('email'),
                    "phone": dealership.get('phone'),
                    "address1": dealership.get('address1'),
                    "address2": dealership.get('address2'),
                    "city": dealership.get('city'),
                    "province": dealership.get('province'),
                    "postal_code": dealership.get('postal_code')
                },
                "conversationId": conversation['id']
            }
            
            # publish
            publish_to_service_bus(payload)

        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    run_interactive()