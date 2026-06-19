import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class TranscriptionHistory:
    def __init__(self, history_file: str = "transcription_history.json", max_entries: int = 1000):
        self.history_file = history_file
        self.stats_file = "usage_statistics.json"  # Separate statistics file
        self.max_entries = max_entries
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        """Ensure the history and statistics files exist."""
        if not os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception as e:
                logging.error(f"Could not create the history file {self.history_file}: {e}")

        if not os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except Exception as e:
                logging.error(f"Could not create the statistics file {self.stats_file}: {e}")

    def add_transcription(self, text: str, duration: float, used_gemini: bool = False, mode: str = "gemini_only") -> None:
        """Add a new transcription to the history."""
        try:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'text': text,
                'duration': duration,
                'used_gemini': used_gemini,
                'mode': mode
            }

            with open(self.history_file, 'r+', encoding='utf-8') as f:
                history = json.load(f)
                history.insert(0, entry)

                if len(history) > self.max_entries:
                    history = history[:self.max_entries]

                f.seek(0)
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.truncate()

        except Exception as e:
            logging.error(f"Error adding transcription to the history: {e}")

    def get_recent_transcriptions(self, limit: int = 10) -> List[Dict]:
        """Get the most recent transcriptions."""
        try:
            if not os.path.exists(self.history_file):
                return []

            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history[:limit]
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error reading the history {self.history_file}: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error reading the history: {e}")
            return []

    def search_transcriptions(self, query: str) -> List[Dict]:
        """Search for transcriptions containing the given text."""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return [entry for entry in history if query.lower() in entry['text'].lower()]
        except Exception as e:
            logging.error(f"Error searching the history: {e}")
            return []

    def get_statistics(self) -> Dict:
        """Compute statistics from the transcription history."""
        default_stats = {
            'last_24h': {'total': 0, 'gemini': 0},
            'last_week': {'total': 0, 'gemini': 0},
            'last_month': {'total': 0, 'gemini': 0},
            'total_duration': 0,
            'avg_duration': 0,
            'total_gemini_requests': 0
        }

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)

            if not history:
                return default_stats

            now = datetime.now()
            last_24h_limit = now - timedelta(hours=24)
            last_week_limit = now - timedelta(days=7)
            last_month_limit = now - timedelta(days=30)

            stats = {
                'last_24h': {'total': 0, 'gemini': 0},
                'last_week': {'total': 0, 'gemini': 0},
                'last_month': {'total': 0, 'gemini': 0},
                'total_duration': 0.0,
                'total_gemini_requests': 0
            }

            total_entries = len(history)

            for entry in history:
                try:
                    timestamp = datetime.fromisoformat(entry['timestamp'])
                    duration = float(entry.get('duration', 0.0))
                    used_gemini = entry.get('used_gemini', False)

                    if timestamp >= last_24h_limit:
                        stats['last_24h']['total'] += 1
                        if used_gemini:
                            stats['last_24h']['gemini'] += 1

                    if timestamp >= last_week_limit:
                        stats['last_week']['total'] += 1
                        if used_gemini:
                            stats['last_week']['gemini'] += 1

                    if timestamp >= last_month_limit:
                        stats['last_month']['total'] += 1
                        if used_gemini:
                            stats['last_month']['gemini'] += 1

                    stats['total_duration'] += duration
                    if used_gemini:
                        stats['total_gemini_requests'] += 1
                except (ValueError, TypeError) as e:
                    logging.warning(f"Skipping malformed history entry: {entry}. Error: {e}")
                    total_entries -= 1  # Do not count corrupt entries toward the average

            if total_entries > 0:
                stats['avg_duration'] = stats['total_duration'] / total_entries
            else:
                stats['avg_duration'] = 0.0

            return stats

        except Exception as e:
            logging.error(f"Error getting statistics: {e}")
            return default_stats
