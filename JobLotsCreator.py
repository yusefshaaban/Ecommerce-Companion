"""
Job lot creation and persistence utilities.

This module defines `JobLotsCreator`, a coordinator responsible for:
- (Placeholder) creating job lots via `create()` (currently unimplemented),
- checking if a stored job lot with a given id exists,
- writing a job lot to persistent collections while avoiding duplicates,
  and ensuring the "working" collection is sorted.

File storage layout
-------------------
- ./Operations/all_job_lots.pkl
- ./Operations/working_job_lots.pkl

Dependencies / expected interfaces
----------------------------------
LotProcessor
    Processes a lot into computed fields (initialized but not used here).
FileHandler
    - load_object(path) -> Any
        Loads and returns a Python object (typically a list of job lots).
    - append_object(path, obj) -> None
        Appends `obj` to the serialized collection at `path`.
    - write_sorted(path) -> None
        Sorts and persists the collection at `path`. The sort criteria
        are defined within `FileHandler`.
ItemNameExtractor
    Utility for extracting item names (initialized but not used here).

Assumptions & caveats
---------------------
- `check_job_lot_exists` gracefully handles a missing all_job_lots file by
  returning False.
- `write` assumes the pickle files exist or that `FileHandler` can handle
  creation on demand.
- Membership checks (`if job_lot not in ...`) rely on the job lot object's
  equality semantics (`__eq__`); if not implemented, duplicates may still
  occur across sessions or processes.
- No concurrency/atomicity guarantees: simultaneous writers could race.
"""

import os
from LotProcessor import LotProcessor
from FileHandler import FileHandler
from ItemNameExtractor import ItemNameExtractor


class JobLotsCreator:
    """
    Coordinates the lifecycle of job lots: creation (stub), existence checks,
    and persistence into "all" and "working" collections on disk.
    """

    def __init__(self):
        """
        Initialize collaborators.

        Attributes
        ----------
        lot_processor : LotProcessor
            Processor for computing lot-level metrics (not used in this snippet).
        file_handler : FileHandler
            Persistence helper for reading/writing pickled collections.
        item_name_extractor : ItemNameExtractor
            Helper for extracting/normalizing item names (not used here).
        """
        self.lot_processor = LotProcessor()
        self.file_handler = FileHandler()
        self.item_name_extractor = ItemNameExtractor()

    def create(self):
        """
        Create job lots and persist them.

        Notes
        -----
        This is a placeholder. A typical implementation might:
        1) Gather raw inputs (files, web data, etc.).
        2) Build job lot objects (using `ItemNameExtractor` as needed).
        3) Process lots with `self.lot_processor`.
        4) Persist via `self.write(job_lot)`.
        """
        pass

    def check_job_lot_exists(self, id, listing_price, postage_price):
        """
        Check whether a job lot with the given identifier is already stored.

        Parameters
        ----------
        id : Any
            Identifier to look up. Comparison is performed using `str(id)`.

        Returns
        -------
        bool
            True if a job lot with a matching id exists in
            './Operations/all_job_lots.pkl'; False otherwise.

        Notes
        -----
        - If the file doesn't exist, the method returns False.
        - Uses string comparison (`str(job_lot.id) == str(id)`) to tolerate
          type differences (e.g., int vs. str).
        """
        if os.path.exists("./Operations/all_job_lots.pkl"):
            job_lots = self.file_handler.load_object("./Operations/all_job_lots.pkl")
            for job_lot in job_lots:
                if str(job_lot.id) == str(id) and job_lot.buy_listing_price == listing_price and job_lot.postage_price == postage_price:
                    return True
        return False
    
    def write(self, job_lot):
        """
        Append `job_lot` to persistent collections if not already present,
        and ensure the working set is sorted.

        Behavior
        --------
        - Loads './Operations/all_job_lots.pkl' and appends `job_lot` if absent.
        - Loads './Operations/working_job_lots.pkl' and appends `job_lot` if absent.
        - Calls `write_sorted('./Operations/working_job_lots.pkl')` to persist a
          sorted working list.

        Parameters
        ----------
        job_lot : Any
            The lot object to store. Membership checks rely on `==` semantics.

        Side Effects
        ------------
        - Reads and writes to the pickle files in ./Operations/.
        - May create or modify these files depending on `FileHandler` behavior.

        Caveats
        -------
        - Not atomic; concurrent writers can cause race conditions.
        - Duplicate detection is based on list membership (`in`), which depends
          on `__eq__` of `job_lot`. If equality isn't defined, duplicates may slip in.
        """
        all_job_lots = self.file_handler.load_object("./Operations/all_job_lots.pkl")
        if job_lot not in all_job_lots:
            self.file_handler.append_object("./Operations/all_job_lots.pkl", job_lot)
        working_job_lots = self.file_handler.load_object("./Operations/working_job_lots.pkl")
        if job_lot.rating < -100:
            print("Rating is too low, discarding")
        elif job_lot in working_job_lots:
            print("Job lot is already in working set, discarding")
        else:
            self.file_handler.append_object("./Operations/working_job_lots.pkl", job_lot)
            print("Info has been updated")

        self.file_handler.write_sorted('./Operations/working_job_lots.pkl')

if __name__ == "__main__":
    creator = JobLotsCreator()
    # Example usage (uncomment to test):
    exists = creator.check_job_lot_exists('v1|267075364121|0', 28.79, 0.0)
    print("Exists:", exists)