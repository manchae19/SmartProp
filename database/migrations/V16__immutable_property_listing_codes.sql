-- Apply while property writes are paused. Keep the allocation ledger when deleting listings.
CREATE TABLE property_listing_code_allocations (
  sequence_no BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  issued_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
  CONSTRAINT uq_listing_allocation_property UNIQUE (property_id)
) ENGINE=InnoDB;

ALTER TABLE properties
  ADD COLUMN listing_code VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL;

INSERT INTO property_listing_code_allocations (property_id)
SELECT id FROM properties ORDER BY created_at, id;

UPDATE properties p
JOIN property_listing_code_allocations a ON a.property_id = p.id
SET p.listing_code = CONCAT('SP', LPAD(CAST(a.sequence_no AS CHAR),
    GREATEST(3, CHAR_LENGTH(CAST(a.sequence_no AS CHAR))), '0'));

ALTER TABLE properties
  MODIFY COLUMN listing_code VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  ADD CONSTRAINT uq_properties_listing_code UNIQUE (listing_code);

DELIMITER $$
CREATE TRIGGER properties_listing_code_insert
BEFORE INSERT ON properties FOR EACH ROW
BEGIN
  DECLARE allocated BIGINT UNSIGNED;
  INSERT INTO property_listing_code_allocations (property_id) VALUES (NEW.id);
  SET allocated = LAST_INSERT_ID();
  SET NEW.listing_code = CONCAT('SP', LPAD(CAST(allocated AS CHAR),
      GREATEST(3, CHAR_LENGTH(CAST(allocated AS CHAR))), '0'));
END$$

CREATE TRIGGER properties_listing_code_update
BEFORE UPDATE ON properties FOR EACH ROW
BEGIN
  IF NOT (NEW.listing_code <=> OLD.listing_code) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'listing_code is immutable';
  END IF;
END$$
DELIMITER ;
