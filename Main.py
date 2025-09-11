import os
import subprocess
import platform
import tkinter as tk
from tkinter import filedialog
from PIL import Image  # type: ignore

from EbayJobLotsCreator import EbayJobLotsCreator
from CustomJobLotsCreator import CustomJobLotsCreator
from Item import Item
from ItemProcessor import ItemProcessor
from FileHandler import FileHandler
from ItemNameExtractor import ItemNameExtractor
import GitHandler


"""
Interactive CLI for sourcing and processing job lots.

Overview
--------
`Main` presents a simple text menu to:
1) Search eBay for job lots and process them.
2) Build items directly from brand/variant names and fetch product info.
3) Extract items from one or more images (file dialog, if available).
4) Extract items from eBay links.
5) Open the folder containing extracted info.
6) Open local instructions file.
7) Edit automatic searches used by option (1).
8) Exit.

Key behavior & dependencies
---------------------------
- Uses `EbayJobLotsCreator` and `CustomJobLotsCreator` to create/persist lots.
- Uses `FileHandler` to manage state, searches, and OS actions.
- Uses `ItemProcessor` to enrich items with product/pricing data.
- Attempts to create a single hidden Tk root for image file selection; falls
  back to headless mode if no display is available.

Caveats
-------
- `run()` invokes itself again after most actions, leading to nested calls
  rather than a true loop. This is preserved as-is and may deepen the call
  stack during long sessions.
- OS-specific opening of folders/files is done via `os.startfile` (Windows),
  `open` (macOS), or `xdg-open` (Linux).
"""


