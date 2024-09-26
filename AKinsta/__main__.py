import os
import re
import sys
from datetime import datetime

from httpx import Client
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)
from user_agent import generate_user_agent

from .js_decoder import deobfuscator

console = Console()


class SnapInsta:
    @staticmethod
    def _get_token(client):
        response = client.get("https://snapinsta.app/")
        response.raise_for_status()
        return (
            (matches := re.search(r'name="token" value="(.*?)"', response.text))
            and matches[1]
            or None
        )

    @staticmethod
    def _get_variable(client, insta_url, token):
        response = client.post(
            "https://snapinsta.app/action2.php",
            headers={"Referer": "https://snapinsta.app/"},
            data={
                "url": insta_url,
                "token": token,
            },
        )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _extract_variables(js_code):
        pattern = r'\("(\w+)",\d+,"(\w+)",(\d+),(\d+),\d+\)'
        return [
            int(x) if x.isdigit() else x for x in re.search(pattern, js_code).groups()
        ]

    @staticmethod
    def _deobfuscate_html(js_variables):
        return deobfuscator(*js_variables)

    @staticmethod
    def _match_patterns(pattern, html_source):
        return re.findall(pattern, html_source)

    @staticmethod
    def _contains_string(video_link, substring):
        return video_link if substring in video_link else None

    @classmethod
    def _extract_snapinsta_links(cls, html_source):
        pattern = r'href=\\"([^\\"]+)\\"'
        matched_links = cls._match_patterns(pattern, html_source)
        return [
            cls._contains_string(link, "snapinsta") for link in matched_links
            if cls._contains_string(link, "snapinsta")
        ]

    @staticmethod
    def _determine_file_type(content_type):
        if content_type.startswith("video"):
            return "video"
        elif content_type.startswith("image"):
            return "photo"
        return "unknown"

    @staticmethod
    def _video_downloader(client, media_link, index):
        with client.stream("GET", media_link) as response:
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            file_type = SnapInsta._determine_file_type(content_type)

            video_folder = "Insta Media"
            os.makedirs(video_folder, exist_ok=True)
            timestamp = datetime.now().strftime("%d%m%y_%I%M%p")

            # Определение расширения файла по типу
            extension = "mp4" if file_type == "video" else "jpg"
            filename = f"{video_folder}/snapinsta.app_{timestamp}_{index}.{extension}"

            total_size = int(response.headers.get("Content-Length", 0))
            with Progress(
                TextColumn("[cyan]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TextColumn("•"),
                TransferSpeedColumn(),
            ) as progress:
                task = progress.add_task("Downloading..", total=total_size)

                with open(filename, "wb") as file:
                    for data in response.iter_bytes():
                        file.write(data)
                        progress.update(task, advance=len(data))

            console.print(f"\n{file_type.capitalize()} has been saved in [medium_purple3]{filename}[/]\n")

    @classmethod
    def start_download(cls, insta_url):
        console.clear()
        with Client(
            headers={"User-Agent": generate_user_agent()},
            timeout=10,
        ) as client:

            token = cls._get_token(client)
            js_code = cls._get_variable(client, insta_url, token)
            js_variables = cls._extract_variables(js_code)
            html_source = cls._deobfuscate_html(js_variables)
            media_links = cls._extract_snapinsta_links(html_source)

            if media_links:
                console.print(f"[green]Found {len(media_links)} download link(s):[/green]")
                for index, link in enumerate(media_links, start=1):
                    console.print(f"[green]Download link:[/green] {link}")
                    cls._video_downloader(client, link, index)
            else:
                raise ValueError("No download links found!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        console.print("[bold]Usage[/]: python -m AKinsta 'insta_video_url_here'")
        sys.exit(1)
    video_url = sys.argv[1]
    SnapInsta.start_download(video_url)
