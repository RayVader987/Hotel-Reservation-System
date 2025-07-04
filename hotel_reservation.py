from datetime import datetime
import time
import threading
import re
import ssl
import requests
import db_config

# Fast2SMS configuration
FAST2SMS_API_KEY = "Replace with your API here"  # Replace with your actual API key
FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"

INDIAN_PHONE_REGEX = r"^(\+91)?[6-9]\d{9}$"

def get_hotels(cursor):
    cursor.execute("SELECT DISTINCT hotel_name FROM hotels")
    return [row[0] for row in cursor.fetchall()]

def get_available_rooms(cursor, hotel_name):
    cursor.execute("""
        SELECT h.room_number 
        FROM hotels h 
        JOIN bookings b ON h.hotel_id = b.hotel_id 
        WHERE h.hotel_name = %s AND b.status = 'available'
    """, (hotel_name,))
    return [row[0] for row in cursor.fetchall()]

def get_hotel_id(cursor, hotel_name, room_number):
    cursor.execute("SELECT hotel_id FROM hotels WHERE hotel_name=%s AND room_number=%s", (hotel_name, room_number))
    return cursor.fetchone()[0]

def reserve_room(cursor, conn, hotel_id, room_number):
    now = datetime.now()
    cursor.execute("""
        UPDATE bookings 
        SET status='reserved', reserved_at=%s 
        WHERE hotel_id=%s AND room_number=%s AND status='available'
    """, (now, hotel_id, room_number))
    conn.commit()
    print(f"Room {room_number} reserved. You have 10 minutes to confirm it.")

def send_sms_notification(phone_number, message):
    try:
        payload = {
            'route': 'q',
            'message': message,
            'language': 'english',
            'flash': 0,
            'numbers': phone_number.replace("+91", ""),
        }

        headers = {
            'authorization': FAST2SMS_API_KEY,
            'Content-Type': "application/x-www-form-urlencoded"
        }

        response = requests.post(FAST2SMS_URL, data=payload, headers=headers)
        if response.status_code == 200:
            print("SMS notification sent.")
        else:
            print(f"Failed to send SMS. Response: {response.text}")
    except Exception as e:
        print(f"Error sending SMS: {e}")

def confirm_reservation(cursor, conn, hotel_id, room_number):
    cursor.execute("""
        UPDATE bookings 
        SET status='permanently_booked', reserved_at=NULL 
        WHERE hotel_id=%s AND room_number=%s AND status='reserved'
    """, (hotel_id, room_number))
    conn.commit()
    print(f"Room {room_number} is now permanently booked.")

def main():
    conn = db_config.get_connection()
    cursor = conn.cursor()

    hotels = get_hotels(cursor)
    print("Available hotels:")
    for i, h in enumerate(hotels, start=1):
        print(f"{i}. {h}")

    hotel_choice = int(input("Select a hotel: ")) - 1
    selected_hotel = hotels[hotel_choice]

    available_rooms = get_available_rooms(cursor, selected_hotel)
    if not available_rooms:
        print("No available rooms in this hotel.")
        return

    print("Available rooms:", available_rooms)
    room_number = int(input("Select a room number: "))

    hotel_id = get_hotel_id(cursor, selected_hotel, room_number)

    choice = input("Do you want to permanently book or reserve this room? (permanent/reserve): ").lower()

    if choice == 'permanent':
        checkout_input = input("Enter checkout date (YYYY-MM-DD): ")
        try:
            checkout_date = datetime.strptime(checkout_input, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Booking cancelled.")
            return

        cursor.execute("""
            UPDATE bookings 
            SET status='permanently_booked', checkout_date=%s 
            WHERE hotel_id=%s AND room_number=%s AND status='available'
        """, (checkout_date, hotel_id, room_number))
        conn.commit()
        print(f"Room {room_number} permanently booked till {checkout_date}.")

    elif choice == 'reserve':
        phone_number = input("Enter your phone number with country code (e.g., +91XXXXXXXXXX): ").strip()
        while not re.match(INDIAN_PHONE_REGEX, phone_number):
            print("Invalid phone number format. Try again.")
            phone_number = input("Enter your phone number with country code (e.g., +91XXXXXXXXXX): ").strip()

        reserve_room(cursor, conn, hotel_id, room_number)

        print("\nYou can come back within 10 minutes to confirm your reservation.")
        print("Note: You will receive an SMS reminder when only 4 minutes are left.")

        def background_sms():
            time.sleep(360)  # 6 minutes
            send_sms_notification(phone_number, "Only 4 minutes left to confirm your hotel room booking!")

        threading.Thread(target=background_sms, daemon=True).start()
        print("\nThe system is now ready for the next customer...\n")

    conn.close()

if __name__ == "__main__":
    main()
