from email.mime import image
import os
from dotenv import load_dotenv
from openai import OpenAI
import re
from Item import Item
import base64

class ItemNameExtractor:
    def __init__(self):
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")  # Ensure you have set your OpenAI API key in environment variables
        )

    
    def extract_items(self, content):
        if not content:
            raise ValueError("Content cannot be empty.")
        if content.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')):
            return self.extract_items_from_image(content)
        
        else:
            if not isinstance(content, str):
                raise ValueError("Content must be a string or a valid image file path.")
            return self.extract_items_from_description(content)


    def extract_items_from_description(self, description):
        response = self.client.responses.create(
            model="gpt-5-mini",
            prompt={
                "id": "pmpt_689a63f0ed508194962c2003a14d1b170d285fb7e442bd2a",
                "version": "3"
            },
            input=description
        )

        return self.parse_items(response.output_text)



    def extract_items_from_image(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"The image file {image_path} does not exist.")

    # Read image file
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        print(f"Extracting items from image...")

        # Use OpenAI Vision API to extract text from image
        response = self.client.responses.create(
            model="gpt-5",
            input=[
            {
                "role": "user",
                "content": [
                {
                    "type": "input_text",
                    "text": (
                    "You are an assistant that extracts product names and their quantities in images. "
                    "Each product should include the brand and variant names without colons and how certain you are. "
                    "Return the result as a semicolon-separated list in this format: "
                    "Brand: Product Variant Size: Quantity: certainty "
                    "e.g. Bluesky: Gel Polish 10 ml: 2: 0.90; product2: variant: qty: certainty"
                    "If no products are found, output NULL. You must output something. "
                    "Try and get the size correct as much as possible"
                    )
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}"
                }
                ]
            }
            ]
        )

        return self.parse_items(response.output_text)
    

    def parse_items(self, items):
        lotItems = []
        print(f"extracted items: {items}")
        # Get the response text from the OpenAI API response
        items = re.sub(r'[^a-zA-Z0-9.:;\-&\s]', ' ', items)
        items = re.sub(r'(?<!^)(?:\:)\s*size(?:\:)', ' ', items, flags=re.IGNORECASE)
        items = re.sub(r'(?<!^)(?:\:)\s*colour(?:\:)', ' ', items, flags=re.IGNORECASE)
        items = re.sub(r'(?<!^)(?:\:)\s*color(?:\:)', ' ', items, flags=re.IGNORECASE)
        items = re.sub(r'(?<!^)(?:\:)\s*quantity(?:\:)', ' ', items, flags=re.IGNORECASE)
        items = re.sub(r'(?<!^)(?:\:)\s*certainty(?:\:)', ' ', items, flags=re.IGNORECASE)
        items = re.sub(r'(?<!^)(?:\:)\s*unknown(?:\:)', ' ', items, flags=re.IGNORECASE)
        # Normalize "n/a" variations and then remove it
        items = re.sub(r'\s+n/a(:)?', r' na\1', items, flags=re.IGNORECASE)
        items = re.sub(r'\s+n/a(:)?', r' na\1', items, flags=re.IGNORECASE)
        items = re.sub(r'\s+n\s*a(:)?', r' na\1', items, flags=re.IGNORECASE)
        items = re.sub(r'\s+na(:)?', r' na\1', items, flags=re.IGNORECASE)
        items = re.sub(r'\s+', ' ', items)
        
        items = items.strip()
        if items.strip() == "NULL":
            return []
        else:
            items = items.strip().split('; ')
            for item in items:
                parts = item.split(': ')
                if len(parts) > 4:
                    raise ValueError(f"Extracted item is too long: {item}, length = {len(parts)}, parts = {parts}")
                brand_name = (parts[0]).strip()
                if brand_name.lower() == "unknown":
                    brand_name = ""
                variant_name = (parts[1]).strip()
                name = f"{brand_name} {variant_name}".strip()
                quantity = float((parts[2]).strip())
                name_certainty = float((parts[3]).strip()) if len(parts) > 3 else 1
                lotItem = Item(name, brand_name, variant_name, quantity, name_certainty, name)
                lotItems.append(lotItem)
            return lotItems


    # def tidy(self, items) :
    #     return re.sub(
    #         r"""
    #         ^\s*
    #         (.*?)                                      # (1) product name
    #         (?:\s*\(size\s*(?:unknown|n/?a|[^)]*)\))?  # drop "(size ...)" if present
    #         \s*:\s*
    #         (?:quantity\s*:?\s*)?                      # optional "Quantity"
    #         (\d+(?:\.\d+)?)                            # (2) qty
    #         \s*:\s*
    #         (?:certainty\s*:?\s*)?                     # optional "certainty"
    #         (\d+(?:\.\d+)?)                            # (3) certainty
    #         .*$                                        # ignore any trailing text
    #         """,
    #         r"\1: \2: \3",
    #         items,
    #         flags=re.IGNORECASE | re.VERBOSE,
    #     ).strip()


if __name__ == "__main__":
    extractor = ItemNameExtractor()
    # Example usage
    work = "ESHO Lip Serum RENEW 12 ml: 1: 0.7; ESHO Lip Serum SCULPT 12 ml: 1: 0.95; ESHO Lip Serum DRENCH 12 ml: 1: 0.95; ESHO Lip Boosting Mask SEAL 10 ml: 1: 0.7"
    nowork= "Bluesky Gel Polish (assorted shades) Size: 10 ml (est): Quantity: 2: certainty: 0.90; Quewel Eyelash Extensions D Curl 0.05 mm Size: 1 tray; Quantity: 1; certainty: 0.85; Avon Hydramatic Matte Lipstick Size: 3.6 g (est); Quantity: 7; certainty: 0.90; Avon Glimmerstick Eye Liner Size: 0.28 g (est); Quantity: 2; certainty: 0.85; So...? Kiss Me Body Fragrance Size: 75 ml; Quantity: 1; certainty: 0.95; Handmade Naturals Super Hydrating Face Cream Size: 50 ml (est); Quantity: 1; certainty: 0.80; Studio 10 Longwear Liner Size: 1 pc; Quantity: 1; certainty: 0.80; NYX Smooth Whip Matte Lip Cream Size: 4 ml (est); Quantity: 1; certainty: 0.80; Rimmel Stay Satin Liquid Lip Colour Size: 5.5 ml (est); Quantity: 2; certainty: 0.80; Avon Ultra Shimmer Lipstick Size: 3.6 g (est); Quantity: 1; certainty: 0.70; Unknown brand Velvet Lip Tint (red tubes, assorted) Size: mixed (mostly full-size); Quantity: 15; certainty: 0.60; The Ordinary unknown product Size: 15 ml; Quantity: 1; certainty: 0.40; mio body cream mini Size: 20 ml; Quantity: 1; certainty: 0.50; mio mini lotion (pink cap) Size: 30 ml (est); Quantity: 1; certainty: 0.40; Domino Mint Gum Size: 1 pack; Quantity: 1; certainty: 0.70"
    test = "Bluesky Gel Polish (assorted shades) Size: 10 ml (est): Quantity: 2: certainty: 0.90"
    items = extractor.parse_items(test)
    for item in items:
        print(item)


