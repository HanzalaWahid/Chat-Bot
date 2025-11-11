import requests

url = "http://127.0.0.1:8000/chat"

def test_chatbot():
    print("=" * 60)
    print("Restaurant Chatbot Test Client")
    print("=" * 60)
    print("Type your messages (type 'quit' or 'exit' to stop)")
    print("-" * 60)
    
    while True:
        try:
            # Get user input
            user_message = input("\nYou: ").strip()
            
            # Check for exit commands
            if user_message.lower() in ['quit', 'exit', 'q', 'bye']:
                print("\nGoodbye! 👋")
                break
            
            # Skip empty messages
            if not user_message:
                continue
            
            # Send request to backend
            data = {"message": user_message}
            response = requests.post(url, json=data)
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                bot_response = result.get("response", "No response received")
                print(f"Bot: {bot_response}")
            else:
                print(f"Error: Received status code {response.status_code}")
                print(f"Response: {response.text}")
        
        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to the server.")
            print("Make sure the FastAPI server is running on http://127.0.0.1:8000")
            print("Start it with: uvicorn app.main:app --reload")
            break
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break

if __name__ == "__main__":
    test_chatbot()