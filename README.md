# Lead Intake Worker Simulator

> **Note**: This worker connects directly to your active Cosmos DB to fetch live vehicles and their exact dealerships. It allows you to test end-to-end conversation flows, edge cases, and AI responses interactively.

## Example Message

```json
{
    "lead": {
        "id": "lead_c47f91a953",
        "fname": "Alice",
        "lname": "Smith",
        "email": "alice.smith@example.com",
        "phone": "555-307-8655",
        "status": 0,
        "notes": "Let's do November 31st at 10 AM.",
        "timestamp": "2026-02-16T10:30:54.198014"
    },
    "vehicle": {
        "id": "vehicle_599cae2001",
        "status": 1,
        "year": 2020,
        "make": "Kia",
        "model": "Stinger",
        "trim": "GT-Line",
        "mileage": "146612 km",
        "transmission": "Manual",
        "comments": "Low mileage for the year."
    },
    "dealership": {
        "id": "dealer_82f7ad2124",
        "name": "Kia Direct Montreal",
        "email": "contact@kiadirectmontreal.com",
        "phone": "555-335-9346",
        "address1": "376 Main St",
        "address2": "",
        "city": "Montreal",
        "province": "QC",
        "postal_code": "B9B 8H3"
    },
    "conversationId": "conv_66e8be1f55"
}
```

---

## Env Variables

Copy the provided template:

```bash
# for live Azure infra
cp .env.example.azure .env
# OR for local infra
cp .env.example.local .env
```

### Azure Variables
If running with live Azure infra, open `.env` and update the following values:

#### **`SERVICE_BUS_CONNECTION_STRING`**
In the /infra/terraform directory of `carclinch-dealership-assistant`, after the Terraform infrastructure is deployed, run:
```
terraform output servicebus_connection_string
```

#### **`COSMOS_ENDPOINT` & `COSMOS_KEY`**
In the /infra/terraform directory of `carclinch-dealership-assistant`, after the Terraform infrastructure is deployed, run:
```
terraform output cosmos_endpoint
terraform output cosmos_primary_key
```

### Local Variables
If running with local infra, update the following values:
#### **`OPENAI_MODEL_NAME`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`**
To find the OPENAI env variables, make sure to create the Foundry resource, deploy the gpt-4.1-mini model, and find the values in `Foundry` -> `Playgrounds` -> `View Code` -> Scroll down and copy paste the key and URL values.

#### **`GMAIL_USER`, `GMAIL_APP_PASSWORD`**
Create an app password for your personal Gmail inbox by going to `Manage your Google Account` -> `Security & sign-in` -> Search `App passwords` -> Create a new one. OR use the one I shared with the team before.

The GMAIL values are your email address and that created app password with no spaces.

#### **`AZURE_COSMOS_EMULATOR_IP_ADDRESS_OVERRIDE`**
Your WiFi IPv4 address found by running:
```
ipconfigs
```
---

## Local Setup (Docker)

This project is configured to spin up the entire pipeline for local testing. If you are using live Azure infra, **skip this step.** From the project root, run:

```bash
docker compose up -d
```

This launches:
- SQL Server & Azure Service Bus Emulator
- Azurite & Cosmos DB Emulator
- The **Email Processing Service** (listens for messages)

To seed the emulated Cosmos DB, run:
```
py init.py
```

---

## Run the Worker


```bash
python -m venv .venv
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

**Windows PowerShell**
```powershell
.venv\Scripts\Activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

```
py worker.py
```

```text
==================================================
  Lead Intake Simulator (Live DB Connection)
==================================================
Enter Lead Information (Press ENTER to use random defaults):
First Name [Alice]: 
Last Name [Smith]: 
Email [alice.smith@example.com]: 
Phone [555-000-0000]: 

--------------------------------------------------
- Press [ENTER] to send a random edge case
- Type a custom message to send a specific scenario
- Type 'q' to quit
--------------------------------------------------

Lead notes (or Enter for random): 
```

Whenever you submit a note, the worker will pull a random vehicle from Cosmos DB, find its matching dealership, and push the payload to the Service Bus.

---

## Utilities

### Peek inside the queue (optional)
Use the included `peek.py` script to inspect messages currently sitting in the Service Bus without consuming them:
```bash
python peek.py
```

### Purge the queue (optional)
Use the included `purge.py` script to instantly clear all stuck/pending messages in the queue:
```bash
python purge.py
```