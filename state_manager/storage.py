import os
import datetime
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv

from shared.schemas.state_schema import GlobalState

load_dotenv()

class StateManager:
    """
    Manages the global state of the pipeline runs using MongoDB.
    Provides snapshotting and version history.
    """
    def __init__(self):
        # Allow connecting via MONGO_URI, default to localhost
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["agentic_project"]
        
        # Collections
        self.runs: Collection = self.db["runs"]
        self.snapshots: Collection = self.db["snapshots"]

    def create_run(self, prompt: str) -> str:
        """
        Initializes a new pipeline run.
        Returns the run_id.
        """
        # Create a unique run ID based on timestamp
        run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        run_doc = {
            "run_id": run_id,
            "prompt": prompt,
            "created_at": datetime.datetime.now()
        }
        self.runs.insert_one(run_doc)
        
        # Initialize the global state
        initial_state = GlobalState(prompt=prompt, version=1)
        
        # Create the first snapshot (v1)
        self.snapshot(run_id, initial_state)
        
        return run_id

    def get_state(self, run_id: str, version: Optional[int] = None) -> Optional[GlobalState]:
        """
        Retrieves the state for a specific run.
        If version is None, retrieves the latest version.
        """
        query = {"run_id": run_id}
        if version is not None:
            query["version"] = version
            
        # Get the highest version matching the query
        snapshot_doc = self.snapshots.find_one(
            query,
            sort=[("version", -1)]
        )
        
        if not snapshot_doc:
            return None
            
        state_dict = snapshot_doc.get("state", {})
        return GlobalState(**state_dict)

    def snapshot(self, run_id: str, state: GlobalState) -> int:
        """
        Saves the state as a new version.
        Returns the new version number.
        """
        # Find current highest version
        latest = self.snapshots.find_one(
            {"run_id": run_id},
            sort=[("version", -1)]
        )
        
        new_version = (latest["version"] + 1) if latest else state.version
        state.version = new_version
        
        snapshot_doc = {
            "run_id": run_id,
            "version": new_version,
            "state": state.model_dump(mode="json"),
            "created_at": datetime.datetime.now()
        }
        self.snapshots.insert_one(snapshot_doc)
        
        return new_version

    def history(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Returns the version history for a given run.
        """
        cursor = self.snapshots.find(
            {"run_id": run_id},
            {"_id": 0, "run_id": 1, "version": 1, "created_at": 1}
        ).sort("version", 1)
        return list(cursor)

    def revert(self, run_id: str, target_version: int) -> Optional[GlobalState]:
        """
        Reverts the state to a previous version by creating a new snapshot
        that copies the target version's state.
        """
        target_state = self.get_state(run_id, target_version)
        if not target_state:
            raise ValueError(f"Version {target_version} not found for run {run_id}")
            
        # Create a new snapshot based on the old state
        new_version = self.snapshot(run_id, target_state)
        target_state.version = new_version
        return target_state
