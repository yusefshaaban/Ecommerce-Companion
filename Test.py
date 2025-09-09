from TokenSet import TokenSet
from Product import Product

def run():

    product = Product("Bath and Shower Gel 30ml Travel Bundle X10 Various Scents New Gift", brand_name="Molton Brown", variant_name="Bath and Shower Gel 30ml Travel Bundle X10.05 Various Scents New Gift", original_brand_name="", original_variant_name="test", web_url="")

    tokenset = TokenSet(product)
    print("Raw Tokens:", tokenset.variant_name_raw)
    print("Normalized Tokens:", tokenset.variant_name_normalized)

if __name__ == "__main__":
    run()