"""
Predefined custom job lots for testing and seeding.

This module defines `CustomJobLotsCreatorInfo`, a concrete subclass of
`JobLotsCreator` that builds a set of curated `JobLot` objects composed
of hand-entered `Item` instances. It’s useful for local testing,
demonstrations, and pipelines that expect `JobLot` inputs without
calling external APIs.

Key points
----------
- Items are grouped into themed bundles (comments show the index ranges).
- `create_with_uninitialized_items()` constructs 10 `JobLot` objects
  (`custom_job_lot1` .. `custom_job_lot10`) but, as written, only returns
  the first three in `self.custom_job_lots`. This is intentional here to
  preserve the original behavior.
- Each `Item` takes: (full_name, brand_name, variant_name, quantity).
- Each `JobLot` is initialized with arguments expected by your project’s
  `JobLot` class; order and semantics are preserved exactly as in the
  original code.

Assumptions / dependencies
--------------------------
- `JobLotsCreator` provides baseline functionality (e.g., file handling).
- `JobLot` supports the given constructor signature used below.
- `Item` supports the given constructor signature used below.

Caveats
-------
- The hard-coded index slicing (e.g., `ci[0:13]`) assumes the `custom_items`
  list order remains unchanged.
- Prices, titles, and URLs are static examples for local workflows; they
  are not validated against live sources.
"""

from JobLotsCreator import JobLotsCreator
from Item import Item
from JobLot import JobLot

