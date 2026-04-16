import requests
from src.config import Config


class KDriveTools:
    """Client for Infomaniak kDrive API operations."""

    def __init__(self, config: Config):
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
            raise RuntimeError("Error listing files: {e}")

    def upload_file(self, file_content, file_name, directory_id):
        url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/upload"

        total_size = len(file_content)

        params = {
            "directory_id": int(directory_id),
            "file_name": file_name,
            "total_size": total_size,
            "conflict": "rename",
        }

        headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Type": "application/pdf",
            "Content-Length": str(total_size),
        }

        try:
            response = requests.post(
                url, headers=headers, params=params, data=file_content
            )

            if not response.ok:
                raise RuntimeError(
                    f"Upload failed: {response.status_code} - {response.text}"
                )

            result = response.json()
            return f"OK: {result}"

        except Exception as e:
            raise RuntimeError(f"Request error: {e}")

    def extract_file_content(self, file_id: str):
        meta_url = f"{self.base_url}/3/drive/{self.config.kdrive_id}/files/{file_id}"

        try:
            response = requests.get(meta_url, headers=self.headers)
            response.raise_for_status()

            data = response.json().get("data", {})

            if data.get("type") == "dir":
                raise ValueError("Error: Cannot download a directory.")

            filename = data.get("name", f"{file_id}.bin")

        except requests.exceptions.RequestException as e:
            return RuntimeError(f"Error retrieving file name: {e}")

        download_url = (
            f"{self.base_url}/2/drive/{self.config.kdrive_id}/files/{file_id}/download"
        )

        try:
            content = []
            response = requests.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    content.append(chunk)

            return content

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error downloading file: {e}")
