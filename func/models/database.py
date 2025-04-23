import psycopg2
from func.constants import DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT, DATABASE_TIMEOUT
from datetime import datetime

class Database:
    def __init__(self, database_name=DATABASE_NAME, user=DATABASE_USERNAME, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT, timeout=DATABASE_TIMEOUT):
        self.database = database_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None
        self.c = None
        self.result = None
        self.timeout = timeout
        
        self.connect()
        self.init()

    def connect(self):
        if not self.conn or self.conn.closed:
            try:
                print(f"Connecting to database {self.database} (User: {self.user}, Password: {self.password}, Host: {self.host})...")
                self.conn = psycopg2.connect(
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port
                )
                self.c = self.conn.cursor()
                self.c.execute(f"SET statement_timeout = {self.timeout};")
            except psycopg2.OperationalError as e:
                print(f"Error: Unable to connect to the self. {e}")
                raise e
            else:
                print("Database connection successful!")

    def alter(self, query: str, params=()):
        if not query or params is None:
            raise ValueError("Query and parameters cannot be empty.")
        
        self.connect()
        if ";" not in query:
            query += ";"

        try:
            self.c.execute(query, params)
            self.conn.commit()

            # Record it in logs/db_alters.log in this format: [date, time] - query using datetime
            with open("logs/db_alters.log", "a") as log_file:
                log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - {query}\n")

        except Exception as e:
            print(f"Failed to alter the database due to {e}, query: {query}")
            self.conn.rollback()
            return None

    def init(self):
        try:
            # Create users table
            self.query("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    username VARCHAR(30) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255),
                    bio TEXT,
                    is_private BOOLEAN DEFAULT FALSE,
                    avatar_id VARCHAR(36),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    google_id VARCHAR(255) UNIQUE,
                    apple_id VARCHAR(255) UNIQUE,
                    FOREIGN KEY (avatar_id) REFERENCES media(id) ON DELETE SET NULL
                )
            """)
            print("Created users table.")
            
            # Create follows table
            self.query("""
                CREATE TABLE IF NOT EXISTS follows (
                    follower_id VARCHAR(36) NOT NULL,
                    followee_id VARCHAR(36) NOT NULL,
                    accepted BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (follower_id, followee_id),
                    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created follows table.")
            
            # Create interests table
            self.query("""
                CREATE TABLE IF NOT EXISTS interests (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT
                )
            """)
            print("Created interests table.")
            
            # Create user_interests table
            self.query("""
                CREATE TABLE IF NOT EXISTS user_interests (
                    user_id VARCHAR(36) NOT NULL,
                    interest_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (user_id, interest_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE
                )
            """)
            print("Created user_interests table.")
            
            # Create media table
            self.query("""
                CREATE TABLE IF NOT EXISTS media (
                    id VARCHAR(36) PRIMARY KEY,
                    media_type VARCHAR(20) NOT NULL,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Created media table.")
            
            # Create chat_rooms table
            self.query("""
                CREATE TABLE IF NOT EXISTS chat_rooms (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    is_private BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    admin_id VARCHAR(36) NOT NULL,
                    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created chat_rooms table.")
            
            # Create user_chat_rooms table
            self.query("""
                CREATE TABLE IF NOT EXISTS user_chat_rooms (
                    user_id VARCHAR(36) NOT NULL,
                    chat_room_id VARCHAR(36) NOT NULL,
                    accepted BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (user_id, chat_room_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
                )
            """)
            print("Created user_chat_rooms table.")
            
            # Create messages table
            self.query("""
                CREATE TABLE IF NOT EXISTS messages (
                    id VARCHAR(36) PRIMARY KEY,
                    chat_room_id VARCHAR(36) NOT NULL,
                    content TEXT,
                    sender_id VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created messages table.")
            
            # Create message_read_by table
            self.query("""
                CREATE TABLE IF NOT EXISTS message_read_by (
                    message_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    read_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id, user_id),
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created message_read_by table.")
            
            # Create message_media table
            self.query("""
                CREATE TABLE IF NOT EXISTS message_media (
                    message_id VARCHAR(36) NOT NULL,
                    media_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (message_id, media_id),
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE SET NULL
                )
            """)
            print("Created message_media table.")
            
            # Create posts table
            self.query("""
                CREATE TABLE IF NOT EXISTS posts (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created posts table.")
            
            # Create post_media table
            self.query("""
                CREATE TABLE IF NOT EXISTS post_media (
                    post_id VARCHAR(36) NOT NULL,
                    media_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (post_id, media_id),
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE SET NULL
                )
            """)
            print("Created post_media table.")
            
            # Create post_interests table
            self.query("""
                CREATE TABLE IF NOT EXISTS post_interests (
                    post_id VARCHAR(36) NOT NULL,
                    interest_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (post_id, interest_id),
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE
                )
            """)
            print("Created post_interests table.")
            
            # Create comments table
            self.query("""
                CREATE TABLE IF NOT EXISTS comments (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    post_id VARCHAR(36) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
                )
            """)
            print("Created comments table.")

            # Create post_likes table
            self.query("""
                CREATE TABLE IF NOT EXISTS post_likes (
                    post_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (post_id, user_id),
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Created post_likes table.")
            
            # Create post_chat_rooms table
            self.query("""
                CREATE TABLE IF NOT EXISTS post_chat_rooms (
                    post_id VARCHAR(36) NOT NULL,
                    chat_room_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (post_id, chat_room_id),
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
                )
            """)
            print("Created post_chat_rooms table.")

            self.query("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            print("Created subscriptions table.")

            self.query("""
                CREATE TABLE IF NOT EXISTS payments (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    amount FLOAT NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            print("Created payments table.")

            self.query("""
                CREATE TABLE IF NOT EXISTS subscription_payments (
                    subscription_id VARCHAR(36) NOT NULL,
                    payment_id VARCHAR(36) NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (subscription_id, payment_id),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
                    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
                )
            """)
            print("Created subscription_payments table.")

            self.query("""
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    subscription_id VARCHAR(255) NOT NULL,
                    plan_id VARCHAR(255) NOT NULL,
                    cycles INT DEFAULT 0,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
            )""")
            print("Created subscription_plans table.")

            self.query("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    icon_id VARCHAR(36),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (icon_id) REFERENCES media(id) ON DELETE SET NULL
                )
            """)
            print("Created notifications table.")
            
            # Create indices for performance
            self.query("""
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
                CREATE INDEX IF NOT EXISTS idx_users_apple_id ON users(apple_id);
                CREATE INDEX IF NOT EXISTS idx_messages_chat_room_id ON messages(chat_room_id);
                CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
                CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
            """)
            print("Created indices")
            self.query("""
            CREATE TABLE IF NOT EXISTS user_embeddings (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL UNIQUE,
                embedding FLOAT[] NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("Created user_embeddings table.")
            print("Database initialization completed successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise
    
    def select(self, query: str, params=(), limit: int = 0):
        if not query or params is None:
            raise ValueError("Query and parameters cannot be empty.")
        
        self.connect()
        if ";" not in query:
            query += ";"

        query = query.replace("?", "%s")

        try:
            self.c.execute(query, params)
            if limit:
                result = self.c.fetchmany(limit)
            else:
                result = self.c.fetchall()
            
            # Handling single column queries
            if '*' not in query and ',' not in query:
                result = [t[0] for t in result]
                self.result = result
                if limit == 1:
                    return result[0] if result else None   
                return result

            # Handling multi-column queries
            columns = [col[0] for col in self.c.description]
            results = [dict(zip(columns, row)) for row in result]
            self.result = results
            
            if limit == 1:
                return results[0] if results else None  # Return first result or None if empty
            return results

        except Exception as e:
            print(f"Failed to select from the database due to {e}, query: {query}")
            self.conn.rollback()
            return None

    def insert(self, query: str, params=()):
        return self.query(query, params)
            
    def query(self, query: str, params=()):
        if not query or params is None:
            raise ValueError("Query and parameters cannot be empty.")
        
        self.connect()
        if ";" not in query:
            query += ";"

        query = query.replace("?", "%s")
                
        try:
            placeholders_count = query.count('%s')
            if len(params) != placeholders_count:
                raise ValueError(f"Parameter mismatch: Expected {placeholders_count} parameters, but got {len(params)}.")
            
            self.c.execute(query, params)
            self.conn.commit()
        except ValueError as ve:
            # Handle specific parameter mismatch error
            print(f"Value Error: {ve}, query: {query}")
            self.conn.rollback()

        except Exception as e:
            print(f"Failed to query the database due to {e}, query: {query}")
            self.conn.rollback()

    def close(self):
        if self.c:
            self.c.close()
            self.c = None
        if self.conn:
            self.conn.close()
            self.conn = None

database = Database()