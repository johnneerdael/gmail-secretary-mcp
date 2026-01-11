-- Contacts table: stores all people we've communicated with
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- Statistics
    email_count INT DEFAULT 0,
    last_email_date TIMESTAMP,
    first_email_date TIMESTAMP,
    
    -- Categorization
    is_vip BOOLEAN DEFAULT FALSE,
    is_internal BOOLEAN DEFAULT FALSE,
    organization VARCHAR(255),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            coalesce(display_name, '') || ' ' || 
            coalesce(email, '') || ' ' ||
            coalesce(organization, '')
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_last_email_date ON contacts(last_email_date DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_email_count ON contacts(email_count DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_search_vector ON contacts USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_contacts_is_vip ON contacts(is_vip) WHERE is_vip = TRUE;

-- Contact interactions: tracks each email exchange
CREATE TABLE IF NOT EXISTS contact_interactions (
    id SERIAL PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    email_uid INT NOT NULL,
    email_folder VARCHAR(100) NOT NULL,
    
    -- Interaction type
    direction VARCHAR(10) NOT NULL, -- 'sent', 'received', 'cc', 'bcc'
    
    -- Email metadata
    subject TEXT,
    email_date TIMESTAMP NOT NULL,
    message_id VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_interaction UNIQUE (contact_id, email_uid, email_folder, direction)
);

CREATE INDEX IF NOT EXISTS idx_contact_interactions_contact_id ON contact_interactions(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_interactions_email_date ON contact_interactions(email_date DESC);
CREATE INDEX IF NOT EXISTS idx_contact_interactions_email_uid ON contact_interactions(email_uid, email_folder);

-- Contact notes: manual notes about contacts
CREATE TABLE IF NOT EXISTS contact_notes (
    id SERIAL PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contact_notes_contact_id ON contact_notes(contact_id);

-- Contact tags: flexible categorization
CREATE TABLE IF NOT EXISTS contact_tags (
    id SERIAL PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_contact_tag UNIQUE (contact_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_contact_tags_contact_id ON contact_tags(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_tags_tag ON contact_tags(tag);
