"""
Oil Trading Desk — Persistence Layer

Handles optional persistent state via Hugging Face Datasets sync.
Used primarily to save and load the paper trading book state across server restarts.
"""

import json
import logging
import os
from pathlib import Path
import config
from hub import hub

logger = logging.getLogger("otd.persistence")

STATE_FILE = "paper_state.json"

try:
    from huggingface_hub import HfApi, hf_hub_download
    HAS_HF_HUB = True
except ImportError:
    HAS_HF_HUB = False


def load_state():
    """
    Load the paper book state from HF Hub if configured,
    otherwise fallback to local file if it exists.
    """
    state_path = Path(STATE_FILE)
    
    if HAS_HF_HUB and config.HF_TOKEN and config.PAPER_STATE_REPO:
        try:
            logger.info(f"Attempting to load state from HF Hub: {config.PAPER_STATE_REPO}")
            downloaded_path = hf_hub_download(
                repo_id=config.PAPER_STATE_REPO,
                repo_type="dataset",
                filename=STATE_FILE,
                token=config.HF_TOKEN
            )
            with open(downloaded_path, "r") as f:
                hub.paper = json.load(f)
            logger.info("Successfully loaded paper state from HF Hub")
            return
        except Exception as e:
            logger.warning(f"Failed to load from HF Hub (it may not exist yet): {e}")
            
    # Fallback to local
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                hub.paper = json.load(f)
            logger.info("Loaded paper state from local disk")
        except Exception as e:
            logger.error(f"Failed to load local state: {e}")


def save_state():
    """
    Save the paper book state to local disk,
    and optionally sync to HF Hub if configured.
    """
    if not hub.paper:
        return
        
    try:
        # Save local
        with open(STATE_FILE, "w") as f:
            json.dump(hub.paper, f, indent=2)
            
        # Sync to HF Hub
        if HAS_HF_HUB and config.HF_TOKEN and config.PAPER_STATE_REPO:
            api = HfApi(token=config.HF_TOKEN)
            api.upload_file(
                path_or_fileobj=STATE_FILE,
                path_in_repo=STATE_FILE,
                repo_id=config.PAPER_STATE_REPO,
                repo_type="dataset",
                commit_message="Update paper trading state"
            )
            logger.debug("Successfully synced paper state to HF Hub")
            
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
