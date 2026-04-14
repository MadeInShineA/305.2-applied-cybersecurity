import os
import requests

class KDriveTools:
    def __init__(self, config):
        self.config = config
        self.base_url = f"https://api.infomaniak.com"
        self.headers = {"Authorization": f"Bearer {self.config.infomaniak_api_key}"}


    def list_files(self, directory_id):

        url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/files/{directory_id}/files"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json().get("data", [])
            
            files_summary = [
                {"name": f["name"], "id": f["id"], "type": f["type"], "size": f.get("size")} 
                for f in data
            ]
            return files_summary
        except requests.exceptions.RequestException as e:
            return f"Error listing files: {e}"

    def upload_file(self, file_content, file_name, directory_id):
        """
        Uploads a binary PDF (bytes) to kDrive.
        """
        url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/upload"

        params = {
            "directory_id": int(directory_id),
            "file_name": file_name,
            "conflict": "rename"
        }

        files = {
            'file': (file_name, file_content, 'application/pdf')
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                params=params,
                files=files
            )

            if not response.ok:
                return f"Upload failed: {response.status_code} - {response.text}"

            result = response.json()
            return f"OK: {result}"
            
        except Exception as e:
            return f"Request error: {e}"

    def extract_file_content(self, file_id: str):
      
        meta_url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/files/{file_id}"

        try:
            response = requests.get(meta_url, headers=self.headers)
            response.raise_for_status()

            data = response.json().get("data", {})

            if data.get("type") == "dir":
                return "Error: Cannot download a directory."

            filename = data.get("name", f"{file_id}.bin")

        except requests.exceptions.RequestException as e:
            return f"Error retrieving file name: {e}"


        download_url = f"{self.base_url}/2/drive/{self.config.kdrive_id}/files/{file_id}/download"

        try:
            content = []
            response = requests.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    content.append(chunk)

            return content

        except requests.exceptions.RequestException as e:
            return f"Error downloading file: {e}"