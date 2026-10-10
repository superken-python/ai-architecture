import json
import os
from pydantic import TypeAdapter
from rvt_contracts.messages import ClientEvent, ServerEvent

def main():
    os.makedirs("web/src/contracts", exist_ok=True)
    
    # Generate JSON schema for ClientEvent
    client_adapter = TypeAdapter(ClientEvent)
    client_schema = client_adapter.json_schema()
    with open("web/src/contracts/ClientEvent.json", "w") as f:
        json.dump(client_schema, f, indent=2)

    # Generate JSON schema for ServerEvent
    server_adapter = TypeAdapter(ServerEvent)
    server_schema = server_adapter.json_schema()
    with open("web/src/contracts/ServerEvent.json", "w") as f:
        json.dump(server_schema, f, indent=2)

    print("Generated JSON schemas in web/src/contracts")

if __name__ == "__main__":
    main()
