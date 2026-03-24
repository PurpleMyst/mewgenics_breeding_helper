"""Static trait dictionaries for breeding probability calculations."""

import re

__all__ = [
    "is_class_active",
    "is_class_passive",
    "has_skillshare_plus",
]

# Generic spells available to all cats (collarless/generic)
_COLLARLESS_ACTIVES = frozenset(
    {
        "BBQ",
        "BarfBall",
        "Block",
        "Blow",
        "BlowKiss",
        "BoostSpellRange",
        "Brace",
        "Brainstorm",
        "BreakShortCircuit",
        "BurgeoningBarrier",
        "BurgeoningBattery",
        "BurgeoningBlast",
        "Burst",
        "ButtScoot",
        "BuyCatnip",
        "CPR",
        "CatNap",
        "ColdShoulder",
        "Confusion",
        "Contort",
        "Copycat",
        "Dart",
        "Desecrate",
        "DexterousHit",
        "DollUp",
        "Donate",
        "Dump",
        "Endeavor",
        "FeatherFeet",
        "FindARock",
        "Flex",
        "Focus",
        "ForbiddenFart",
        "GainThorns",
        "Gamble",
        "GymMembership",
        "HealBolt",
        "HireHitman",
        "Hiss",
        "HoseOff",
        "Hunt",
        "Infiltrate",
        "Interchange",
        "Itch",
        "Knead",
        "Landscape",
        "Lick",
        "LookAtMe",
        "LotteryShottery",
        "Magnet",
        "ManaDrain",
        "Meow",
        "Metabolize",
        "Metronome",
        "MiniDistract",
        "MiniHook",
        "Nerf",
        "PathOfTheButcher",
        "PathOfTheCleric",
        "PathOfTheDruid",
        "PathOfTheFighter",
        "PathOfTheHunter",
        "PathOfTheJester",
        "PathOfTheMage",
        "PathOfTheMonk",
        "PathOfTheNecromancer",
        "PathOfThePsychic",
        "PathOfTheTank",
        "PathOfTheThief",
        "PathOfTheTinkerer",
        "PathOfTheVoid",
        "PissYourself",
        "PlayDead",
        "PokeWound",
        "Ponder",
        "PrepareToJump",
        "Purr",
        "PushMove",
        "Reach",
        "Reduce",
        "Reflect",
        "Rest",
        "Roll",
        "Rouse",
        "RussianRoulette",
        "ScuffItOff",
        "SharpenClaws",
        "Shift",
        "SlipThrough",
        "Smack",
        "Snacks",
        "SoothingGlow",
        "SoulReap",
        "Spit",
        "StackTheDeck",
        "Step",
        "SubwayRide",
        "Sunburn",
        "SuperCrateBox",
        "Suppress",
        "Swat",
        "Taint",
        "Till",
        "Toast",
        "Trip",
        "VetVisit",
        "WasteTime",
        "WetHairball",
        "Zap",
    }
)

# Generic passives available to all cats (collarless/generic)
_COLLARLESS_PASSIVES = frozenset(
    {
        "Amped",
        "Amplify",
        "AnimalHandler",
        "BareMinimum",
        "ButchersSoul",
        "Careful",
        "Charming",
        "ClericsSoul",
        "Daunt",
        "Dealer",
        "DeathBoon",
        "DeathProof",
        "DeathsDoor",
        "DirtyClaws",
        "DruidsSoul",
        "ETank",
        "FastFooted",
        "FightersSoul",
        "FirstImpression",
        "Furious",
        "Gassy",
        "HotBlooded",
        "HuntersSoul",
        "Infested",
        "JestersSoul",
        "LateBloomer",
        "Leader",
        "LongShot",
        "LuckDrain",
        "Lucky",
        "MagesSoul",
        "Mange",
        "Mania",
        "MetalDetector",
        "MiniMe",
        "MonksSoul",
        "NaturalHealing",
        "NecromancersSoul",
        "OneEighty",
        "OverConfident",
        "Patience",
        "PressurePoints",
        "Protection",
        "PsychicsSoul",
        "Pulp",
        "Rockin",
        "SantaSangre",
        "Scavenger",
        "SelfAssured",
        "SerialKiller",
        "SkillShare",
        "Slugger",
        "StrengthInNumbers",
        "Study",
        "TanksSoul",
        "ThiefsSoul",
        "TinkerersSoul",
        "Unrestricted",
        "Untouched",
        "VoidSoul",
        "WhipCracker",
        "Wiggly",
        "Worms",
        "ZenkaiBoost",
    }
)

# Base SkillShare (cannot be inherited by offspring)
SKILLSHARE_BASE_ID = "SkillShare"

# Only the UPGRADED SkillShare+ triggers guaranteed inheritance
SKILLSHARE_PLUS_ID = SKILLSHARE_BASE_ID + "2"


def normalize_ability_key(ability_key: str) -> str:
    """Strips upgrade identifiers (e.g., trailing '2') to return the base ability."""
    return re.sub(r"\d*$", "", ability_key.strip())


def is_class_active(spell_id: str) -> bool:
    """Returns True if active ability is class-specific (NOT generic/collarless)."""
    return normalize_ability_key(spell_id) not in _COLLARLESS_ACTIVES


def is_class_passive(passive_id: str) -> bool:
    """Returns True if passive ability is class-specific."""
    return normalize_ability_key(passive_id) not in _COLLARLESS_PASSIVES


def has_skillshare_plus(cat) -> bool:
    """Check if cat has the upgraded SkillShare+ passive."""
    return SKILLSHARE_PLUS_ID in cat.passive_abilities