class Main:
    """
    Interactive entry point that wires together creators, processors, and I/O.
    """
    def __init__(self):
        """
        Initialize collaborators and (optionally) a hidden Tk root for dialogs.

        Attributes
        ----------
        ebayJobLotsCreator : EbayJobLotsCreator
        customJobLotsCreator : CustomJobLotsCreator
        file_handler : FileHandler
        item_processor : ItemProcessor
        item_name_extractor : ItemNameExtractor
        root : tk.Tk | None
            Hidden Tk root for file dialogs; None in headless environments.
        """
        self.ebayJobLotsCreator = EbayJobLotsCreator()
        self.customJobLotsCreator = CustomJobLotsCreator()
        self.file_handler = FileHandler()
        self.item_processor = ItemProcessor()
        self.item_name_extractor = ItemNameExtractor()
        GitHandler.self_update()

        # Create ONE Tk root and keep it hidden
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as e:
            print("GUI not available (no display). File dialog won't open.")
            print(f"Details: {e}")
            self.root = None  # continue without GUI

    def _choose_image_files(self):
        """
        Open a file dialog to select image files (if GUI is available).

        Returns
        -------
        list[str]
            List of selected file paths; empty if GUI is unavailable or the
            dialog is canceled.
        """
        if not self.root:
            return []

        try:
            self.root.attributes("-topmost", True)
            self.root.update()
            paths = filedialog.askopenfilenames(
                parent=self.root,
                title="Select Image Files",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
            )
            # askopenfilenames returns a tuple; normalize to list
            return list(paths)
        finally:
            # Best-effort cleanup of "always on top" attribute
            try:
                self.root.attributes("-topmost", False)
                self.root.update()
            except tk.TclError:
                pass

    def run(self):
        """
        Present the main menu and dispatch to the selected action.

        Notes
        -----
        - Method re-invokes itself after most actions, effectively creating a
          recursive interaction loop (preserved as-is).
        - User input is read from stdin.
        """
        print("Please choose an option:\n")
        print("1. Automatically search for eBay job lots")
        print("2. Get items info from names")
        print("3. Extract items from images")
        print("4. Extract items from links")
        print("5. View extracted info")
        print("6. View Instructions")
        print("7. Settings")
        print("8. Exit\n")

        choice = input("Enter your choice (1, 2, 3, 4, 5, 6, 7, or 8): ")

        if choice == "1":
            self.file_handler.reset_current_time()
            self.search_for_job_lots()
            self.run()

        elif choice == "2":
            brand_names = input("\nPlease enter the brand names or leave blank (separated by commas): ")
            variant_names = input("Please enter the variant names (separated by commas): ")
            num_brands = len(brand_names.split(","))
            num_variants = len(variant_names.split(","))
            items = []
            if num_brands + num_variants == 0:
                print("No brand or variant names provided.")
                self.run()
                return
            for i in range(max(num_brands, num_variants)):
                brand_name = brand_names.split(",")[i].strip() if i < num_brands else ""
                variant_name = variant_names.split(",")[i].strip() if i < num_variants else ""
                name = (brand_name + " " + variant_name).strip()
                item = Item(name, brand_name, variant_name, 1)
                params={
                    "filter": f"filter=",
                    "buyingOptions": f"buyingOptions:{{FIXED_PRICE}}",
                    "conditions": f"conditions:{{NEW}}",
                    "deliveryCountry": f"deliveryCountry:GB",
                    "itemLocationCountry": f"itemLocationCountry:GB"
                }
                self.item_processor.process(item, params)
                items.append(item)
            for item in items:
                print("\n")
                print(item)
            self.run()

        elif choice == "3":
            try:
                file_paths = self._choose_image_files()
            except tk.TclError as e:
                print("Failed to open file dialog. Are you running in a GUI session?")
                print(f"Details: {e}")
                self.run()
                return

            if file_paths:
                self.file_handler.reset_current_time()
                jobLot = self.customJobLotsCreator.create_custom(file_paths)
            else:
                print("No file selected.")

            self.run()

        elif choice == "4":
            links = input("\nPlease enter the links (separated by commas): ")
            self.file_handler.reset_current_time()
            self.ebayJobLotsCreator.create_custom(links)
            
            self.run()

        elif choice == "5":
            file_path = "./Extracted_Info"
            if platform.system() == "Windows":
                os.startfile(os.path.abspath(file_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", os.path.abspath(file_path)])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", os.path.abspath(file_path)])
            self.run()
        
        elif choice == "6":
            file_path = "./Other/Instructions.txt"
            if platform.system() == "Windows":
                os.startfile(os.path.abspath(file_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", os.path.abspath(file_path)])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", os.path.abspath(file_path)])
            self.run()

        elif choice == "7":
            print("1. Edit automatic searches")
            print("2. Exit settings\n")
            setting_choice = input("Enter your choice (1 or 2): ")
            if setting_choice == "1":
                self.edit_auto_searches()
            elif setting_choice == "2":
                print("Exiting settings.")
            else:
                print("Invalid choice.")
            self.run()            

        elif choice == "8":
            print("Exiting the program.")
            GitHandler.self_push_all("Operations/all_job_lots.pkl")
            return
        
        else:
            print("Invalid choice.")
            self.run()

    def search_for_job_lots(self):
        """
        Run automatic eBay searches listed in the configuration.

        Behavior
        --------
        - Refreshes the working job lots file.
        - Reads newline-separated search terms from `FileHandler.get_auto_searches()`.
        - For each non-empty term, triggers `EbayJobLotsCreator.create(term, 5)`.
        """
        self.file_handler.refresh_working_job_lots()
        searches = self.file_handler.get_auto_searches()
        for search in searches.split("\n"):
            search = search.strip()
            if search:
                self.ebayJobLotsCreator.create(search, 5)

    def edit_auto_searches(self):
        """
        Display current automatic searches and optionally replace them.

        Notes
        -----
        - New searches are provided as a comma-separated string and stored as
          newline-separated entries.
        """
        print("\nCurrent searches:")
        self.file_handler.display_auto_searches()

        new_searches = input("\nEnter new searches (separated by commas) or leave blank to keep current: ").strip()
        if new_searches:
            new_searches = "\n".join([s.strip() for s in new_searches.split(",") if s.strip()])
            self.file_handler.update_auto_searches(new_searches)


if __name__ == "__main__":
    main = Main()
    print("Welcome!")
    main.run()
