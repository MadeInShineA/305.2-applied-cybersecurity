"""
kDrive tools module for the email agent application.

This module provides the KDriveTools class which provides an interface to
the Infomaniak kDrive API for file management operations. It supports listing
files in a directory, uploading files, and downloading file content.

The module handles authentication via Bearer tokens and provides error handling
for all API operations.
"""

import requests
from typing import List, Dict, Any, Optional

from src.config import Config


class KDriveTools:
    """
    Client for Infomaniak kDrive API operations.

    This class provides methods for interacting with Infomaniak's kDrive
    cloud storage service. It supports listing files in a directory,
    uploading PDF files, and downloading file content.

    The class uses the Infomaniak API v3 and handles authentication
    via Bearer tokens stored in the configuration.

    Attributes:
        config: Configuration object containing kDrive API credentials.
        base_url: Base URL for the Infomaniak API (https://api.infomaniak.com).
        headers: Dictionary containing the Authorization header with Bearer token.

    Example:
        >>> tools = KDriveTools(config)
        >>> files = tools.list_files(directory_id)
        >>> tools.upload_file(file_bytes, "resume.pdf", directory_id)
        >>> content = tools.extract_file_content(file_id)
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the KDriveTools client with configuration.

        Args:
            config: Config object containing Infomaniak API key and kDrive ID.
        """
        self.config = config
        self.base_url = f"https://api.infomaniak.com"
        self.headers = {"Authorization": f"Bearer {self.config.infomaniak_api_key}"}

    def list_files(self, directory_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a kDrive directory.

        This method fetches the list of files and subdirectories within
        a specified kDrive directory. It returns a simplified list containing
        each file's name, ID, type, and size.

        Args:
            directory_id: The unique identifier of the kDrive directory to list.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing:
                - name: The file or directory name
                - id: The unique identifier
                - type: "file" or "dir"
                - size: File size in bytes (may be None for directories)

        Raises:
            RuntimeError: If the API request fails (network error, auth error, etc.).

        Example:
            >>> files = tools.list_files("12345")
            >>> for f in files:
            ...     print(f"{f['name']} ({f['type']})")
        """
        # Construct the API endpoint for listing directory contents
        url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/files/{directory_id}/files"

        try:
            # Make GET request to fetch directory contents
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json().get("data", [])

            # Transform raw API data into simplified dictionary format
            files_summary = [
                {
                    "name": f["name"],
                    "id": f["id"],
                    "type": f["type"],
                    "size": f.get("size"),
                }
                for f in data
            ]
            return files_summary

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error listing files: {e}")

    def upload_file(
        self, file_content: bytes, file_name: str, directory_id: str
    ) -> str:
        """
        Upload a file to a kDrive directory.

        This method uploads a file (typically a PDF) to a specified kDrive
        directory. It handles the chunked upload process by providing
        the total file size and uses the "rename" conflict strategy to
        avoid overwriting existing files.

        Args:
            file_content: The raw bytes content of the file to upload.
            file_name: The desired name for the uploaded file.
            directory_id: The unique identifier of the target kDrive directory.

        Returns:
            str: A success message in the format "OK: {result}" if successful.

        Raises:
            RuntimeError: If the upload fails (network error, API error, etc.).

        Note:
            - The Content-Type is set to "application/pdf" as this module
              is primarily used for CV uploads.
            - If a file with the same name exists, the new file will be
              renamed (e.g., "resume.pdf" becomes "resume (1).pdf").
        """
        # API endpoint for file upload
        url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/upload"

        # Calculate total size for chunked upload
        total_size = len(file_content)

        # Request parameters
        params = {
            "directory_id": int(directory_id),
            "file_name": file_name,
            "total_size": total_size,
            "conflict": "rename",  # Rename if file exists
        }

        # Request headers
        headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Type": "application/pdf",
            "Content-Length": str(total_size),
        }

        try:
            # Perform the upload request
            response = requests.post(
                url, headers=headers, params=params, data=file_content
            )

            # Check for errors
            if not response.ok:
                raise RuntimeError(
                    f"Upload failed: {response.status_code} - {response.text}"
                )

            # Return success message with API response
            result = response.json()
            return f"OK: {result}"

        except Exception as e:
            raise RuntimeError(f"Request error: {e}")

    def extract_file_content(self, file_id: str) -> List[bytes]:
        """
        Download and return the content of a file from kDrive.

        This method retrieves the binary content of a file from kDrive.
        First, it fetches the file metadata to determine the filename,
        then it downloads the actual file content in chunks.

        Args:
            file_id: The unique identifier of the file to download.

        Returns:
            List[bytes]: A list of byte chunks containing the file content.
                        The chunks are joined to reconstruct the full file.

        Raises:
            ValueError: If the file_id refers to a directory instead of a file.
            RuntimeError: If the download fails (network error, API error, etc.).

        Example:
            >>> content = tools.extract_file_content("abc123")
            >>> file_bytes = b"".join(content)
        """
        # Step 1: Get file metadata to determine filename
        meta_url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/files/{file_id}"

        try:
            response = requests.get(meta_url, headers=self.headers)
            response.raise_for_status()

            data = response.json().get("data", {})

            # Verify this is a file, not a directory
            if data.get("type") == "dir":
                raise ValueError("Error: Cannot download a directory.")

            # Extract filename from metadata
            filename = data.get("name", f"{file_id}.bin")

        except requests.exceptions.RequestException as e:
            return RuntimeError(f"Error retrieving file name: {e}")

        # Step 2: Construct download URL and fetch file content
        download_url = (
            f"{self.base_url}/2/drive/{self.config.kdrive_id}/files/{file_id}/download"
        )

        try:
            # Stream download to handle large files efficiently
            content = []
            response = requests.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()

            # Read file in 1MB chunks
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    content.append(chunk)

            return content

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error downloading file: {e}")
