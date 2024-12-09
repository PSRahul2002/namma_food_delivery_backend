import os
import pymongo
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Query

app = FastAPI()

# Custom Middleware to add COOP and COEP headers
class COOP_COEP_Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
client = AsyncIOMotorClient("mongodb+srv://Rahul:qwerty123456@cluster0.n8whb.mongodb.net/")
db = client["namma-food-delivery"]
users_collection = db["users"]
addresses_collection = db["addresses"]

# Pydantic models
class Address(BaseModel):
    name: str
    city: str
    area: str
    street: str
    landmark: str
    pincode: str
    phone: str

class AddAddressRequest(BaseModel):
    email: str
    address: Address

class GoogleSignInRequest(BaseModel):
    token: str

# Function to save user data to MongoDB
async def save_user_data(user_data):
    # Check if user already exists based on email
    existing_user = await users_collection.find_one({"email": user_data["email"]})

    if existing_user:
        print(f"User with email {user_data['email']} already exists. Skipping insert.")
    else:
        # Insert new user data into MongoDB
        await users_collection.insert_one(user_data)
        print(f"User data saved to MongoDB: {user_data}")

# Endpoint to get addresses for the user
@app.get("/api/get_addresses")
async def get_addresses(email: str):
    addresses = await addresses_collection.find({"email": email}).to_list(100)
    for address in addresses:
        address["_id"] = str(address["_id"])  # Convert ObjectId to string
    return {"addresses": addresses}

# Endpoint to add an address for the user
@app.post("/api/add_address")
async def add_address(request: AddAddressRequest):
    # Check if the user exists
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count existing addresses for the user
    count = await addresses_collection.count_documents({"email": request.email})
    if count >= 5:
        raise HTTPException(status_code=400, detail="Cannot add more than 5 addresses")

    # Add the new address
    new_address = request.address.dict()
    new_address["email"] = request.email

    result = await addresses_collection.insert_one(new_address)
    return {"success": True, "address_id": str(result.inserted_id)}

# Endpoint to delete an address
@app.delete("/api/delete_address/{address_id}")
async def delete_address(address_id: str, email: str = Query(...)):
    result = await addresses_collection.delete_one(
        {"_id": ObjectId(address_id), "email": email}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Address not found or does not belong to the user")

    return {"success": True, "message": "Address deleted successfully"}

# Endpoint for Google Sign-In
@app.post("/api/auth/google-signin")
async def google_signin(request: GoogleSignInRequest):
    token = request.token
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), "971490819126-330ghvdvkup77r2hhug1lkvoir6ggfvt.apps.googleusercontent.com")
        user_data = {
            "google_id": id_info["sub"],
            "email": id_info["email"],
            "name": id_info.get("name"),
            "picture": id_info.get("picture")
        }
        await save_user_data(user_data)
        return JSONResponse(content={"message": "User data saved successfully", "user": user_data}, status_code=201)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")
