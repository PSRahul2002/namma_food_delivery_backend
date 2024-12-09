import pickle

try:
    # Open the pickle file in read-binary mode
    with open('user_data.pkl', 'rb') as file:
        data = pickle.load(file)

    # Check if data is loaded and print each user's details
    if data:
        print("User Data:")
        for idx, user in enumerate(data, start=1):
            print(f"\nUser {idx}:")
            for key, value in user.items():
                print(f"  {key}: {value}")
    else:
        print("No data found in user_data.pkl.")
except (EOFError, FileNotFoundError):
    print("The file is empty or not found.")
except pickle.UnpicklingError:
    print("Error reading the pickle file.")