class CustomJobLotsCreatorInfo(JobLotsCreator):
    """
    Creates predefined, static `JobLot` objects from a hard-coded catalog
    of `Item`s grouped into themed bundles.

    Use this class when you want deterministic input data without network
    calls (e.g., unit tests, demos).
    """
    def __init__(self):
        """
        Initialize the base creator and populate `self.custom_items` with
        a curated list of `Item` instances. Inline comments document the
        groupings (bundles) and index ranges used downstream.
        """
        super().__init__()
        # Create items based on eBay job lots data
        self.custom_items = [
            # Bundle 1 items
            Item("Nails Inc. Porchester Square Nail Polish 10ml", "Nails Inc.", "Porchester Square Nail Polish 10ml", 1),   # 0
            Item("SportFX CoolDown Primer Recovery Gel 30ml", "SportFX", "CoolDown Primer Recovery Gel 30ml", 1),         # 1
            Item("Jelly Pong Pong Lip Scrub", "Jelly Pong Pong", "Lip Scrub", 1),                 # 2
            Item("Cougar 6 Shades of Nude Eyeshadow Contour Set", "Cougar", "6 Shades of Nude Eyeshadow Contour Set", 1),      # 3
            Item("417 Time Control Firming Radiant Mud Mask 20ml", "417", "Time Control Firming Radiant Mud Mask 20ml", 1),        # 4
            Item("MayBeauty The Incredible Pore Strip 2Pcs", "MayBeauty", "The Incredible Pore Strip 2Pcs", 1),        # 5
            Item("The Beauty Crop GRLPWR Liquid Lipstick Piedaho 4ml", "The Beauty Crop", "GRLPWR Liquid Lipstick Piedaho 4ml", 1), # 6
            Item("Kawaii Brush Cleansing Egg", "Kawaii", "Brush Cleansing Egg", 1),                         # 7
            Item("Essence Brushed Metals Nail Polish Steel The Show 01 8ml", "Essence", "Brushed Metals Nail Polish Steel The Show 01 8ml", 1), # 8
            Item("Laritzy Cosmetics Veto Long Lasting Liquid Lipsticks 3.1g", "Laritzy Cosmetics", "Veto Long Lasting Liquid Lipsticks 3.1g", 1), # 9
            Item("Avant Supreme Hyaluronic Acid Duo Moisturiser 10ml", "Avant", "Supreme Hyaluronic Acid Duo Moisturiser 10ml", 1),  # 10
            Item("Trifle Cosmetics Buttercream Hydrating Body Lotion 30ml", "Trifle Cosmetics", "Buttercream Hydrating Body Lotion 30ml", 1), # 11
            Item("Pixi By Petra Endless Silky Eye Pen 1.2g", "Pixi By Petra", "Endless Silky Eye Pen 1.2g", 1),    # 12

            # Bundle 2 items
            Item("Too Faced Primer", "Too Faced", "Primer", 1),                                # 13
            Item("ELLIE SAAB GIRL OF NOW LOVELY 1.5ml", "Ellie Saab", "GIRL OF NOW LOVELY 1.5ml", 1),            # 14
            Item("Laura Mercier Blush", "Laura Mercier", "Blush", 1),                         # 15
            Item("OFRA Pressed Powder", "OFRA", "Pressed Powder", 1),                                  # 16
            Item("Lord Berry Lipstick", "Lord Berry", "Lipstick", 1),                            # 17
            Item("OFRA Lip Gloss", "OFRA", "Lip Gloss", 1),                                       # 18
            Item("Dr Lipp Balm", "Dr Lipp", "Balm", 1),                                      # 19
            Item("Avena Moisturiser", "Avena", "Moisturiser", 1),                                   # 20
            Item("Wild Nutrition Wellness", "Wild Nutrition", "Wellness", 1),                    # 21
            Item("This Works Sleep Mist", "This Works", "Sleep Mist", 1),                          # 22
            Item("Bare Minerals Serum", "Bare Minerals", "Serum", 1),                         # 23

            # Bundle 3 items (18 item bundle)
            Item("Superdrug Face Mask Pink Clay", "Superdrug", "Face Mask Pink Clay", 1),                   # 24
            Item("Superdrug Face Mask Cucumber", "Superdrug", "Face Mask Cucumber", 1),                    # 25
            Item("Me by Superdrug Salicylic Acid Cleanser", "Me by Superdrug", "Salicylic Acid Cleanser", 1),   # 26
            Item("Sophia Mabelle Eyeshadow Palette", "Sophia Mabelle", "Eyeshadow Palette", 1),           # 27
            Item("Barry M Eyeshadow", "Barry M", "Eyeshadow", 1),                                 # 28
            Item("Gruum Aftersun Face Oil Bar", "Gruum", "Aftersun Face Oil Bar", 1),                         # 29
            Item("Delilah Eye Liner", "Delilah", "Eye Liner", 1),                                        # 30
            Item("Revolution Super Highlighter", "Revolution", "Super Highlighter", 1),                   # 31
            Item("Habitat Candle Amber and Patchouli", "Habitat", "Candle Amber and Patchouli", 1),                # 32
            Item("Colour Couture Nail Varnish", "Colour Couture", "Nail Varnish", 2),                # 33
            Item("The Body Shop Almond Milk Body Butter", "The Body Shop", "Almond Milk Body Butter", 1),       # 34
            Item("Dirty Works Nail File", "Dirty Works", "Nail File", 2),                         # 35
            Item("Dirty Works Nail Cutter", "Dirty Works", "Nail Cutter", 1),                       # 36
            Item("MS Meditate Body Butter", "MS Meditate", "Body Butter", 1),                       # 37
            Item("Yodeyma Skincare Testers", "Yodeyma", "Skincare Testers", 1),                          # 38
            Item("Bubble T Bath Crumble Pink Grapefruit", "Bubble T", "Bath Crumble Pink Grapefruit", 1),            # 39

            # Bundle 4 items (Clarins/Lancome samples)
            Item("Clarins Total Eye Lift 3ml", "Clarins", "Total Eye Lift 3ml", 1),                        # 40
            Item("Clarins SOS Hydra 3ml", "Clarins", "SOS Hydra 3ml", 1),                             # 41
            Item("Lancome Day Cream", "Lancome", "Day Cream", 1),                                 # 42
            Item("Lancome Night Cream", "Lancome", "Night Cream", 1),                               # 43

            # Bundle 5 items (Avon bundle)
            Item("Avon Faraway Beyond the Moon Body Lotion", "Avon", "Faraway Beyond the Moon Body Lotion", 1),             # 44
            Item("Avon Perfect Nonsense Choco Tuberose EDP", "Avon", "Perfect Nonsense Choco Tuberose EDP", 1),             # 45
            Item("Avon Perfect Nonsense Choco Tuberose Shower Gel", "Avon", "Perfect Nonsense Choco Tuberose Shower Gel", 1),      # 46
            Item("Japanese GeGe Bear Pressed Powder", "Japanese GeGe Bear", "Pressed Powder", 1),      # 47
            Item("Avon Show Glow Lip Gloss", "Avon", "Show Glow Lip Gloss", 1),                             # 48
            Item("Avon Planet Spa Sleep Serenity Pillow Mist", "Avon", "Planet Spa Sleep Serenity Pillow Mist", 3),           # 49
            Item("Avon Body Spray Magnolia", "Avon", "Body Spray Magnolia", 1),                             # 50
            Item("Avon Body Spray Lavender and Chamomile", "Avon", "Body Spray Lavender and Chamomile", 1),               # 51
            Item("Avon Body Spray Cherry Blossom", "Avon", "Body Spray Cherry Blossom", 1),                       # 52

            # Bundle 6 items (Beauty samples)
            Item("Augustinus Bader The Body Cleanser 8ml", "Augustinus Bader", "The Body Cleanser 8ml", 1),   # 53
            Item("Amly Day Light 10ml", "Amly", "Day Light 10ml", 1),                                  # 54
            Item("BYOMA SPF50 UltraLight Face Fluid 5ml", "BYOMA", "SPF50 UltraLight Face Fluid 5ml", 1),           # 55
            Item("Inlight Body Butter 15ml", "Inlight", "Body Butter 15ml", 1),                         # 56
            Item("Cetaphil Gentle Skin Cleanser 29ml", "Cetaphil", "Gentle Skin Cleanser 29ml", 1),               # 57
            Item("Make Up For Ever Mist Fix 24hr 30ml", "Make Up For Ever", "Mist Fix 24hr 30ml", 1),      # 58

            # Bundle 7 items (Perfume samples)
            Item("LOreal Bright Face Reveals Serum 1ml", "LOreal", "Bright Face Reveals Serum 1ml", 5),               # 59
            Item("La Roche Posay Oil Correct Photocorrection 50 SPF 3ml", "La Roche Posay", "Oil Correct Photocorrection 50 SPF 3ml", 3), # 60
            Item("La RochePosay Duo M Creme AntiImperfections 3ml", "La Roche Posay", "Duo M Creme AntiImperfections 3ml", 3), # 61
            Item("Yves Saint Laurent Libre Flowers Flames 1.2ml Spray Perfume", "Yves Saint Laurent", "Libre Flowers Flames 1.2ml Spray Perfume", 1), # 62
            Item("Yves Saint Laurent Libre LAbsolu Platine Parfum 1.2ml Spray Perfume", "Yves Saint Laurent", "Libre LAbsolu Platine Parfum 1.2ml Spray Perfume", 1), # 63
            Item("REM 1.5ml Splash Perfume", "REM", "1.5ml Splash Perfume", 1),                              # 64
            Item("Pepe Jeans London Calling for Her 1.5ml Spray Perfume", "Pepe Jeans", "London Calling for Her 1.5ml Spray Perfume", 1), # 65
            Item("VO5 Fixing Spray for Glitter 50ml", "VO5", "Fixing Spray for Glitter 50ml", 1),                     # 66

            # Bundle 8 items (Foundation bundle)
            Item("Stila Stay All Day Foundation Tan", "Stila", "Stay All Day Foundation Tan", 3),                   # 67
            Item("Stila Aqua Glow Serum Foundation", "Stila", "Aqua Glow Serum Foundation", 1),                    # 68
            Item("Nude by Nature Flawless Liquid Foundation", "Nude by Nature", "Flawless Liquid Foundation", 1),  # 69

            # Bundle 9 items (Michael Marcus skincare)
            Item("Michael Marcus Skin Exfoliate Jojoba Cleanser 120ml", "Michael Marcus", "Skin Exfoliate Jojoba Cleanser 120ml", 1), # 70
            Item("Michael Marcus Skin Firm Throat Gel 50ml", "Michael Marcus", "Skin Firm Throat Gel 50ml", 1),   # 71
            Item("Michael Marcus Skin Tighten Throat Serum 30ml", "Michael Marcus", "Skin Tighten Throat Serum 30ml", 1), # 72
            Item("Michael Marcus Skin Realeyes Firming Eye Cream 15ml", "Michael Marcus", "Skin Realeyes Firming Eye Cream 15ml", 1), # 73
            Item("Michael Marcus Skin Refresh Anti Pouf Eye Gel 15ml", "Michael Marcus", "Skin Refresh Anti Pouf Eye Gel 15ml", 1), # 74
            Item("Michael Marcus Skin Oxygen Masque 12ml", "Michael Marcus", "Skin Oxygen Masque 12ml", 1),     # 75

            # Bundle 10 items (Beauty Pie wholesale)
            Item("Beauty Pie Precision Shaping Lip Liner", "Beauty Pie", "Precision Shaping Lip Liner", 23),        # 76
            Item("Beauty Pie Wonder Colour Eye Crayon", "Beauty Pie", "Wonder Colour Eye Crayon", 30),           # 77
            Item("Beauty Pie Wonder Gel Longwear Lip Liner", "Beauty Pie", "Wonder Gel Longwear Lip Liner", 5),       # 78
            Item("Beauty Pie Super Cheek Powder Blush", "Beauty Pie", "Super Cheek Powder Blush", 2),            # 79
            Item("Beauty Pie Super Brown Pro Sculpting Powder", "Beauty Pie", "Super Brown Pro Sculpting Powder", 39),   # 80
            Item("Beauty Pie Super Brown Colour Mousse", "Beauty Pie", "Super Brown Colour Mousse", 6),           # 81
        ]
        self.custom_job_lots = []

    def create_with_uninitialized_items(self):
        """
        Build and return a list of predefined `JobLot` objects assembled
        from slices of `self.custom_items`.

        Returns
        -------
        list[JobLot]
            As written, a list containing only the first three constructed
            job lots (`custom_job_lot1`..`custom_job_lot3`). The remaining
            lots are created but not appended to the returned list.

        Notes
        -----
        - The `JobLot` constructor argument order is preserved exactly as
          in the original code; no validation is done here.
        - The price values provided are example buy prices for testing.
        """
        ci = self.custom_items  # alias for brevity

        custom_job_lot1 = JobLot(
            "custom",
            1,
            "v1|335632535170|0",
            "https://www.ebay.co.uk/itm/335632535170",
            "Wholesale Job lot of 100 Mixed Beauty Stock - Great Variety of Products!",
            ci[0:13],
            120
        )

        custom_job_lot2 = JobLot(
            "custom",
            2,
            "v1|126322633431|0",
            "https://www.ebay.co.uk/itm/126322633431",
            "BEAUTY BUNDLE - MAKE-UP SKINCARE JOBLOT - WORTH £50+ BEAUTY BOX - FREE SHIPPING",
            ci[13:24],
            17.99
        )

        custom_job_lot3 = JobLot(
            "custom",
            3,
            "v1|226904859352|0",
            "https://www.ebay.co.uk/itm/226904859352",
            "Beauty and Skincare Bundle Job Lot x 18 items",
            ci[24:40],
            16.13
        )

        custom_job_lot4 = JobLot(
            "custom",
            4,
            "v1|336045918234|0",
            "https://www.ebay.co.uk/itm/336045918234",
            "8x bags Assorted Beauty Samples Clarins Lancome Job Lot Bundle Mystery Gift Bags",
            ci[40:44],
            26.68
        )

        custom_job_lot5 = JobLot(
            "custom",
            5,
            "v1|257025312416|0",
            "https://www.ebay.co.uk/itm/257025312416",
            "Joblot/ Bundle Various Beauty Products",
            ci[44:53],
            37.08
        )

        custom_job_lot6 = JobLot(
            "custom",
            6,
            "v1|357358490727|0",
            "https://www.ebay.co.uk/itm/357358490727",
            "Job Lot Beauty Products See Picture & Description & Cult Beauty Makeup Bag - BN",
            ci[53:59],
            75
        )

        custom_job_lot7 = JobLot(
            "custom",
            7,
            "v1|297206865749|0",
            "https://www.ebay.co.uk/itm/297206865749",
            "BEAUTY BUNDLE - MAKE-UP SKINCARE JOBLOT BEAUTY BOX Perfume Minis Travel Gift Set",
            ci[59:67],
            25
        )

        custom_job_lot8 = JobLot(
            "custom",
            8,
            "v1|376362454603|0",
            "https://www.ebay.co.uk/itm/376362454603",
            "Beauty Bundle Job Lot - Stila Stay All Day Foundation, Aqua Glow, Nudebynature",
            ci[67:70],
            32
        )

        custom_job_lot9 = JobLot(
            "custom",
            9,
            "v1|306421393426|0",
            "https://www.ebay.co.uk/itm/306421393426",
            "Job Lot Michael Marcus Beauty Products",
            ci[70:76],
            76
        )

        custom_job_lot10 = JobLot(
            "custom",
            10,
            "v1|177316755479|0",
            "https://www.ebay.co.uk/itm/177316755479",
            "Wholesale job lot make up 105 items High End Brand Beauty Pie RRP over £1300",
            ci[76:82],
            12
        )

        self.custom_job_lots = [
            custom_job_lot1, custom_job_lot2, custom_job_lot3
        ]

        return self.custom_job_lots
