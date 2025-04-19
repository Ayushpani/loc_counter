import requests
import base64
import asyncio
import aiohttp
import mimetypes
from gitignore_parser import parse_gitignore
from urllib.parse import urlparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import time
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('loc_counter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GitHubLOCCounter:
    def __init__(
        self,
        repo_url: str,
        token: str,
        include_tests: bool = True,
        max_file_size_mb: float = 1,
        exclude_extensions: List[str] = None
    ) -> None:
        self.repo = self._parse_repo_url(repo_url)
        self.headers = {"Authorization": "token %s" % token, "Accept": "application/vnd.github.v3+json"}
        self.gitignore_rules: Dict[str, Optional[callable]] = {}
        self.include_tests = include_tests
        self.max_file_size_mb = max_file_size_mb  # Explicitly defined for Pylint
        self.max_file_size_bytes = max_file_size_mb * 1_000_000
        self.exclude_extensions = exclude_extensions or []
        self.loc_counts: Dict[str, int] = {"total": 0}
        self.api_base = "https://api.github.com/repos"
        self.processed_files = 0
        self.total_files = 0
        self.start_time = time.time()

    def _parse_repo_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/").split("/")
            if len(path) < 2:
                raise ValueError("Invalid GitHub repository URL")
            return "%s/%s" % (path[0], path[1])
        except Exception as e:
            logger.error("Failed to parse repo URL %s: %s", url, str(e))
            raise

    async def fetch_gitignore_files(self, session: aiohttp.ClientSession) -> None:
        async def search_gitignore(path: str = "") -> None:
            try:
                async with session.get(
                    "%s/%s/contents/%s" % (self.api_base, self.repo, path), headers=self.headers
                ) as response:
                    if response.status == 200:
                        contents = await response.json()
                        for item in contents:
                            item_path = item["path"]
                            if item["type"] == "file" and item_path.endswith(".gitignore"):
                                try:
                                    file_response = await session.get(item["download_url"])
                                    content = await file_response.text()
                                    self.gitignore_rules[item_path] = parse_gitignore(content.splitlines())
                                    logger.info("Parsed .gitignore: %s", item_path)
                                except Exception as e:
                                    logger.warning("Failed to parse .gitignore %s: %s", item_path, str(e))
                                    self.gitignore_rules[item_path] = None
                            elif item["type"] == "dir":
                                await search_gitignore(item_path)
                    elif response.status == 404:
                        logger.info("No .gitignore found at %s", path)
                    else:
                        logger.warning("Error fetching contents at %s: %d", path, response.status)
            except Exception as e:
                logger.error("Error searching .gitignore at %s: %s", path, str(e))

        await search_gitignore()

    async def is_text_file(self, path: str, content: bytes = None) -> bool:
        ext = Path(path).suffix.lstrip('.').lower()
        if ext in self.exclude_extensions:
            logger.info("Excluded file by extension: %s", path)
            return False
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type and (mime_type.startswith("text") or mime_type in [
            "application/json", "application/xml", "application/x-yaml", "application/javascript"
        ]):
            return True
        if content:
            try:
                content[:1024].decode("utf-8")
                return True
            except UnicodeDecodeError:
                return False
        return False

    async def list_files(self, session: aiohttp.ClientSession, path: str = "") -> List[str]:
        non_ignored_files = []
        try:
            async with session.get(
                "%s/%s/contents/%s" % (self.api_base, self.repo, path), headers=self.headers
            ) as response:
                if response.status == 200:
                    contents = await response.json()
                    for item in contents:
                        item_path = item["path"]
                        if not self.include_tests and "/tests/" in item_path.lower():
                            logger.info("Skipped test file: %s", item_path)
                            continue
                        if self._is_ignored(item_path):
                            logger.info("Ignored: %s", item_path)
                            continue
                        if item["type"] == "file":
                            non_ignored_files.append(item_path)
                        elif item["type"] == "dir":
                            non_ignored_files.extend(await self.list_files(session, item_path))
                elif response.status == 404:
                    logger.info("Path not found: %s", path)
                else:
                    logger.warning("Error listing files at %s: %d", path, response.status)
        except Exception as e:
            logger.error("Error listing files at %s: %s", path, str(e))
        return non_ignored_files

    def _is_ignored(self, path: str) -> bool:
        for gitignore_path, matcher in self.gitignore_rules.items():
            if matcher and path.startswith(gitignore_path.rsplit("/", 1)[0] or ""):
                if matcher(path):
                    return True
        return False

    async def count_loc(self, session: aiohttp.ClientSession, file_path: str) -> int:
        self.processed_files += 1
        progress = (self.processed_files / self.total_files * 100) if self.total_files else 0
        elapsed = time.time() - self.start_time
        logger.info(
            "Processing %d/%d (%.1f%%): %s [Elapsed: %.1fs]",
            self.processed_files, self.total_files, progress, file_path, elapsed
        )

        try:
            async with session.get(
                "%s/%s/contents/%s" % (self.api_base, self.repo, file_path), headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("size", 0) > self.max_file_size_bytes:
                        logger.warning("Skipping large file (> %.1f MB): %s", self.max_file_size_mb, file_path)
                        return 0
                    content = base64.b64decode(data["content"])
                    if await self.is_text_file(file_path, content):
                        try:
                            lines = content.decode("utf-8").splitlines()
                            line_count = len(lines)
                            ext = Path(file_path).suffix.lstrip('.').lower() or "no_extension"
                            if ext == "php" and any(tag in content.decode("utf-8").lower() for tag in ["<html", "<!doctype html"]):
                                ext = "php_html"
                            self.loc_counts[ext] = self.loc_counts.get(ext, 0) + line_count
                            self.loc_counts["total"] += line_count
                            logger.info("Counted %d lines in %s (extension: %s)", line_count, file_path, ext)
                            return line_count
                        except UnicodeDecodeError:
                            logger.warning("Encoding error in %s, skipping", file_path)
                            return 0
                    else:
                        logger.info("Skipping non-text file: %s", file_path)
                        return 0
                elif response.status == 403 and "rate limit" in (await response.text()).lower():
                    logger.error("GitHub API rate limit exceeded")
                    raise Exception("Rate limit exceeded")
                elif response.status == 403:
                    logger.error("Access denied for %s. Check token permissions", file_path)
                    return 0
                elif response.status == 404:
                    logger.warning("File not found: %s", file_path)
                    return 0
                else:
                    logger.warning("Failed to fetch %s: %d", file_path, response.status)
                    return 0
        except Exception as e:
            logger.error("Error counting LOC for %s: %s", file_path, str(e))
            return 0

    async def run(self) -> Dict[str, int]:
        try:
            async with aiohttp.ClientSession() as session:
                logger.info("Fetching .gitignore files...")
                await self.fetch_gitignore_files(session)
                logger.info("Listing repository files...")
                files = await self.list_files(session)
                self.total_files = len(files)
                logger.info("Found %d non-ignored files", self.total_files)
                batch_size = 10
                for i in range(0, len(files), batch_size):
                    batch = files[i:i + batch_size]
                    tasks = [self.count_loc(session, file_path) for file_path in batch]
                    await asyncio.gather(*tasks)
                with open('loc_counts.json', 'w') as f:
                    json.dump(self.loc_counts, f, indent=2)
                logger.info("Saved LOC counts to loc_counts.json")
                elapsed = time.time() - self.start_time
                logger.info("Completed in %.1f seconds", elapsed)
                return self.loc_counts
        except Exception as e:
            logger.error("Failed to complete LOC counting: %s", str(e))
            raise