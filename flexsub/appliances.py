"""Appliance names per dataset and a common category for the ground truth.

Sources: REFIT README (CLEAN_READ_ME_081116.txt, appliance list "known at the beginning of the study" - see the notes
there about swaps), UK-DALE ReadMe (channel -> appliance). Categories:
  shiftable  washing machine, tumble dryer, washer dryer, dishwasher
  thermal    electric heater, dehumidifier/heater, air conditioner
  ev         electric vehicle
  base       fridge/freezer (always on)
  other      everything else (TV, computer, kettle, ...)
"""

# REFIT: Appliance1..Appliance9 for each house (index 0 = Appliance1)
REFIT_APPLIANCES = {
    1: ["Fridge", "Chest Freezer", "Upright Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Computer Site", "Television Site", "Electric Heater"],
    2: ["Fridge-Freezer", "Washing Machine", "Dishwasher", "Television", "Microwave", "Toaster", "Hi-Fi", "Kettle", "Oven Extractor Fan"],
    3: ["Toaster", "Fridge-Freezer", "Freezer", "Tumble Dryer", "Dishwasher", "Washing Machine", "Television", "Microwave", "Kettle"],
    4: ["Fridge", "Freezer", "Fridge-Freezer", "Washing Machine (1)", "Washing Machine (2)", "Computer Site", "Television Site", "Microwave", "Kettle"],
    5: ["Fridge-Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Computer Site", "Television Site", "Combination Microwave", "Kettle", "Toaster"],
    6: ["Freezer (Utility Room)", "Washing Machine", "Dishwasher", "MJY Computer", "Television Site", "Microwave", "Kettle", "Toaster", "PGM Computer"],
    7: ["Fridge", "Freezer (Garage)", "Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Television Site", "Toaster", "Kettle"],
    8: ["Fridge", "Freezer", "Dryer", "Washing Machine", "Toaster", "Computer", "Television Site", "Microwave", "Kettle"],
    9: ["Fridge-Freezer", "Washer Dryer", "Washing Machine", "Dishwasher", "Television Site", "Microwave", "Kettle", "Hi-Fi", "Electric Heater"],
    10: ["Magimix (Blender)", "Freezer", "Chest Freezer (In Garage)", "Fridge-Freezer", "Washing Machine", "Dishwasher", "Television Site", "Microwave", "Kenwood KMix"],
    11: ["Fridge", "Fridge-Freezer", "Washing Machine", "Dishwasher", "Computer Site", "Microwave", "Kettle", "Router", "Hi-Fi"],
    12: ["Fridge-Freezer", "Television Site (Lounge)", "Microwave", "Kettle", "Toaster", "Television Site (Bedroom)", "Not Used", "Not Used", "Not Used"],
    13: ["Television Site", "Unknown", "Washing Machine", "Dishwasher", "Tumble Dryer", "Television Site (2)", "Computer Site", "Microwave", "Kettle"],
    15: ["Fridge-Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Computer Site", "Television Site", "Microwave", "Kettle", "Toaster"],
    16: ["Fridge-Freezer (1)", "Fridge-Freezer (2)", "Electric Heater (1)", "Electric Heater (2)", "Washing Machine", "Dishwasher", "Computer Site", "Television Site", "Dehumidifier/Heater"],
    17: ["Freezer (Garage)", "Fridge-Freezer", "Tumble Dryer (Garage)", "Washing Machine", "Computer Site", "Television Site", "Microwave", "Kettle", "Plug Site (Bedroom)"],
    18: ["Fridge (garage)", "Freezer (garage)", "Fridge-Freezer", "Washer Dryer (garage)", "Washing Machine", "Dishwasher", "Desktop Computer", "Television Site", "Microwave"],
    19: ["Fridge & Freezer", "Washing Machine", "Television Site", "Microwave", "Kettle", "Toaster", "Bread-maker", "Lamp (80Watts)", "Hi-Fi"],
    20: ["Fridge", "Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Computer Site", "Television Site", "Microwave", "Kettle"],
    21: ["Fridge-Freezer", "Tumble Dryer", "Washing Machine", "Dishwasher", "Food Mixer", "Television", "Kettle/Toaster", "Vivarium", "Pond Pump"],
}
# Aggregate affected by solar panels (README): not usable as plain consumption
REFIT_PV_HOUSES = (11, 21)

# UK-DALE: building -> {channel (= NILMTK meterN): name}; only the channels useful for flexibility.
# Channel 1 is the aggregate of every building. Building 1 aggregate is recorded as apparent power.
UKDALE_CHANNELS = {
    1: {2: "boiler", 5: "washing_machine", 6: "dishwasher", 12: "fridge"},
    2: {12: "washing_machine", 13: "dish_washer", 14: "fridge"},
    3: {3: "electric_heater"},
    4: {5: "freezer"},  # channel 6 mixes washing machine + microwave + breadmaker -> not used
    5: {19: "fridge_freezer", 22: "dishwasher", 24: "washer_dryer"},
}


def category(name):
    n = name.lower()
    if any(k in n for k in ("washing machine", "tumble dryer", "washer dryer", "washer_dryer", "dishwasher", "dish_washer", "dryer")):
        return "shiftable"
    if any(k in n for k in ("electric heater", "electric_heater", "dehumidifier", "air condition", "a/c", "ac_", "heater")):
        return "thermal"
    if "ev" == n or "car" in n:
        return "ev"
    if any(k in n for k in ("fridge", "freezer")):
        return "base"
    return "other"
