"""
Custom job lot creation utilities (offline / image-based).

This module defines `CustomJobLotsCreator`, which:
- Seeds local working job lots from predefined items (`CustomJobLotsCreatorInfo`)
  and runs them through `LotProcessor`.
- Optionally creates custom job lots from one or more image files by extracting
  items via `ItemNameExtractor.extract_items_from_image`.

Flow overview
-------------
create():
    1) Refresh working job lots.
    2) Get predefined lots from `CustomJobLotsCreatorInfo`.
    3) Skip any lot that already exists on disk (by id).
    4) Process remaining lots and persist them; return the processed list.

create_custom(searches):
    - If `searches` is an iterable of image paths and the first path has an
      image-file extension, process each image via `create_custom_from_img`.

Assumptions / dependencies
--------------------------
- `JobLotsCreator` provides:
    * file_handler.refresh_working_job_lots()
    * check_job_lot_exists(id) -> bool
    * write(job_lot) -> None
    * lot_processor.process(job_lot) -> None
    * item_name_extractor.extract_items_from_image(path) -> list[Item]
- `CustomJobLotsCreatorInfo.create_with_uninitialized_items()` returns a list
  of `JobLot` objects.
- `JobLot` constructor used below accepts:
    JobLot(source, id, name, web_url, description=None, items=None, buy_price=None)

Caveats
-------
- `create_custom(searches)` expects `searches` to be an indexable sequence of
  string paths; if a single string is passed, `searches[0]` will be its first
  character, which may cause incorrect behavior. Preserved as-is.
- Only image-file extensions in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
  trigger processing in `create_custom`.
"""

from JobLot import JobLot
from JobLotsCreator import JobLotsCreator
from CustomJobLotsCreatorInfo import CustomJobLotsCreatorInfo

class CustomJobLotsCreator(JobLotsCreator):
    """
    Builds job lots from predefined data and from image inputs.

    Responsibilities
    ----------------
    - Bootstrap working job lots from a curated set (no network).
    - Deduplicate against stored lots by id.
    - Extract items from images to form ad-hoc custom lots.
    """
    def __init__(self):
        """
        Initialize the base creator and attach the predefined lots provider.
        """
        super().__init__()
        self.info = CustomJobLotsCreatorInfo()

    def create(self):
        """
        Create and persist job lots from predefined items.

        Returns
        -------
        list[JobLot]
            The list of newly processed (and persisted) job lots that were
            not already present in storage.
        """
        self.file_handler.refresh_working_job_lots()
        job_lots = self.info.create_with_uninitialized_items()
        updated_job_lots = []
        for lot in job_lots:
            if super().check_job_lot_exists(str(lot.id)) is True:
                continue
            self.lot_processor.process(lot)
            updated_job_lots.append(lot)
            super().write(lot)

        return updated_job_lots
    
    def create_custom(self, searches):
        """
        Create one or more custom job lots from image files.

        Parameters
        ----------
        searches : Sequence[str]
            A sequence of filesystem paths to images. Processing only occurs
            if the first element ends with a recognized image extension.

        Side Effects
        ------------
        - For each image, calls `create_custom_from_img` which extracts items,
          processes the lot, and writes it to storage.
        """
        self.file_handler.refresh_working_job_lots()
        if searches[0].lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')):
            n = 1
            for image in searches:
                self.create_custom_from_img(image, n)
                n += 1

    def create_custom_from_img(self, image_path, item_id):
        """
        Build a single custom job lot by extracting items from an image.

        Parameters
        ----------
        image_path : str
            Path to the source image to analyze for item extraction.
        item_id : int
            Numeric id used to create a negative lot id (-item_id) and a
            human-readable name ("custom{item_id}").

        Behavior
        --------
        - Extracts items via `self.item_name_extractor.extract_items_from_image`.
        - Creates a `JobLot` with source="custom" and a negative id.
        - Processes the lot and persists it.
        - Prints a blank line for readability.
        """
        items = self.item_name_extractor.extract_items_from_image(image_path)
        job_lot = JobLot("custom", -item_id, f"custom{item_id}", "NA", "Custom image", items)
        self.lot_processor.process(job_lot)
        super().write(job_lot)
        print("\n")


if __name__ == "__main__":
    # Example: seed and process predefined lots, then print item info.
    creator = CustomJobLotsCreator()
    job_lots = creator.create()
    for job_lot in job_lots:
        print(job_lot.get_item_info())
