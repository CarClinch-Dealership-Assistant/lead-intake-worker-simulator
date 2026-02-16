from azure.servicebus import ServiceBusClient, ServiceBusReceiveMode
import os
from dotenv import load_dotenv

load_dotenv()

CONN = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE = "leads"

client = ServiceBusClient.from_connection_string(CONN)

with client:
    receiver = client.get_queue_receiver(
        queue_name=QUEUE,
        receive_mode=ServiceBusReceiveMode.RECEIVE_AND_DELETE
    )

    with receiver:
        print("Purging messages...")
        while True:
            msgs = receiver.receive_messages(max_message_count=50, max_wait_time=1)
            if not msgs:
                break
            print(f"Deleted {len(msgs)} messages")

print("Queue is now empty.")
