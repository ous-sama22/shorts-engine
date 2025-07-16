import docker
import logging
from typing import Dict, Optional

import docker.errors

class DockerSandboxManager:
    """
    Manages Docker sandboxes for isolating API keys.
    Creates a new container for each API key and cleans up old containers when switching.
    """
    
    def __init__(self, base_image: str = "python:3.9-slim"):
        """
        Initialize the Docker sandbox manager.
        
        Args:
            base_image: The base Docker image to use for sandboxes
        """
        self.client = docker.from_env()
        self.base_image = base_image
        self.active_containers: Dict[str, str] = {}  # Maps API key to container ID
        self.current_container_id: Optional[str] = None
        self.current_api_key: Optional[str] = None
        
        # Ensure the base image is available
        try:
            self.client.images.get(self.base_image)
        except docker.errors.ImageNotFound:
            logging.info(f"Pulling base image: {self.base_image}")
            self.client.images.pull(self.base_image)
    
    def create_sandbox_for_api_key(self, api_key: str) -> str:
        """
        Create a new Docker sandbox for the given API key.
        
        Args:
            api_key: The API key to containerize
            
        Returns:
            The container ID of the newly created sandbox
        """
        # Check if a container already exists for this API key
        if api_key in self.active_containers:
            container_id = self.active_containers[api_key]
            try:
                # Check if container still exists
                container = self.client.containers.get(container_id)
                if container.status != "running":
                    container.start()
                return container_id
            except docker.errors.NotFound:
                # Container no longer exists, remove from active containers
                del self.active_containers[api_key]
        
        # Create a new container with the API key as an environment variable
        container = self.client.containers.run(
            self.base_image,
            detach=True,
            environment={
                "ELEVENLABS_API_KEY": api_key
            },
            command="sleep infinity",  # Keep container running
            remove=False,  # We'll manually remove it when done
            name=f"elevenlabs-sandbox-{api_key[-8:]}"  # Use last 8 chars of API key for name
        )
        
        # Store the container ID
        container_id = container.id
        if container_id is None:
            raise ValueError("Failed to create container, received None ID.")
        
        self.active_containers[api_key] = container_id
        self.current_container_id = container_id
        self.current_api_key = api_key
        
        logging.info(f"Created new sandbox container for API key ending in '...{api_key[-4:]}'")
        return container_id
    
    def switch_to_api_key(self, api_key: str) -> str:
        """
        Switch to a different API key, creating a new sandbox if needed and removing the old one.
        
        Args:
            api_key: The API key to switch to
            
        Returns:
            The container ID of the sandbox for the new API key
        """
        if api_key == self.current_api_key:
            return self.current_container_id or ""
        
        # Create sandbox for the new API key
        new_container_id = self.create_sandbox_for_api_key(api_key)
        
        # Remove the old container if it exists
        if self.current_container_id and self.current_api_key:
            try:
                old_container = self.client.containers.get(self.current_container_id)
                old_container.stop()
                old_container.remove()
                logging.info(f"Removed old sandbox container for API key ending in '...{self.current_api_key[-4:]}'")
            except docker.errors.NotFound:
                pass
            
            # Remove from active containers
            if self.current_api_key in self.active_containers:
                del self.active_containers[self.current_api_key]
        
        # Update current container and API key
        self.current_container_id = new_container_id
        self.current_api_key = api_key
        
        return new_container_id
    
    def execute_in_sandbox(self, api_key: str, command: str) -> str:
        """
        Execute a command in the sandbox for the given API key.
        
        Args:
            api_key: The API key whose sandbox to use
            command: The command to execute
            
        Returns:
            The output of the command
        """
        # Ensure we have a sandbox for this API key
        container_id = self.switch_to_api_key(api_key)
        
        # Execute the command in the container
        container = self.client.containers.get(container_id)
        result = container.exec_run(command)
        
        return result.output.decode('utf-8')
    
    def cleanup(self):
        """Clean up all active containers."""
        for api_key, container_id in list(self.active_containers.items()):
            try:
                container = self.client.containers.get(container_id)
                container.stop()
                container.remove()
                logging.info(f"Removed sandbox container for API key ending in '...{api_key[-4:]}'")
            except docker.errors.NotFound:
                pass
        
        self.active_containers.clear()
        self.current_container_id = None
        self.current_api_key = None
