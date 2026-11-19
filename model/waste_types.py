"""The waste types PlanetWatch classifies each detected pile into.

One list shared by the labelling, training and inference code so the names never
drift. Each type maps to a different municipal response, which is why rubble and
hazardous waste are their own types even though the public datasets barely have them.

`prompts` are only used by `prelabel_types.py` (CLIP zero-shot suggestions before any
classifier is trained). Several phrasings per type are averaged, which makes CLIP's
guesses noticeably steadier than a single sentence.
"""

WASTE_TYPES = {
    "plastic": {
        "label": "Plastic",
        "prompts": [
            "a photo of a pile of plastic bags and plastic bottles dumped on the ground",
            "a photo of discarded plastic waste and plastic packaging",
            "a photo of plastic litter dumped by the roadside",
        ],
    },
    "paper_cardboard": {
        "label": "Paper / cardboard",
        "prompts": [
            "a photo of dumped cardboard boxes and paper",
            "a photo of a pile of waste paper and cardboard",
            "a photo of discarded cardboard packaging on the ground",
        ],
    },
    "organic": {
        "label": "Organic (food / garden)",
        "prompts": [
            "a photo of dumped garden waste, branches, grass cuttings and leaves",
            "a photo of rotting food waste dumped on the ground",
            "a photo of a pile of organic waste and vegetable scraps",
        ],
    },
    "metal_glass": {
        "label": "Metal / glass",
        "prompts": [
            "a photo of dumped scrap metal and tin cans",
            "a photo of a pile of broken glass bottles",
            "a photo of discarded metal sheets and rusty scrap",
        ],
    },
    "construction_rubble": {
        "label": "Construction rubble",
        "prompts": [
            "a photo of a pile of construction rubble, broken bricks and concrete",
            "a photo of dumped building debris, sand and broken blocks",
            "a photo of demolition waste dumped on open ground",
        ],
    },
    "bulky": {
        "label": "Bulky items (furniture / mattresses / appliances)",
        "prompts": [
            "a photo of an old mattress dumped on the street",
            "a photo of dumped old furniture, sofas and chairs",
            "a photo of a broken fridge or washing machine dumped outside",
        ],
    },
    "hazardous": {
        "label": "Hazardous (e-waste / medical / nappies)",
        "prompts": [
            "a photo of dumped electronic waste, old computers and cables",
            "a photo of discarded medical waste, syringes and face masks",
            "a photo of dumped used disposable nappies",
            "a photo of dumped old tyres and car batteries",
        ],
    },
    "mixed_household": {
        "label": "Mixed household",
        "prompts": [
            "a photo of a pile of mixed household rubbish dumped illegally",
            "a photo of an overflowing illegal dump with all kinds of garbage",
            "a photo of a heap of mixed trash on a street corner",
        ],
    },
}

TYPE_NAMES = list(WASTE_TYPES)

# Stored when the classifier isn't confident enough to name a type.
UNCLASSIFIED = "unclassified"


def type_label(name: str) -> str:
    """Human-readable label for a stored type ("construction_rubble" -> "Construction rubble").

    Reports saved before the classifier existed carry the detector's class `waste`.
    """
    if name in WASTE_TYPES:
        return WASTE_TYPES[name]["label"]
    return {"waste": "Waste (type not classified)", UNCLASSIFIED: "Unclassified"}.get(name, name)
