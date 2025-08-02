# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
MCP Memory Service Test Client
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
import json
import logging
import sys
import os
from typing import Dict, Any
import threading
import queue
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class MCPTestClient:
    def __init__(self):
        self.message_id = 0
        self.client_name = "test_client"
        self.client_version = "0.1.0"
        self.protocol_version = "0.1.0"
        self.response_queue = queue.Queue()
        self._setup_io()

    def _setup_io(self):
        """Set up binary mode for Windows."""
        if os.name == 'nt':
            import msvcrt
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')

    def get_message_id(self) -> str:
        """Generate a unique message ID."""
        self.message_id += 1
        return f"msg_{self.message_id}"

    def send_message(self, message: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Send a message and wait for response."""
        try:
            message_str = json.dumps(message) + '\n'
            logger.debug(f"Sending message: {message_str.strip()}")
            
            # Write message to stdout
            sys.stdout.write(message_str)
            sys.stdout.flush()
            
            # Read response from stdin with timeout
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"No response received within {timeout} seconds")
                
                try:
                    response = sys.stdin.readline()
                    if response:
                        logger.debug(f"Received response: {response.strip()}")
                        return json.loads(response)
                except Exception as e:
                    logger.error(f"Error reading response: {str(e)}")
                    raise
                
                time.sleep(0.1)  # Small delay to prevent busy waiting

        except Exception as e:
            logger.error(f"Error in communication: {str(e)}")
            raise

    def test_memory_operations(self):
        """Run through a series of test operations."""
        try:
            # Initialize connection
            logger.info("Initializing connection...")
            init_message = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "client_name": self.client_name,
                    "client_version": self.client_version,
                    "protocol_version": self.protocol_version
                },
                "id": self.get_message_id()
            }
            init_response = self.send_message(init_message)
            logger.info(f"Initialization response: {json.dumps(init_response, indent=2)}")

            # List available tools
            logger.info("\nListing available tools...")
            tools_message = {
                "jsonrpc": "2.0",
                "method": "list_tools",
                "params": {},
                "id": self.get_message_id()
            }
            tools_response = self.send_message(tools_message)
            logger.info(f"Available tools: {json.dumps(tools_response, indent=2)}")

            # Store test memories
            test_memories = [
                {
                    "content": "Remember to update documentation for API changes",
                    "metadata": {
                        "tags": ["todo", "documentation", "api"],
                        "type": "task"
                    }
                },
                {
                    "content": "Team meeting notes: Discussed new feature rollout plan",
                    "metadata": {
                        "tags": ["meeting", "notes", "features"],
                        "type": "note"
                    }
                }
            ]

            logger.info("\nStoring test memories...")
            for memory in test_memories:
                store_message = {
                    "jsonrpc": "2.0",
                    "method": "call_tool",
                    "params": {
                        "name": "store_memory",
                        "arguments": memory
                    },
                    "id": self.get_message_id()
                }
                store_response = self.send_message(store_message)
                logger.info(f"Store response: {json.dumps(store_response, indent=2)}")

        except TimeoutError as e:
            logger.error(f"Operation timed out: {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise

def main():
    client = MCPTestClient()
    client.test_memory_operations()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test client stopped by user")
    except Exception as e:
        logger.error(f"Test client failed: {str(e)}")