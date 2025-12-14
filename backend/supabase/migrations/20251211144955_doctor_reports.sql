-- Create doctor_reports table to store verification results
CREATE TABLE doctor_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verification_id VARCHAR(255) NOT NULL UNIQUE,

    -- Full Name verification fields
    full_name_input VARCHAR(255),
    full_name_scraped VARCHAR(255),
    full_name_scraped_from VARCHAR(500),
    full_name_matches BOOLEAN,
    
    -- Specialty verification fields
    specialty_input VARCHAR(255),
    specialty_scraped VARCHAR(255),
    specialty_scraped_from VARCHAR(500),
    specialty_matches BOOLEAN,
    
    -- Address verification fields
    address_input TEXT,
    address_scraped TEXT,
    address_scraped_from VARCHAR(500),
    address_matches BOOLEAN,
    
    -- Phone Number verification fields
    phone_number_input VARCHAR(255),
    phone_number_scraped VARCHAR(255),
    phone_number_scraped_from VARCHAR(500),
    phone_number_matches BOOLEAN,
    
    -- License Number verification fields
    license_number_input VARCHAR(255),
    license_number_scraped VARCHAR(255),
    license_number_scraped_from VARCHAR(500),
    license_number_matches BOOLEAN,
    
    -- Insurance Networks verification fields
    insurance_networks_input JSONB,
    insurance_networks_scraped JSONB,
    insurance_networks_scraped_from VARCHAR(500),
    insurance_networks_matches BOOLEAN,
    
    -- Services Offered verification fields
    services_offered_input JSONB,
    services_offered_scraped JSONB,
    services_offered_scraped_from VARCHAR(500),
    services_offered_matches BOOLEAN,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_doctor_reports_verification_id ON doctor_reports(verification_id);
CREATE INDEX idx_doctor_reports_full_name_input ON doctor_reports(full_name_input);
CREATE INDEX idx_doctor_reports_specialty_input ON doctor_reports(specialty_input);
CREATE INDEX idx_doctor_reports_created_at ON doctor_reports(created_at);

-- Create trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_doctor_reports_updated_at
    BEFORE UPDATE ON doctor_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();