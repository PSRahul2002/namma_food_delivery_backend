# Sample user data to save
sample_data = [{"google_id": "123", "email": "user@example.com", "name": "Test User", "picture": "url_to_picture"}]

# Save this data to the pickle file
with open('user_data.pkl', 'wb') as file:
    pickle.dump(sample_data, file)