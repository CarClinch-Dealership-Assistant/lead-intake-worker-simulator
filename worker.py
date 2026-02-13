import time
import uuid
import random
from datetime import datetime
import psycopg2
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os
from dotenv import load_dotenv

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "local",
    "host": "localhost",
    "port": 5432,
}

# Load environment variables from .env file
load_dotenv()


# For local development, we use the Azure Service Bus emulator connection string
SERVICE_BUS_CONNECTION_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = "leads"
INTERVAL_SECONDS = int(os.getenv("INTERVAL")) 

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
    "Toronto", "Ottawa", "Vancouver", "Calgary", "Edmonton",
    "Montreal", "Winnipeg", "Halifax", "Regina", "Saskatoon"
]

PROVINCES = [
    "ON", "BC", "AB", "QC", "MB", "NS", "SK"
]


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def generate_dealership(dealer_id, make):
    city = random.choice(CITIES)
    province = random.choice(PROVINCES)

    name_template = random.choice(DEALERSHIP_NAMES)
    dealership_name = name_template.format(make=make, city=city, province=province)

    return {
        "name": dealership_name,
        "email": f"contact@{dealership_name.replace(' ', '').lower()}.com",
        "phone": f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
        "address1": f"{random.randint(10,999)} Main St",
        "address2": "",
        "city": city,
        "province": province,
        "postal_code": f"{random.choice('ABCEGHJ')}{random.randint(1,9)}{random.choice('ABCEGHJ')} {random.randint(1,9)}{random.choice('ABCEGHJ')}{random.randint(1,9)}"
    }

def generate_vehicle():
    # Pick a random category, then a random vehicle tuple
    category = random.choice(list(VEHICLE_OPTIONS.keys()))
    make, model, trim = random.choice(VEHICLE_OPTIONS[category])

    dealer_id = random.randint(1, 200)

    # Mock dealership lookup
    dealership = generate_dealership(dealer_id, make)
    
    year = random.randint(2000, 2026)

    return {
        "dealership": dealership,
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
        ]),
        "category": category  
    }


def insert_lead(conn):
    lead_id = random.randint(1, 999999)
    fname = random.choice(["John", "Alice", "Maria", "David"])
    lname = random.choice(["Doe", "Smith", "Lee", "Patel"])
    email = f"{fname.lower()}.{lname.lower()}@example.com"
    phone = "123-456-7890"
    
    # For testing, we can generate a vehicle object even if we aren't inserting into the DB, since the Service Bus message will include it and the downstream consumer can handle it accordingly. In production, we would want to ensure the vehicle is created in the DB first and we have a valid vehicle_id to reference.
    vehicle = generate_vehicle()
    
    status = 0 # New lead
    wants_email = random.choice([True, False])
    # Used AI to generate a variety of notes for context testing
    notes = random.choice([
        "Interested in availability",
        "Wants financing options",
        "Asked about trade-in",
        "Looking to schedule a test drive this week",
        "Wants to compare this model with similar vehicles",
        "Concerned about mileage and maintenance history",
        "Asking whether the vehicle has been in any accidents",
        "Wants to know total out-the-door pricing",
        "Checking if the vehicle is still under manufacturer warranty",
        "Interested in monthly payment estimates",
        "Wants to see interior photos or a video walkthrough",
        "Asking about delivery options for out-of-town buyers",
        "Wants to negotiate the listed price",
        "Inquiring about available color options",
        "Wants to confirm if the vehicle supports Apple CarPlay/Android Auto",
        "Asking whether winter tires are included",
        "Wants to know if the dealership accepts cryptocurrency",
        "Concerned about credit score and financing approval",
        "Asking if extended warranty packages are available",
        "Wants to reserve the vehicle with a deposit",
        "Inquiring about previous owner history",
        "Wants to know if the vehicle can tow a small trailer",
        "Asking about insurance cost estimates",
        "Wants to bring a mechanic to inspect the vehicle",
        "Looking for a family-friendly vehicle with good safety ratings",
        "Asking if the dealership offers student or military discounts",
        "Wants to upgrade from their current vehicle and needs recommendations",
        "Asking about hybrid vs. gas model differences",
        "Wants to confirm if the vehicle has remote start",
        "Looking for a quick purchase and wants paperwork prepared in advance",
    ])
    created_at = datetime.now()

    # with conn.cursor() as cur:
    #     cur.execute(
    #         """
    #         INSERT INTO leads (lead_id, fname, lname, email, phone, vehicle, wants_email, notes, created_at)
    #         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    #         """,
    #         (lead_id, fname, lname, email, phone, vehicle, wants_email, notes, created_at),
    #     )
    #     conn.commit()

    # print(f"[DB] Inserted lead: {lead_id}")
    return {
        "lead_id": lead_id,
        "fname": fname,
        "lname": lname,
        "email": email,
        "phone": phone,
        "status": status,
        "vehicle": vehicle,
        "wants_email": wants_email,
        "notes": notes,
        "created_at": created_at.isoformat(),
    }


def create_conversation(conn, lead_id):
    conversation_id = f"{random.randint(0, 999):03d}"
    now = datetime.now()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversations (conversation_id, lead_id, status, created_at, last_updated)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (conversation_id, lead_id, 1, now, now),
        )
        conn.commit()

    print(f"[DB] Created conversation: {conversation_id}")
    return conversation_id


def publish_to_service_bus(payload):
    client = ServiceBusClient.from_connection_string(conn_str=SERVICE_BUS_CONNECTION_STR)
    sender = client.get_queue_sender(queue_name=QUEUE_NAME)

    with sender:
        message = ServiceBusMessage(str(payload))
        sender.send_messages(message)

    print(f"[SB] Published message for lead: {payload['lead_id']}")


def simulate_worker():
    print("Starting lead simulation worker...")
    print(f"Interval: {INTERVAL_SECONDS} seconds\n")

    while True:
        try:
            conn = None
            # conn = get_db_connection()

            # Insert lead
            lead = insert_lead(conn)
            
            # For testing, we can generate a conversation ID even if we aren't inserting into the DB, since the Service Bus message will include it and the downstream consumer can handle it accordingly. In production, we would want to ensure the conversation is created in the DB first.
            conversation_id = f"{random.randint(0, 999):03d}"

            # Create conversation if needed
            # conversation_id = None
            # if lead["wants_email"]:
            #     conversation_id = create_conversation(conn, lead["lead_id"])

            # Publish to Service Bus
            publish_payload = {
                "lead_id": lead["lead_id"],
                "conversation_id": conversation_id,
                "fname": lead["fname"],
                "lname": lead["lname"],
                "email": lead["email"],
                "vehicle": lead["vehicle"],
                "notes": lead["notes"],
                "created_at": lead["created_at"],
            }

            publish_to_service_bus(publish_payload)

            #conn.close()

        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    simulate_worker()
