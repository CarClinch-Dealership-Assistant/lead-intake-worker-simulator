import json
import uuid
import random
from datetime import datetime
import psycopg2
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

# for local development, we use the service bus emulator connection string
SERVICE_BUS_CONNECTION_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
USER_EMAIL = os.getenv("USER_EMAIL")
QUEUE_NAME = "leads"

EDGE_CASES = [
    # Time Edge Cases (Exact vs. Fuzzy vs. Invalid)
    "I'd like to test drive it tomorrow at 4:30 PM.",
    "I can swing by around 2 on Friday.",
    "Are you free tomorrow morning?",
    "I'll be there between 3 and 5 PM on April 20th.",
    
    # The "Max 7 Dates" Limit
    "What do you have open sometime this month?",
    "I'm out of town, but I can come in anytime after May 10th.",
    "I want to test drive between May 1st and May 20th.",
    
    # Date Validation (Impossible Dates)
    "Let's do November 31st at 10 AM.",
    "Can I come in on February 29th at 1 PM?",
    
    # Compound / Complex Intents
    "Can I come in next Tuesday or Wednesday at 4?",
    "Can we do 2 PM tomorrow? Also, what is your absolute lowest cash price?",
    "Actually, I'd rather look at the 2021 Honda Civic you have instead of the Ford. Are you free Friday at 5?",
    
    # Vague / Low Confidence
    "I might want to come look at it sometime soon.",
    "Yeah, maybe.",
    
    # Relative Logic
    "I'm busy this week. What do you have for next Monday or Tuesday morning?",
    
    # Frustrated Human (Sentiment Escalation)
    "Stop asking me about the morning. I already told you I work until 5. Is there a real person I can talk to?"
]

VEHICLE_OPTIONS = {
    "Economy / Compact": [
        ("Honda", "Fit", "LX"),
        ("Toyota", "Corolla", "LE"),
        ("Hyundai", "Elantra", "Preferred"),
        ("Kia", "Forte", "EX"),
        ("Mazda", "Mazda3", "Sport"),
        ("Volkswagen", "Golf", "Trendline"),
        ("Ford", "Focus", "SE"),
        ("Nissan", "Sentra", "SV"),
    ],

    "Sedans": [
        ("Honda", "Accord", "Touring"),
        ("Toyota", "Camry", "XSE"),
        ("Nissan", "Altima", "SV"),
        ("Hyundai", "Sonata", "Hybrid"),
        ("Volkswagen", "Jetta", "Highline"),
        ("Subaru", "Legacy", "Limited"),
        ("Mazda", "Mazda6", "GS"),
        ("Kia", "Stinger", "GT-Line"),
    ],

    "SUVs / Crossovers": [
        ("Toyota", "RAV4", "XLE"),
        ("Honda", "CR-V", "EX-L"),
        ("Mazda", "CX-5", "Signature"),
        ("Hyundai", "Tucson", "Preferred"),
        ("Ford", "Escape", "Titanium"),
        ("Subaru", "Forester", "Touring"),
        ("Nissan", "Rogue", "SL"),
        ("Chevrolet", "Equinox", "LT"),
    ],

    "Pickup Trucks": [
        ("Ford", "F-150", "XLT"),
        ("RAM", "1500", "Big Horn"),
        ("Chevrolet", "Silverado", "LTZ"),
        ("Toyota", "Tacoma", "TRD Sport"),
        ("GMC", "Sierra", "Elevation"),
        ("Nissan", "Frontier", "PRO-4X"),
        ("Ford", "Ranger", "Lariat"),
        ("Honda", "Ridgeline", "Black Edition"),
    ],

    "EVs / Hybrids": [
        ("Tesla", "Model 3", "Long Range"),
        ("Nissan", "Leaf", "SV"),
        ("Hyundai", "Ioniq 5", "Preferred AWD"),
        ("Toyota", "Prius Prime", "Upgrade"),
        ("Ford", "Mustang Mach-E", "Premium"),
        ("Kia", "EV6", "Wind AWD"),
        ("Volkswagen", "ID.4", "Pro"),
        ("Chevrolet", "Bolt", "Premier"),
    ],

    "Luxury": [
        ("BMW", "330i", "xDrive"),
        ("Mercedes-Benz", "C300", "4MATIC"),
        ("Audi", "Q5", "Technik"),
        ("Lexus", "RX 350", "Luxury"),
        ("Volvo", "XC90", "Inscription"),
        ("Acura", "RDX", "A-Spec"),
        ("Infiniti", "QX50", "Sensory"),
        ("Genesis", "GV70", "Advanced"),
    ],

    "Sports / Performance": [
        ("Ford", "Mustang", "GT"),
        ("Subaru", "WRX", "STI"),
        ("Chevrolet", "Camaro", "SS"),
        ("Dodge", "Challenger", "R/T"),
        ("Toyota", "GR86", "Premium"),
        ("Nissan", "370Z", "Sport"),
        ("BMW", "M2", "Competition"),
        ("Porsche", "718 Cayman", "Base"),
    ],

    "Budget / Older Vehicles": [
        ("Honda", "Civic", "LX"),
        ("Toyota", "Camry", "LE"),
        ("Ford", "Escape", "SE"),
        ("Hyundai", "Santa Fe", "GLS"),
        ("Mazda", "Mazda6", "GS"),
        ("Chevrolet", "Impala", "LT"),
        ("Nissan", "Altima", "S"),
        ("Kia", "Rio", "LX"),
    ],

    "High-End / Aspirational": [
        ("Porsche", "Macan", "S"),
        ("BMW", "X5", "xDrive40i"),
        ("Mercedes-Benz", "GLE", "450"),
        ("Land Rover", "Range Rover Velar", "R-Dynamic"),
        ("Tesla", "Model S", "Plaid"),
        ("Audi", "A7", "Prestige"),
        ("Lexus", "LS 500", "Executive"),
        ("Maserati", "Levante", "GranSport"),
    ],
}

