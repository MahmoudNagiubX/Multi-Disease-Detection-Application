from typing import Tuple, Union
from app.core.managers.database_manager import db_manager
from app.models.user.user import User

class AuthService:  # Handles user registration, login, and password changes
    def __init__(self) -> None:
        self.db = db_manager
    
    def register(self, username: str, email: str, password: str) -> Tuple[bool, str]: # Register a new user
        
        # Check if username already exists
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )
        if row is not None:
            return False, "Username is already taken."

        # Check if email already exists
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        )
        if row is not None:
            return False, "Email is already registered."

        # Create new User instance
        created_at = User.now_iso()
        user = User(
            id = None,
            username = username,
            email = email,
            password_hash = "",
            created_at = created_at,
            updated_at = None,
            is_active = 1,
        )
        user.set_password(password)

        # Insert into database
        self.db.execute(
            """
            INSERT INTO users (username, email, password_hash, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user.username,
                user.email,
                user.password_hash,
                user.created_at,
                user.updated_at,
                user.is_active,
            ),
        )

        return True, "Registration successful. You can now log in."
    
    def login(
        self,
        identifier: str, # Username/Email
        password: str,
    ) -> Tuple[bool, Union[str, User]]:
       
        # Search by Email/Username
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            (identifier, identifier),
        )
        if row is None:
            return False, "User not found."

        user = User.from_row(row)

        if not user.check_password(password):
            return False, "Incorrect password."

        if not user.is_active:
            return False, "Account is deactivated."

        return True, user
    
auth_service = AuthService() # Global service instance
    
