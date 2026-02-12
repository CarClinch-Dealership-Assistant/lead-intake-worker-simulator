CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    fname TEXT,
    lname TEXT,
    email TEXT,
    phone TEXT,
    vehicle TEXT,
    wants_email BOOLEAN,
    notes TEXT,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    lead_id TEXT REFERENCES leads(lead_id),
    status INT,
    created_at TIMESTAMP,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(conversation_id),
    direction INT,
    body TEXT,
    created_at TIMESTAMP
);
