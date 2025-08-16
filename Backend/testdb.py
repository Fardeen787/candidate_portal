import mysql.connector
from mysql.connector import Error
import json

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'hiring_bot'
}

def check_ticket(ticket_id):
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        print(f"Checking ticket: {ticket_id}")
        print("="*60)
        
        # 1. Check main ticket record
        print("\n1. TICKET RECORD:")
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        if ticket:
            print("✅ Ticket found in database!")
            for key, value in ticket.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Ticket not found!")
            return
        
        # 2. Check ticket details
        print("\n2. TICKET DETAILS:")
        cursor.execute("""
            SELECT field_name, field_value, created_at, is_initial
            FROM ticket_details
            WHERE ticket_id = %s
            ORDER BY created_at
        """, (ticket_id,))
        
        details = cursor.fetchall()
        if details:
            print(f"✅ Found {len(details)} detail records:")
            for detail in details:
                print(f"   - {detail['field_name']}: {detail['field_value']}")
                print(f"     (Created: {detail['created_at']}, Initial: {detail['is_initial']})")
        
        # 3. Check ticket history
        print("\n3. TICKET HISTORY:")
        cursor.execute("""
            SELECT field_name, old_value, new_value, changed_by, changed_at, change_type
            FROM ticket_history
            WHERE ticket_id = %s
            ORDER BY changed_at
        """, (ticket_id,))
        
        history = cursor.fetchall()
        if history:
            print(f"✅ Found {len(history)} history records:")
            for h in history:
                print(f"   - {h['field_name']}: {h['old_value']} → {h['new_value']}")
                print(f"     (By: {h['changed_by']}, Type: {h['change_type']}, At: {h['changed_at']})")
        
        # 4. Check the chat session that created this ticket
        print("\n4. RELATED CHAT SESSION:")
        cursor.execute("""
            SELECT cs.*, COUNT(cm.message_id) as message_count
            FROM chat_sessions cs
            LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
            WHERE cs.session_id = %s
            GROUP BY cs.session_id
        """, (ticket.get('session_id'),))
        
        session = cursor.fetchone()
        if session:
            print(f"✅ Found chat session: {session['session_id']}")
            print(f"   User: {session['user_id']}")
            print(f"   Messages: {session['message_count']}")
            print(f"   Started: {session['started_at']}")
        
        # 5. Show all messages in this conversation
        print("\n5. CONVERSATION MESSAGES:")
        cursor.execute("""
            SELECT sender_type, message_content, timestamp
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY timestamp
        """, (ticket.get('session_id'),))
        
        messages = cursor.fetchall()
        print(f"Found {len(messages)} messages:")
        for i, msg in enumerate(messages, 1):
            print(f"\n   [{i}] {msg['sender_type'].upper()} ({msg['timestamp']}):")
            print(f"   {msg['message_content'][:100]}...")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ VERIFICATION COMPLETE")
        print(f"Ticket {ticket_id} is properly stored in the database!")
        
    except Error as e:
        print(f"Database error: {e}")

# Check your specific ticket
if __name__ == "__main__":
    check_ticket("bfef627871")
    
    # Also show summary of all tickets
    print("\n\nSUMMARY OF ALL TICKETS:")
    print("="*60)
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                source, 
                COUNT(*) as count,
                MAX(created_at) as latest
            FROM tickets
            GROUP BY source
        """)
        
        for row in cursor.fetchall():
            print(f"{row['source']}: {row['count']} tickets (latest: {row['latest']})")
        
        # Show recent chat tickets
        print("\nRecent tickets from chat:")
        cursor.execute("""
            SELECT ticket_id, subject, created_at, approval_status
            FROM tickets
            WHERE source = 'chat'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        for ticket in cursor.fetchall():
            print(f"  - {ticket['ticket_id']}: {ticket['subject']} ({ticket['approval_status']})")
        
        cursor.close()
        conn.close()
        
    except Error as e:
        print(f"Error: {e}")