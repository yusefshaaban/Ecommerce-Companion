"""
FileHandler utilities for persisting and exporting "job lot" data.

This module provides a `FileHandler` class that:
- Creates a predictable folder structure for outputs and operational files.
- Serializes/deserializes Python objects with `pickle` (supports lists and single objects).
- Maintains "working" and "all" job-lot pickle files.
- Exports human-readable, normalized text reports of job lots, items, and products.
- Manages a simple text file of saved searches for automation.

Expected data model (informal):
- `job_lot` objects used by this module should implement:
    - `__str__` for readable text output.
    - Attributes: `rating`, `accuracy_score`, `sell_price`, and `items` (iterable).
- Each `item` inside a `job_lot` should implement:
    - `__str__` for readable text output.
    - Attribute: `products` (iterable).
- Each `product` should implement `__str__` for readable text output.

Note:
- Pickle files store one pickled object after another (a "pickled stream").
- Removing objects expects those objects to have a `.name` attribute; only objects
  whose `.name` differs from `obj_name` are retained.
"""

from datetime import datetime
from normalize_text_indentation import normalize_text
import pickle
import os


class FileHandler:
    """
    High-level file I/O helper for job-lot workflows.

    Responsibilities:
        - Initialize dated/time-stamped output directories.
        - Write, append, remove, and load pickled objects from files.
        - Produce sorted, text-based reports of job lots/items/products.
        - Track and print "auto searches" from a flat text file.

    Directory layout created on initialization:
        ./Extracted_Info/
            Saved/
            <DD_MM_YYYY>/
        ./Operations/
            Images/
            working_job_lots.pkl
            all_job_lots.pkl
            searches.txt
        ./Other/
            Instructions.txt
    """

    def __init__(self):
        """
        Initialize the handler and ensure required directories/files exist.

        Creates date- and time-based attributes:
            - self.current_date: str formatted as "DD_MM_YYYY"
            - self.current_time: str formatted as "HH-MM-SS"

        Side effects:
            - Ensures the folder hierarchy exists (idempotent).
            - Touches/creates several operational files in append mode ('a') to
              guarantee their existence without truncating them.
        """
        self.current_date = datetime.now().strftime("%d_%m_%Y")
        self.current_time = datetime.now().strftime("%H-%M-%S")

        # Ensure directories exist
        os.makedirs('./Extracted_Info', exist_ok=True)
        os.makedirs('./Extracted_Info/Saved', exist_ok=True)
        os.makedirs('./Operations', exist_ok=True)
        os.makedirs('./Operations/Images', exist_ok=True)
        os.makedirs('./Other', exist_ok=True)

        # "Touch" operational files by opening in append mode.
        # Note: Files are intentionally not kept open; the handles are discarded.
        f = open("./Operations/working_job_lots.pkl", "a")
        f = open("./Operations/all_job_lots.pkl", "a")
        f = open("./Operations/searches.txt", "a")
        f = open("./Other/Instructions.txt", "a")

    def write_object(self, filename, obj):
        """
        Overwrite `filename` with a pickled representation of `obj`.

        If `obj` is a list, each element is pickled sequentially, forming a stream:
        [obj0][obj1]...[objN]. If `obj` is not a list, it's pickled once.

        Args:
            filename (str): Path to target pickle file (will be overwritten).
            obj (Any | list[Any]): The object(s) to pickle.

        Exceptions:
            Prints a message if pickling fails (e.g., unsupported types).
        """
        try:
            with open(filename, "wb") as f:
                if isinstance(obj, list):
                    for item in obj:
                        pickle.dump(item, f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as ex:
            print("Error during pickling object (Possibly unsupported):", ex)

    def refresh_working_job_lots(self):
        """
        Reset the working job lots file to an empty pickled stream.

        Effectively clears ./Operations/working_job_lots.pkl by writing an empty list
        (resulting in zero objects in the stream after rewrite).
        """
        self.write_object('./Operations/working_job_lots.pkl', [])

    def append_object(self, filename, obj):
        """
        Append a pickled representation of `obj` to the end of `filename`.

        If `obj` is a list, each element is appended sequentially.

        Args:
            filename (str): Path to target pickle file (opened in append-binary mode).
            obj (Any | list[Any]): The object(s) to append.

        Exceptions:
            Prints a message if pickling fails.
        """
        try:
            with open(filename, "ab") as f:
                if isinstance(obj, list):
                    for item in obj:
                        pickle.dump(item, f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as ex:
            print("Error during pickling object (Possibly unsupported):", ex)

    def remove_object(self, filename, obj_name):
        """
        Remove objects (by `.name` attribute) from a pickled stream.

        Works by reading all objects from `filename`, filtering out those whose
        `.name` equals `obj_name`, then rewriting the file with the retained objects.

        Args:
            filename (str): Path to the pickle file.
            obj_name (str | list[str]): Name(s) to remove. If a list is supplied,
                removal is performed for each name recursively.

        Notes:
            - Objects are expected to have a `.name` attribute. If an object does
              not, an exception may be raised during filtering; it is caught and
              printed, and processing continues.
        """
        if isinstance(obj_name, list):
            for name in obj_name:
                self.remove_object(filename, name)
            return
        try:
            objects = []
            with open(filename, "rb") as f:
                while True:
                    try:
                        obj = pickle.load(f)
                        # Keep objects whose name doesn't match the target
                        if obj.name != obj_name:
                            objects.append(obj)
                    except EOFError:
                        # End of pickled stream
                        break
                    except Exception as ex:
                        print("Error during unpickling object (Possibly unsupported):", ex)
            # Rewrite the file with remaining objects
            self.write_object(filename, objects)
        except Exception as ex:
            print("Error during unpickling object (Possibly unsupported):", ex)

    def load_object(self, filename):
        """
        Load all pickled objects from `filename` into a list.

        Args:
            filename (str): Path to the pickle file.

        Returns:
            list[Any]: List of unpickled objects (may be empty if file is empty
            or on error).

        Exceptions:
            Prints a message if unpickling fails; returns items accumulated up to
            the failure point.
        """
        try:
            items = []
            with open(filename, "rb") as f:
                while True:
                    try:
                        items.append(pickle.load(f))
                    except EOFError:
                        # Reached end of file/stream
                        break
        except Exception as ex:
            print("Error during unpickling object (Possibly unsupported):", ex)
        return items

    def write_sorted(self, source_filename):
        """
        Generate a normalized text report of job lots, sorted by key metrics.

        Sorting:
            Descending by (rating, accuracy_score, sell_price).

        Output:
            Writes a single text report to:
                ./Extracted_Info/<DD_MM_YYYY>/<HH-MM-SS>.txt

            The report includes three sections:
                1. Job Lots
                2. Items in Each Job Lot
                3. Products used to calculate item info

            After writing, the file is read back and normalized with `normalize_text`
            using:
                - indent="spaces", tabsize=4
                - eol="crlf" (Windows-friendly)
                - strip_trailing=True
                - ensure_final_newline=True
                - convert_all_tabs=False

        Args:
            source_filename (str): Path to the pickle file containing job_lot objects.
        """
        job_lots = self.load_object(source_filename)

        # Sort job lots by specified attributes (highest-rated first)
        job_lots = sorted(
            job_lots,
            key=lambda job_lot: (job_lot.rating, job_lot.accuracy_score, job_lot.sell_price),
            reverse=True
        )

        # Compose report path using current date/time
        with open(f"./Extracted_Info/{self.current_date}/{self.current_time}.txt", "w", encoding="utf-8") as file:
            file.write("Job Lots:"+"\n")
            file.write("_" * 160 + "\n")
            n = 1
            for job_lot in job_lots:
                file.write(f"{n}. ")
                self.write_job_lot(job_lot, file)
                n += 1

            file.write("\n\nItems in Each Job Lot:\n")
            file.write("_" * 161 + "\n")
            n = 1
            for job_lot in job_lots:
                file.write(f"{n}. ")
                self.write_item(job_lot, file)
                n += 1

            file.write("\n\nProducts used to calculate item info:\n")
            file.write("_" * 161 + "\n")
            n = 1
            for job_lot in job_lots:
                file.write(f"{n}. ")
                self.write_product(job_lot, file)
                n += 1

        # Normalize line endings/indentation to improve cross-platform readability
        with open(f"./Extracted_Info/{self.current_date}/{self.current_time}.txt", "r", encoding="utf-8") as file:
            content = file.read()

        normalized, stats = normalize_text(
            text=content,
            indent="spaces",         # or "tabs" or "keep"
            tabsize=4,
            eol="crlf",              # "lf" for Linux/Mac, "crlf" for Windows Notepad
            strip_trailing=True,
            ensure_final_newline=True,
            convert_all_tabs=False,
        )

        # Write normalized content back to the same file. newline="" preserves CRLF.
        with open(f"./Extracted_Info/{self.current_date}/{self.current_time}.txt", "w", encoding="utf-8", newline="") as file:
            file.write(normalized)
        print("Info has been saved")

    def write_progress(self, job_lot):
        """
        Append a single job lot's details to cumulative progress files.

        Files appended:
            - ./Extracted_Info/job_lots.txt
            - ./Extracted_Info/items.txt
            - ./Extracted_Info/products.txt

        Args:
            job_lot: A job lot object with `items` (and items with `products`).

        Notes:
            Each file receives a different level of detail:
                - job_lots.txt: job lot summary
                - items.txt: job lot + items
                - products.txt: job lot + items + products
        """
        with open("./Extracted_Info/job_lots.txt", "a", encoding="utf-8") as file:
            self.write_job_lot(job_lot, file)
            file.close()
        with open("./Extracted_Info/items.txt", "a", encoding="utf-8") as file:
            self.write_item(job_lot, file)
            file.close()
        with open("./Extracted_Info/products.txt", "a", encoding="utf-8") as file:
            self.write_product(job_lot, file)
            file.close()

    def write_job_lot(self, job_lot, file):
        """
        Write a one-line textual representation of a job lot.

        Args:
            job_lot: Object implementing `__str__`.
            file (io.TextIOBase): Open text file handle in write/append mode.
        """
        file.write(f"{job_lot}\n")

    def write_item(self, job_lot, file):
        """
        Write a job lot and its items in a simple, indented text format.

        Args:
            job_lot: Object with `__str__` and iterable `items`.
            file (io.TextIOBase): Open text file handle.
        """
        file.write(f"{job_lot}\n")
        file.write(f"\tItems in Job Lot:\n")
        for item in job_lot.items:
            file.write(f"\t{item}\n")
        file.write("\n")

    def write_product(self, job_lot, file):
        """
        Write a job lot, its items, and each item's products in an indented format.

        Args:
            job_lot: Object with `items`, where each item has iterable `products`.
            file (io.TextIOBase): Open text file handle.
        """
        file.write(f"{job_lot}\n")
        file.write(f"\tItems in Job Lot:\n")
        for item in job_lot.items:
            file.write(f"\t{item}\n")
            file.write(f"\t\tProducts in Item:\n")
            for product in item.products:
                file.write(f"\t\t{product}\n")
            file.write("\n")

    def reset_current_time(self):
        """
        Refresh `self.current_time` to the current clock time and touch a new output file.

        Side effects:
            - Updates `self.current_time` to "HH-MM-SS".
            - Opens (and implicitly creates) a new report file for the current date/time
              in append mode to prepare for subsequent writes.
        """
        self.current_time = datetime.now().strftime("%H-%M-%S")
        f = open(f"./Extracted_Info/{self.current_date}/{self.current_time}.txt", "a")

    def get_auto_searches(self):
        """
        Read the current saved searches from ./Operations/searches.txt.

        Returns:
            str: The file contents stripped of leading/trailing whitespace, or
                 an empty string if the file does not exist.
        """
        try:
            with open("./Operations/searches.txt", "r", encoding="utf-8") as f:
                current_searches = f.read().strip()
                return current_searches
        except FileNotFoundError:
            return ""

    def display_auto_searches(self):
        """
        Print the saved searches to stdout, or a default message if none are found.
        """
        current_searches = self.get_auto_searches()
        print(current_searches if current_searches else "No searches found.")

    def update_auto_searches(self, new_searches):
        """
        Overwrite ./Operations/searches.txt with new search terms.

        Args:
            new_searches (str): The content to write. If falsy, no changes are made.

        Side effects:
            - Writes `new_searches` to the file if provided.
            - Prints a status message indicating whether the searches were updated.
        """
        if new_searches:
            with open("./Operations/searches.txt", "w", encoding="utf-8") as f:
                f.write(new_searches)
            print("Searches updated.")
        else:
            print("Searches unchanged.")



if __name__ == "__main__":
    file_handler = FileHandler()
    objects_to_remove = [
        "110 Cosmetic Wholesale Makeup skincare Joblot Beauty Bundle Make up NEW",
        "Nivea FEEL PAMPERED Skincare Regime Bath & Body Gift Set - Cream Shower Gel Deo",
        "Mixed branded, make up hair & beauty bundle.",
        "NIVEA Feel Flawless Women's Gift Set with Skincare Essentials 4 Products",
        "15 item Luxury Beauty gift box bundle, Skincare, Present - RRP £100-UK Seller",
        "MAKE UP BUNDLE SKINCARE WHOLESALE JOBLOT MAKEUP CHRISTMAS GIFT - 15 ITEMS NEW",
        "Job Lot Beauty Products See Picture & Description & Cult Beauty Makeup Bag  - BN",
        "Make up Bundle Make-up Skincare Joblot Christmas Gift Makeup  RRP £100+ 30 Items",
        "Beauty Bundle - 8 Items - Kanzen, Collection, Halo RRP £50",
        "Mixed Lot Beauty Bundle Products Skin Care Body Face SO UNIQUE DOVE IPANEMA 72",
        "Below The Belt Ballers Duo Gift Set Fresh & Dry Balls Fresh & Cool 2 x 75ml",
        "9 Item Beauty Bundle...New.",
        "SodaStream 2 x Older Style Plastic Bottles (Used) + Brand‑New Pepsi BUNDLE",
        "Ladies Pamper Hamper Gift Spa Box Set For Her Personalised Letterbox Gift",
        "Beauty Bundle/Joblot Including Lip Balm Lipstick and Magnetic Lashes, Read Descr",
        "NEW MINT JOB LOT OF 2 STORY OF SUN RECORDS  BOX SETS 6 CDS IN TOTAL",
        "20X BRAND NEW ITEMS Clearance Sale Pallet Wholesale Box JOB LOT Warehouse Stock",
        "Job Lot Box- Random Cosmetics Clearance & Beauty 10+ Items Worth £40+ Brand New"
    ]
    
    # file_handler.remove_object("./Operations/working_job_lots.pkl", objects_to_remove)
    # file_handler.remove_object("./Operations/all_job_lots.pkl", objects_to_remove)
    # file_handler.write_sorted('./Operations/working_job_lots.pkl')


    # job_lots = file_handler.load_object("./Operations/working_job_lots.pkl")
    # print(type((job_lots)[0]))
    # job_lot = next(filter(lambda x: x.name == "10 Cosmetic Wholesale Makeup skincare Joblot Beauty Bundle Make up NEW", job_lots), None)
    # if job_lot is not None:
    #     items = job_lot.items
    #     for item in items:
    #         print(item.brand_name)
    #         products = item.products
    #         for product in products:
    #             print(f"Product Name: {product.name}, Buy Price: {product.buy_price}, Accuracy Score: {product.accuracy_score}")
    #             print(f"Product brand: {product.brand_name}")
    #             print(f"Product Variant: {product.variant_name}")
    # else:
    #     print("Job lot not found.")