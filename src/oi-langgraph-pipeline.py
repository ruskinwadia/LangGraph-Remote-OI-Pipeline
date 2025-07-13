import requests
import json
import time
import random
from typing import Iterator, List, Dict, Any, Optional, Generator, Union
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        MODEL_ID: str = Field(default="")
        LANGGRAPH_URL: str = Field(default="")
        VERSION: str = Field(default="1.0")

    def __init__(self):
        self.valves = self.Valves()
        self.name = "OI LangGraph Pipeline"
        self.headers = {"Content-Type": "application/json"}
        self.assistant_id = "agent"
        # Store thread data per conversation (using a simple dict for now)
        self.conversations = {}
        self.waiting_quotes = [
            "Brewing coffee...",
            "Diving deep into the data ocean...",
            "Aligning the digital constellations...",
            "Summoning insights from the ether...",
            "Just coaxing the information into existence...",
            "Spinning threads of thought...",
            "My circuits are currently composing a masterpiece...",
            "Waiting for the knowledge tree to bear fruit...",
            "Polishing the answer until it sparkles...",
            "Chasing down the perfect response...",
            "The digital gears are whirring harmoniously...",
            "Consulting with my inner muse...",
            "Just adding a sprinkle of digital magic...",
            "Gathering stardust to answer your query...",
            "My neural networks are having a pow-wow...",
            "Loading... please wait for the digital confetti...",
            "Forging the ultimate reply...",
            "In the grand theatre of algorithms...",
            "Shuffling the deck of possibilities...",
            "Almost ready to unveil the answer...",
            "Just persuading the pixels to cooperate...",
            "Warming up the thought engines...",
            "Sculpting the perfect response...",
            "Navigating the labyrinth of information...",
            "Attuning to the cosmic frequency of knowledge...",
            "Just persuading the data bits to line up...",
            "Waiting for inspiration to strike the silicon...",
            "Building your answer pixel by pixel...",
            "My digital cogs are turning... smoothly, I promise!",
            "Conjuring insights from the code cauldron...",
            "Just a moment while I consult the infinite library...",
            "Letting the algorithms dance...",
            "Preparing a response sprinkled with starlight...",
            "Deciphering the whispers of the web...",
            "Just organizing my thoughts into a neat little package...",
            "Waiting for the final piece of the puzzle...",
            "My internal hamsters are on a coffee break...",
            "Crafting a reply worthy of your query...",
            "Synchronizing the digital universe...",
            "Just waiting for the creative juices to flow... virtually, of course.",
            "Almost ready to emerge with the answer...",
        ]

    async def on_startup(self):
        """Called when the pipeline starts up"""
        print(f"Pipeline '{self.name}' started")

    async def on_shutdown(self):
        """Called when the pipeline shuts down"""
        print(f"Pipeline '{self.name}' shut down")

    def get_conversation_id(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a simple conversation ID based on first message"""
        if messages:
            # Use a hash of the first message as conversation ID
            first_msg = str(messages[0].get("content", ""))
            return str(hash(first_msg))
        return "default"

    def get_random_waiting_quote(self) -> str:
        """Returns a random quote from the list of creative waiting quotes."""
        return random.choice(self.waiting_quotes)

    def create_thread(self) -> str:
        """Creates a new thread and returns the thread ID"""
        try:
            url = f"{self.valves.LANGGRAPH_URL}/threads"
            payload = json.dumps({"thread_id": "", "metadata": {}, "if_exists": "raise"})
            response = requests.post(url, headers=self.headers, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()["thread_id"]
        except Exception as e:
            print(f"Error creating thread: {e}")
            raise

    def edit_state(self, thread_id: str, messages: List[Dict[str, Any]], first_checkpoint_id: str) -> str:
        """Edits the state of the current thread with the given messages"""
        if not thread_id:
            print("Error: thread_id is not set. Cannot edit state.")
            return first_checkpoint_id

        if not first_checkpoint_id:
            try:
                response = requests.get(
                    f"{self.valves.LANGGRAPH_URL}/threads/{thread_id}/history",
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                history = response.json()
                if history:
                    first_checkpoint_id = history[-1].get("checkpoint_id", "")
                else:
                    print(f"Warning: No history found for thread {thread_id}")
                    return first_checkpoint_id
            except Exception as e:
                print(f"Error fetching thread history: {e}")
                return first_checkpoint_id

        chkpt_id = first_checkpoint_id

        for msg in messages:
            as_node = "__start__" if msg.get("role") == "user" else "generate"
            update_payload = json.dumps({
                "values": {"messages": [msg]},
                "checkpoint": {
                    "checkpoint_id": chkpt_id,
                    "thread_id": thread_id,
                    "checkpoint_ns": "",
                    "checkpoint_map": {},
                },
                "as_node": as_node,
            })
            try:
                response = requests.post(
                    f"{self.valves.LANGGRAPH_URL}/threads/{thread_id}/state",
                    data=update_payload,
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                new_chkpt_id = response.json().get("checkpoint_id")
                if new_chkpt_id:
                    chkpt_id = new_chkpt_id
            except Exception as e:
                print(f"Error editing state for message {msg}: {e}")
                break

        return chkpt_id

    def pipe(
        self,
        user_message: str,
        messages: List[Dict[str, Any]],
        body: Dict[str, Any]
    ) -> Union[str, Generator, Iterator]:
        """Main pipeline method that processes the user message and returns response"""
        
        # Yield the opening thinking tag at the very beginning.
        yield "<thinking>"
        
        try:
            print(f"Pipeline called with user_message: {user_message[:100]}...")
            print(f"Number of messages: {len(messages)}")

            if not messages:
                yield "</thinking>\n\nError: No messages provided"
                return

            # Yield a creative quote to start the thinking process.
            yield f"\n{self.get_random_waiting_quote()}"

            # Get conversation context
            conv_id = self.get_conversation_id(messages)
            conv_data = self.conversations.get(conv_id, {
                "thread_id": None,
                "prev_msg_len": 0,
                "first_checkpoint_id": ""
            })

            # Create new thread if this is the first message
            if len(messages) == 1 or not conv_data["thread_id"]:
                print("Creating new thread...")
                yield "\n🔄 Setting up new conversation..."
                conv_data["thread_id"] = self.create_thread()
                conv_data["prev_msg_len"] = 0
                conv_data["first_checkpoint_id"] = ""
                print(f"Created new thread with ID: {conv_data['thread_id']}")

            # Check if an existing query was modified
            new_msg_length = len(messages)

            # Edit the state if needed
            if new_msg_length <= conv_data["prev_msg_len"] and new_msg_length > 0:
                print("Editing conversation state...")
                yield "\n🔄 Updating conversation state..."
                conv_data["first_checkpoint_id"] = self.edit_state(
                    conv_data["thread_id"],
                    messages[:-1],
                    conv_data["first_checkpoint_id"]
                )

            # Store updated conversation data
            self.conversations[conv_id] = conv_data

            latest_message_content = messages[-1]["content"]

            # Start the run
            run_url = f"{self.valves.LANGGRAPH_URL}/threads/{conv_data['thread_id']}/runs"
            print(f"Starting thread run at: {run_url}")

            username = "unknown"
            if "user" in body and isinstance(body["user"], dict):
                username = body["user"].get("name", "unknown")

            payload = json.dumps({
                "assistant_id": self.assistant_id,
                "input": {
                    "messages": [{"content": latest_message_content, "type": "human"}],
                    "openwebui_username": username,
                },
                "metadata": {},
            })

            run_response = requests.post(run_url, headers=self.headers, data=payload, timeout=30)
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data.get("run_id")

            if not run_id:
                yield "</thinking>\n\nError: Failed to start run - No run ID received"
                return

            print(f"Started thread run with ID: {run_id}")
            yield "\n🔄 Processing your request..."

            # Poll for completion with status updates
            check_run_url = f"{self.valves.LANGGRAPH_URL}/threads/{conv_data['thread_id']}/runs/{run_id}"
            start_time = time.time()
            max_time = 120
            poll_interval = 2
            
            print("Polling run status...")
            last_quote_time = time.time()
            quote_interval = 8

            while time.time() - start_time <= max_time:
                try:
                    status_response = requests.get(check_run_url, headers=self.headers, timeout=10)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    current_status = status_data.get("status", "unknown")
                    print(f"Current run status: {current_status}")

                    if current_status == "success":
                        print("Run completed successfully.")
                        yield "\n✅ Generating response..."
                        break
                    elif current_status in ["error", "timeout", "interrupted"]:
                        error_msg = f"Run failed with status: {current_status}"
                        print(error_msg)
                        yield f"</thinking>\n\n❌ {error_msg}"
                        return
                    
                    current_time = time.time()
                    if current_time - last_quote_time >= quote_interval:
                        yield f"\n⏳ {self.get_random_waiting_quote()}"
                        last_quote_time = current_time

                    time.sleep(poll_interval)

                except Exception as e:
                    print(f"Error during polling: {e}")
                    yield "\n⚠️ Connection hiccup, retrying..."
                    time.sleep(poll_interval)
                    continue
            else:
                yield f"</thinking>\n\n⏰ Run timed out after {max_time} seconds"
                return

            # Fetch final messages
            messages_url = f"{check_run_url}/join"
            print(f"Fetching final messages from: {messages_url}")
            yield "\n📥 Retrieving response..."

            messages_response = requests.get(messages_url, headers=self.headers, timeout=30)
            messages_response.raise_for_status()
            
            # --- Close the thinking tag before sending the answer. ---
            yield "</thinking>"

            messages_data = messages_response.json().get("messages", [])

            if not messages_data:
                yield "\n\n❌ No response received from assistant"
                return

            latest_assistant_message = messages_data[-1]
            output_content = latest_assistant_message.get("content")

            if not output_content:
                yield "\n\n❌ Assistant response is empty"
                return

            try:
                output = json.loads(output_content)
                response_text = output.get("answer", output_content)
                
                # Yield the main answer, adding newlines for separation.
                yield f"\n\n{response_text}"
                
                # Then yield citations if available
                source_documents = output.get("citations", [])
                if source_documents:
                    for src in source_documents:
                        quote = src.get("quote", "")
                        source = src.get("source", "Unknown Source")
                        file_url = src.get("file_url", "")
                        
                        if quote:
                            yield {
                                "event": {
                                    "type": "citation",
                                    "data": {
                                        "document": [quote.strip()],
                                        "metadata": [{"source": source}],
                                        "source": {
                                            "name": source,
                                            "url": file_url if file_url else "#"
                                        },
                                    },
                                }
                            }
            except (json.JSONDecodeError, TypeError):
                # If not JSON, use content as-is
                yield f"\n\n{str(output_content)}"

            # Update conversation data for the next turn
            conv_data["prev_msg_len"] = new_msg_length
            self.conversations[conv_id] = conv_data
            print("Completed response processing")

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e}"
            print(error_msg)
            yield f"</thinking>\n\n🌐 {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(error_msg)
            yield f"</thinking>\n\n⚠️ {error_msg}"
