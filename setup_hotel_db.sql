-- Step 1: Create database and use it
CREATE DATABASE IF NOT EXISTS hotel_mgmt;
USE hotel_mgmt;

-- Step 2: Table for hotel and room info
CREATE TABLE IF NOT EXISTS hotels (
    hotel_id INT AUTO_INCREMENT PRIMARY KEY,
    hotel_name VARCHAR(255),
    room_number INT
);

-- Step 3: Table for booking status and tracking
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    hotel_id INT,
    room_number INT,
    status ENUM('available', 'reserved', 'permanently_booked', 'cleaning') DEFAULT 'available',
    reserved_at DATETIME DEFAULT NULL,
    checkout_date DATE DEFAULT NULL,
    FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id)
);

-- Step 4: Insert 3 hotels with 5 rooms each
INSERT INTO hotels (hotel_name, room_number)
VALUES 
('Hotel Sunshine', 101), ('Hotel Sunshine', 102), ('Hotel Sunshine', 103), ('Hotel Sunshine', 104), ('Hotel Sunshine', 105),
('Grand Palace', 201), ('Grand Palace', 202), ('Grand Palace', 203), ('Grand Palace', 204), ('Grand Palace', 205),
('Seaside Resort', 301), ('Seaside Resort', 302), ('Seaside Resort', 303), ('Seaside Resort', 304), ('Seaside Resort', 305);

-- Step 5: Sync initial booking statuses
INSERT INTO bookings (hotel_id, room_number)
SELECT h.hotel_id, h.room_number 
FROM hotels h
WHERE NOT EXISTS (
    SELECT 1 FROM bookings b 
    WHERE b.hotel_id = h.hotel_id AND b.room_number = h.room_number
);

-- Step 6: Enable Event Scheduler
SET GLOBAL event_scheduler = ON;

-- Step 7: Create event to expire reserved rooms after 10 minutes
DELIMITER $$
CREATE EVENT IF NOT EXISTS expire_reserved_rooms
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
    UPDATE bookings
    SET status = 'available',
        reserved_at = NULL
    WHERE status = 'reserved'
      AND TIMESTAMPDIFF(MINUTE, reserved_at, NOW()) >= 10;
END$$
DELIMITER ;

-- Step 8: Create event to switch to cleaning on checkout day
DELIMITER $$
CREATE EVENT IF NOT EXISTS move_to_cleaning_after_checkout
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
    UPDATE bookings
    SET status = 'cleaning'
    WHERE status = 'permanently_booked'
      AND checkout_date IS NOT NULL
      AND CURDATE() >= checkout_date;
END$$
DELIMITER ;

-- Step 9: Create event to make room available 10 minutes after cleaning
DELIMITER $$
CREATE EVENT IF NOT EXISTS clean_rooms_after_checkout
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
    UPDATE bookings
    SET status = 'available',
        reserved_at = NULL,
        checkout_date = NULL
    WHERE status = 'cleaning'
      AND TIMESTAMPDIFF(MINUTE, CONCAT(checkout_date, ' 00:00:00'), NOW()) >= 10;
END$$
DELIMITER ;
