import os
import pymongo
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Query
from typing import List
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()

# Custom Middleware to add COOP and COEP headers
class COOP_COEP_Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"  # Adjust based on your use case
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"  # Adjust based on your use case
        return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Replace with your front-end origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# MongoDB connection
client = AsyncIOMotorClient("mongodb+srv://Rahul:qwerty123456@cluster0.n8whb.mongodb.net/")  # Use motor for async connection
db = client["namma-food-delivery"]
users_collection = db["users"]  # Users collection
addresses_collection = db["addresses"]  # Addresses collection = db["user-addresses"]  # Addresses collection

# Define a Pydantic model to validate the incoming request
class GoogleSignInRequest(BaseModel):
    token: str

class Address(BaseModel):
    # email:str
    name: str
    city: str
    area: str
    street: str
    landmark: str
    pincode: str
    phone: str
    
class AddAddressRequest(BaseModel):
    email: str  # Email to associate the address with the user
    address: Address

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

    # Add the new address, associating it with the user's email
    new_address = request.address.dict()  # Get address fields as a dictionary
    new_address["email"] = request.email  # Add the email to the address document

    result = await addresses_collection.insert_one(new_address)
    return {"success": True, "address_id": str(result.inserted_id)}


# Endpoint to delete an address

@app.delete("/api/delete_address/{address_id}")
async def delete_address(address_id: str, email: str = Query(...)):
    # Verify that the address exists and belongs to the logged-in user
    result = await addresses_collection.delete_one(
        {"_id": ObjectId(address_id), "email": email}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, detail="Address not found or does not belong to the user"
        )

    return {"success": True, "message": "Address deleted successfully"}

# Function to save user data to MongoDB
def save_user_data(user_data):
    # Check if user already exists based on email
    existing_user = users_collection.find_one({"email": user_data["email"]})

    if existing_user:
        print(f"User with email {user_data['email']} already exists. Skipping insert.")
    else:
        # Insert new user data into MongoDB
        users_collection.insert_one(user_data)
        print(f"User data saved to MongoDB: {user_data}")
          
# Function to save or retrieve user data from MongoDB
def save_or_get_user_data(user_data):
    # Check if user already exists based on email
    existing_user = users_collection.find_one({"email": user_data["email"]})

    if existing_user:
        return existing_user  # If user exists, return their data
    else:
        # If user does not exist, insert new user data
        user_id = users_collection.insert_one(user_data).inserted_id
        user_data["_id"] = user_id
        return user_data

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

        # Save user data to MongoDB
        save_user_data(user_data)

        return JSONResponse(content={"message": "User data saved successfully", "user": user_data}, status_code=201)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")



cart_collection = db["cart"]


# Pydantic models
class CartItem(BaseModel):
    id: str
    name: str
    price: float
    quantity: int

class Cart(BaseModel):
    email: EmailStr
    restaurant_id: str
    items: List[CartItem]
    total_amount: float = Field(..., gt=0)
    

# Add or Update Cart
@app.post("/api/cart")
async def add_to_cart(cart: Cart):
    # Fetch the user's current cart
    existing_cart = await cart_collection.find_one({"email": cart.email})

    # If the cart exists and has a different restaurant_id, clear it
    if existing_cart and existing_cart["restaurant_id"] != cart.restaurant_id:
        await cart_collection.delete_one({"_id": existing_cart["_id"]})

    # Calculate total amount
    cart.total_amount = sum(item.price * item.quantity for item in cart.items)

    # Insert or update the cart
    result = await cart_collection.update_one(
        {"email": cart.email},
        {"$set": cart.dict()},
        upsert=True
    )

    return {"message": "Cart updated successfully", "cart_id": str(result.upserted_id or existing_cart['_id'])}



@app.get("/api/cart/{email}")
async def get_cart(email: EmailStr):
    cart = await cart_collection.find_one({"email": email})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    cart["_id"] = str(cart["_id"])  # Convert ObjectId to string for JSON serialization
    return {"cart": cart}



@app.delete("/api/cart/{email}")
async def clear_cart(email: EmailStr):
    result = await cart_collection.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cart not found")
    return {"message": "Cart cleared successfully"}








# @app.post("/api/add_address")
# async def add_address(address: Address):
#     # Check if there are already 5 addresses
#     count = await users_address.count_documents({})
#     if count >= 5:
#         raise HTTPException(status_code=400, detail="Cannot add more than 5 addresses")

#     new_address = address.model_dump()  # Use model_dump instead of dict()
#     result = await users_address.insert_one(new_address)
#     return {"success": True, "address_id": str(result.inserted_id)}

# @app.get("/api/get_addresses")
# async def get_addresses():
#     try:
#         addresses = await users_address.find({}).to_list(100)
#         # Convert ObjectId to string for JSON serialization
#         for address in addresses:
#             address["_id"] = str(address["_id"])  # Convert ObjectId to string
#         return {"addresses": addresses}
#     except Exception as e:
#         print(f"Error retrieving addresses: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")

# @app.delete("/api/delete_address/{address_id}")
# async def delete_address(address_id: str):
#     result = await users_address.delete_one({"_id": ObjectId(address_id)})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Address not found")
#     return {"success": True}