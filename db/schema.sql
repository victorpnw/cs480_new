-- 1. Defect Master Table
CREATE TABLE defects (
    id SERIAL PRIMARY KEY,
    defect_code VARCHAR(50) NOT NULL UNIQUE, -- Business Key
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Lot Master Table
CREATE TABLE lots (
    id SERIAL PRIMARY KEY,
    lot_id VARCHAR(100) NOT NULL UNIQUE, -- Business Key
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Inspection Records (Transactional Table)
CREATE TABLE inspection_records (
    id SERIAL PRIMARY KEY,
    inspection_id VARCHAR(100) NOT NULL UNIQUE, -- AC requirement: surrogate PK 'id' + UNIQUE inspection_id
    lot_id INTEGER NOT NULL,
    defect_id INTEGER NOT NULL,
    inspection_date DATE NOT NULL,
    qty_defects INTEGER NOT NULL CHECK (qty_defects >= 0),
    is_data_complete BOOLEAN DEFAULT TRUE,
    
    -- FKs with Cascade Delete
    CONSTRAINT fk_lot 
        FOREIGN KEY (lot_id) REFERENCES lots(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_defect 
        FOREIGN KEY (defect_id) REFERENCES defects(id) 
        ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_ir_date ON inspection_records(inspection_date);
CREATE INDEX idx_ir_defect_lookup ON inspection_records(defect_id, inspection_date);
