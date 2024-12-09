import pickle
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Replace with your front-end origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Define a Pydantic model to validate the incoming request
class GoogleSignInRequest(BaseModel):
    token: str

# Function to save user data to a text file using pickle
def save_user_data(user_data):
    file_path = "user_data.pkl"
    
    # Debug: Print user data to verify
    print("Saving user data:", user_data)

    if os.path.exists(file_path):
        try:
            # Load existing data
            with open(file_path, "rb") as file:
                existing_data = pickle.load(file)
            print("Existing data loaded:", existing_data)
        except (EOFError, pickle.UnpicklingError):
            print("Error loading existing data, starting fresh.")
            existing_data = []  # In case of any error
    else:
        existing_data = []
        print("No existing data, starting fresh.")

    # Append new user data
    existing_data.append(user_data)

    # Save back to the file using pickle
    with open(file_path, "wb") as file:
        pickle.dump(existing_data, file)
        print("Data saved to file:", existing_data)


# def save_user_data(user_data):
#     file_path = "user_data.pkl"
    
#     # Debug: Print user data to verify
#     print("Saving user data:", user_data)

#     # Check if the file already exists
#     if os.path.exists(file_path):
#         # Load existing data
#         with open(file_path, "rb") as file:
#             existing_data = pickle.load(file)
#         print("Existing data loaded:", existing_data)
#     else:
#         existing_data = []
#         print("No existing data, starting fresh.")

#     # Append new user data
#     existing_data.append(user_data)

#     # Save back to the file using pickle
#     with open(file_path, "wb") as file:
#         pickle.dump(existing_data, file)
#         print("Data saved to file:", existing_data)

# Endpoint for handling Google Sign-In
@app.post("/api/auth/google-signin")
async def google_signin(request: GoogleSignInRequest):
    token = request.token

    try:
        # Verify the token with Google's API
        id_info = id_token.verify_oauth2_token(token, requests.Request(), "971490819126-330ghvdvkup77r2hhug1lkvoir6ggfvt.apps.googleusercontent.com")

        # Extract user info from the token
        user_id = id_info["sub"]  # Google user ID (unique identifier)
        email = id_info["email"]
        name = id_info.get("name")
        picture = id_info.get("picture")

        # Prepare user data
        user_data = {
            "google_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
        }

        # Debug: Print the user data before saving
        print("User data to save:", user_data)

        # Save user data to a text file using pickle
        save_user_data(user_data)

        return JSONResponse(content={"message": "User data saved successfully", "user": user_data}, status_code=201)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")