DEALERSHIP_NAMES = [
    "AutoNation {city}",
    "{make} of {city}",
    "{city} Auto Mall",
    "{province} Motor Group",
    "{make} Centre {city}",
    "{city} Premium Autos",
    "{make} & More",
    "{city} Car House",
    "{province} Auto Plaza",
    "{make} Direct {city}",
]

CITIES = [
    "Toronto", "Ottawa", "Mississauga", "Brampton", "Hamilton", "London", "Markham", "Vaughan", "Kitchener", "Windsor"
]

PROVINCES = [
    "ON"
]

# utility function to generate unique IDs with a prefix
def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

# function to generate random dealership based on the make of the vehicle and random city/province
def generate_dealership(make):
    dealer_id = new_id("dealer")
    city = random.choice(CITIES)
    province = random.choice(PROVINCES)

    name_template = random.choice(DEALERSHIP_NAMES)
    dealership_name = name_template.format(make=make, city=city, province=province)

    return {
        "id": dealer_id,
        "name": dealership_name,
        "email": f"contact@{dealership_name.replace(' ', '').lower()}.com",
        "phone": f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
        "address1": f"{random.randint(10,999)} Main St",
        "address2": "",
        "city": city,
        "province": province,
        "postal_code": f"{random.choice('ABCEGHJ')}{random.randint(1,9)}{random.choice('ABCEGHJ')} {random.randint(1,9)}{random.choice('ABCEGHJ')}{random.randint(1,9)}"
    }

# function to generate random vehicle based on the VEHICLE_OPTIONS
def generate_vehicle():
    # pick a random category, then a random vehicle from that category
    category = random.choice(list(VEHICLE_OPTIONS.keys()))
    make, model, trim = random.choice(VEHICLE_OPTIONS[category])
    
    year = random.randint(2000, 2026)

    return {
        "id": new_id("vehicle"),
        "status": random.choice([0, 1]),  # new/used
        "year": year,
        "make": make,
        "model": model,
        "trim": trim,
        "mileage": f"{random.randint(20_000, 250_000)} km",
        "transmission": random.choice(["Automatic", "Manual", "CVT"]),
        "comments": random.choice([
            "",
            "",
            "",
            "Clean CarFax, one owner.",
            "Dealer maintained.",
            "Low mileage for the year.",
            "Certified pre-owned.",
            "Excellent condition.",
            "Minor cosmetic wear.",
            "Fully loaded with premium package.",
            "Recently serviced and detailed.",
        ])
    }

# function to generate notes for the lead, focusing on edge cases
def generate_notes(custom_note=None):
    if custom_note:
        return custom_note
    return random.choice(EDGE_CASES)

# function to generate random lead 
def generate_lead(custom_note=None):
    lead_id = new_id("lead")
    fname = random.choice(["John", "Alice", "Maria", "David"])
    lname = random.choice(["Doe", "Smith", "Lee", "Patel"])
    email = USER_EMAIL if USER_EMAIL else f"{fname.lower()}.{lname.lower()}@example.com"
    phone = f"555-{random.randint(100,999)}-{random.randint(1000,9999)}"
    notes = generate_notes(custom_note)
    
    return {
        "id": lead_id,
        "fname": fname,
        "lname": lname,
        "email": email,
        "phone": phone,
        "status": 0,
        "notes": notes,
        "timestamp": datetime.now().isoformat(),
    }

# function to publish the generated lead + vehicle + dealership to the service bus
def publish_to_service_bus(payload):
    client = ServiceBusClient.from_connection_string(conn_str=SERVICE_BUS_CONNECTION_STR)
    sender = client.get_queue_sender(queue_name=QUEUE_NAME)

    with sender:
        message = ServiceBusMessage(json.dumps(payload))
        sender.send_messages(message)

    print(f"[SB] Published message for lead: {payload['lead']['id']}")
    print(f"     Notes Sent: '{payload['lead']['notes']}'\n")

# main interactive worker function
def run_interactive():
    print("==================================================")
    print("  Lead Intake Simulator")
    print("==================================================")
    print("- Press [ENTER] to send a message")
    print("- Type a custom message to send a specific scenario")
    print("- Type 'q' to quit")
    print("==================================================\n")

    while True:
        try:
            user_input = input("Lead notes (or Enter for random): ").strip()
            
            if user_input.lower() == 'q':
                print("Exiting...")
                break
                
            custom_note = user_input if user_input else None

            # generate lead
            lead = generate_lead(custom_note)
            
            # generate vehicle + dealership
            vehicle = generate_vehicle()
            dealership = generate_dealership(vehicle["make"])

            # generate conversation ID
            conversation_id = new_id("conv")
            
            # publish to service bus
            payload = {
                "lead": lead,
                "vehicle": vehicle,
                "dealership": dealership,
                "conversationId": conversation_id
            }
            publish_to_service_bus(payload)

        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    run_interactive()