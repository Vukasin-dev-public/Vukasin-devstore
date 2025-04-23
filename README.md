# ZoomerangZ-backend

Backend API, database, and server logic for the Zoomerang-Z social media platform.

## Project Overview

Zoomerang-Z is a social media platform with advanced features including:

-   Real-time messaging and video/audio calling
-   Group music streaming (Z@M feature)
-   AI-powered chatbot (Z-Ai)
-   Face matching technology (Doppelgänger)
-   Media sharing (stories, posts)
-   User profiles and authentication
-   "Talk to Strangers" functionality

## Tech Stack

-   **Python Flask**: API and business logic
-   **Node.js**: Real-time services (WebSocket, WebRTC)
-   **PostgreSQL**: Database layer
-   **AWS S3 & CloudFront**: Media storage and delivery
-   **Firebase**: Push notifications
-   **Stripe**: Payment processing

## Current Implementation

This repository currently implements the authentication system with:

-   User registration and login
-   JWT-based authentication
-   Google and Apple Sign-in integrations
-   Username availability checking
-   User profile management

## Setup and Running

### Prerequisites

-   Python 3.8+
-   PostgreSQL database

### Installation

1. Clone the repository:

    ```
    git clone https://github.com/your-username/ZoomerangZ-backend.git
    cd ZoomerangZ-backend
    ```

2. Install dependencies:

    ```
    pip install -r requirements.txt
    ```

3. Configure the database:

    - Open `func/constants.py` and set your database credentials

    ```python
    DATABASE_NAME = "zoomerangz"
    DATABASE_USERNAME = "postgres"
    DATABASE_PASSWORD = "Pass@123"
    DATABASE_HOST = "localhost"  # or your database host
    DATABASE_PORT = '5432'  # default PostgreSQL port
    DATABASE_TIMEOUT = '5000'  # in milliseconds
    ```

4. Initialize the database:

    ```
    python scripts/init_db.py
    ```

5. Run the application:
    ```
    python app.py
    ```

### API Endpoints

#### Authentication

-   `POST /api/user/register`: Register a new user
-   `POST /api/user/login`: Log in a user
-   `POST /api/user/refresh`: Refresh JWT tokens
-   `POST /api/google/auth`: Google Sign-in
-   `POST /api/apple/auth`: Apple Sign-in
-   `GET /api/user/username/check`: Check username availability
-   `GET /api/user/username/suggest`: Suggest available usernames
-   `GET /api/auth/me`: Get current user profile
-   `POST /api/auth/logout`: Log out a user

#### User Management

-   `GET /api/users/profile/<username>`: Get user profile
-   `PUT /api/users/profile`: Update user profile
-   `PUT /api/users/password`: Change password
-   `POST /api/users/follow/<username>`: Follow a user
-   `POST /api/users/unfollow/<username>`: Unfollow a user
-   `GET /api/users/search`: Search for users

## Project Structure

```
ZoomerangZ-backend/
├── app.py                  # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── plans.json              # Dynamic Subscription plans
├── func/
│   ├── constants.py        # Configuration constants
│   ├── utils.py            # Utility functions
│   ├── oauth_utils.py      # OAuth utility functions
│   ├── payment_utils.py    # Payments Utility functions
│   └── objects/            # Domain models
│       ├── user.py         # User model
│       ├── database.py     # Database connector
│       ├── notification.py # Notification model
│       ├── interest.py     # Interest model
│       ├── media.py        # Media model
│       ├── message.py      # Message model
│       ├── post.py         # Post model
│       └── chat_room.py    # Chat room model
│       ├── payment.py      # Payment model
│       └── plan.py         # Plan model
│       └── chat_room.py    # Subscription model
├── routes/
│   ├── account_routes.py   # Account-related routes
│   ├── apple_routes.py     # Apple OAuth routes
│   ├── google_routes.py    # Google OAuth routes
│   ├── user_routes.py      # User-related routes
│   └── temp/               # Temporary routes (for testing or staging)
├── scripts/
│   └── init_db.py          # Database initialization script
└── logs/                   # Application logs
```

## Class Creation Template

````
from datetime import datetime
from func.models.database import database
from func.utils import generate_unique_id

# Import other objects this one has relations with, e.g., User, Media

class ClassName:
    def __init__(self, id: str, ..., created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        # Define attributes that directly map to DB columns
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

        # Define relations (foreign keys as objects)
        # e.g., self.user = user

    def __repr__(self):
        return f"ClassName(id={self.id}, ...)"  # Add key fields for easier debugging

    @classmethod
    def get(cls, id: str):
        result = database.select("SELECT * FROM table_name WHERE id = %s", (id,), limit=1)
        if result:
            return cls(
                id=result['id'],
                ...,  # map columns
                created_at=result['created_at'],
                updated_at=result.get('updated_at')
            )
        return None

    @classmethod
    def create(cls, ..., optional_field: type = default):
        obj_id = generate_unique_id()
        obj = cls(id=obj_id, ..., optional_field=optional_field)
        return obj.save(insert=True)

    def to_dict(self):
        return {
            "id": self.id,
            ...,  # flatten other fields
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def save(self, insert: bool = False):
        if insert:
            query = "INSERT INTO table_name (id, ..., created_at, updated_at) VALUES (%s, ..., %s, %s)"
            params = (self.id, ..., self.created_at, self.updated_at)
        else:
            query = "UPDATE table_name SET ..., updated_at = %s WHERE id = %s"
            params = (..., self.updated_at, self.id)

        database.query(query, params)
        return self

    def delete(self):
        database.query("DELETE FROM table_name WHERE id = %s", (self.id,))

```sql
CREATE TABLE IF NOT EXISTS table_name (
    id SERIAL PRIMARY KEY,
    column_name column_datatype,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
````

## Future Work

-   Implement remaining social features (posts, comments)
-   Set up real-time chat using WebSockets
-   Implement video/audio calling with WebRTC
-   Integrate with AWS S3 for media storage
-   Set up AI-powered chatbot and face matching

## Documentation

For more detailed documentation, refer to the [project design document](https://app.eraser.io/workspace/RugGBhdXP8OBWDQH7fh1?origin=share).
Postman collection: https://.postman.co/workspace/My-Workspace~bdee9e04-0d76-4632-868b-9e0026d1935a/collection/31986548-12f563fa-483b-44a2-8f77-0ac9ccd9730d?action=share&creator=31986548
