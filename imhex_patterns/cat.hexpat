import std.io;

// ImHex pattern for cats/*

// NOTES

// Based off tracing glaiel::SerializeCatData, so size and shape of fields are accurate
// Version-specific handling prior to format version 19 is not captured

// More work is required to validate and correct field types and naming

// Mewgenics 1.0.20695
// Mewgenics.exe
// SHA-256 25ae2f2fbd3c13faa04c69f5f1494330423ad1e268b41de73bb5cd9ac0590ac7

// Serializer/deserializer that dictates the layout of the file format under analysis
// 14022b370    void glaiel::SerializeCatData(struct glaiel::CatData* cat, struct glaiel::ByteStream* byte_stream, bool assert_version_cutoff_on_load)
// Constructor for the class manipulated by the serializer/deserializer
// 14005dac0    struct glaiel::CatData* glaiel::CatData(struct glaiel::CatData* this)
// Maps text keys to class fields and formats the data, possibly as part of a GUI builder
// 1400dec80    int64_t sub_7ff7016bec80(struct glaiel::CatData* cat, void* arg2, struct DecompMsvcString* arg3, int64_t* arg4)
// Manipulates many of the fields of the class under analysis
// 1400a5ba0    void glaiel::CatData::breed(struct glaiel::CatData* this, struct glaiel::CatData* p_parent_a, struct glaiel::CatData* p_parent_b, double coi, void* arg5)

// COMMON SUB-STRUCTURES

fn format_string_data(auto s) {
    return std::format("{}", s.data);
};

struct WString {
    u64 size;
    char16 data[size];
} [[sealed, format("format_string_data")]];

struct String {
    u64 size;
    char data[size];
} [[sealed, format("format_string_data")]];

struct Vector<S, T> {
    S size;
    T data[size];
};

// FILE LAYOUT

// Set to 19 (0x13) as of Mewgenics 1.0.20695
u32 version @ 0x00;

// Random bits rolled when a cat/kitten is generated
// Hashed to select a picture pose in the family tree viewer
u64 entropy @ $;

// Name
WString name @ $;

// Nameplate symbol
String nameplate_symbol @ $;

enum Sex : u32 {
    Male,
    Female,
    Neutral,
};

// Sex
// Both fields appear to carry the same value
Sex sex @ $;
Sex sex_dup @ $;

bitfield StatusFlagsB0 {
    owned : 1;                    // 0; stayed in the house for at least one night, or donated
    returned : 1;                 // 1; survived an adventure
    starving: 1;                  // 2
    unknown_3 : 1;                // 3
    unknown_4 : 1;                // 4; not sure what this does, but can be 0 or 1
    dead : 1;                     // 5
    unknown_7_6: 2;               // 7:6
};
bitfield StatusFlagsB1 {
    unknown_9_8 : 2;              // 9:8
    died_from_old_age : 1;        // 10
    donated_to_dr_beanies : 1;    // 11
    donated_to_butch : 1;         // 12
    donated_to_tink : 1;          // 13
    donated_to_tracy : 1;         // 14
    donated_to_organ_grinder : 1; // 15
};
bitfield StatusFlagsB2 {
    donated_to_frank : 1;         // 16
    donated_to_baby_jack : 1;     // 17
    died_in_battle : 1;           // 18
    on_adventure: 1;              // 19
    unknown_23_20 : 4;            // 23:20
};
bitfield StatusFlagsB3To7 {
    unknown_b3_0: 8;
    unknown_b4_0: 8;
    unknown_b5_0: 8;
    unknown_b6_0: 8;
    unknown_b7_0: 8;
};

// Various boolean bitfields
StatusFlagsB0 flags0 @ $;
StatusFlagsB1 flags1 @ $;
StatusFlagsB2 flags2 @ $;
StatusFlagsB3To7 flags37 @ $;

// unknown_2 and unknown_3 could form a passive ability structure ("None", 1)
// is referenced as a base pointer but not functionally used in current decomp database
String unknown_2 @ $;
// no references found in current decomp database
u32 unknown_3 @ $;

// Libido
double libido @ $;

// Sexual preference
double sexuality @ $;

// SQL key of loved cat
u64 lover_sql_key @ $;

// Increases every time the cat mates with their lover
// and decreases when they mate with another cat
// Unsure how/if this affects cat picked for events
double lover_affinity @ $;

// Aggression
double aggression @ $;

// SQL key of rival cat
u64 hater_sql_key @ $;

// Increases every time the cat fights with their rival
// and decreases when they fight with another cat
// Unsure how/if this affects cat picked for events
double hater_affinity @ $;

// Numerically multipled with a partner's fertility number
// to influence number of kittens during breeding
double fertility @ $;

struct BodyPartDescriptor {
    // need to validate by twiddling these numbers
    s32 part_sprite_idx;
    s32 texture_sprite_idx;
    s32 scar_sprite_idx;
    s32 unknown_1_nonzero_on_arms_and_legs;
    s32 unknown_2;
};
struct BodyParts {
    // need to validate by twiddling these numbers
    s32 texture_sprite_idx;
    s32 heritable_palette_idx;
    s32 collar_palette_idx;

    BodyPartDescriptor body;
    BodyPartDescriptor head;
    BodyPartDescriptor tail;
    BodyPartDescriptor leg1;
    BodyPartDescriptor leg2;
    BodyPartDescriptor arm1;
    BodyPartDescriptor arm2;
    BodyPartDescriptor lefteye;
    BodyPartDescriptor righteye;
    BodyPartDescriptor lefteyebrow;
    BodyPartDescriptor righteyebrow;
    BodyPartDescriptor leftear;
    BodyPartDescriptor rightear;
    BodyPartDescriptor mouth;

    s32 unknown_0;
    s32 unknown_1;

    // Voice actor
    String voice;

    // Voice pitch modifier
    double pitch;
};

// Body part and voice selection
BodyParts body_parts @ $;

struct CatStats {
    s32 str_;
    s32 dex;
    s32 con;
    s32 int;
    s32 spd;
    s32 cha;
    s32 lck;
};

// Base stats that would be passed to children
CatStats stats_heritable @ $;

// Stat deltas as a result of levelling and events
CatStats stats_delta_levelling @ $;

// Stat deltas as a result of injury
CatStats stats_delta_injuries @ $;

// stores the string name of a stat
// correlates with last injury
String last_injury_debuffed_stat @ $;

struct StatModifier {
    String expression;
    // Downcounter indicating how many battles this effect will last
    u32 battles_remaining;
};

struct CampaignStats {
    s32 hp;
    bool dead;
    bool unknown_0;
    s32 unknown_1;
    // Stat modifiers from events; next battle only
    Vector<u32, StatModifier> event_stat_modifiers;
};

// Tracks adventure stats and effects between battles
CampaignStats campaign_stats @ $;

// Movement and basic attack actives
String actives_basic[2] @ $;

// Current usable active ability list
// (including any inherited from parents)
String actives_accessible[4] @ $;

// Copy of active abilities originally
// inherited from parents
String actives_inherited[4] @ $;

struct Passive {
    String name;
    s32 unknown_0;
};

// Current usable passive ability list
Passive passives[2] @ $;

// Disorder and mutation passives
Passive mutations[2] @ $;

struct Equipment {
    // Set to 0x5 as of Mewgenics 1.0.20695
    u32 version;
    bool has_equipment;
    if(has_equipment) {
        String name;
        // Optional parameter string
        // (e.g. the Champion's Mask stores its buffed stat in this string)
        String aux_string;
        s32 uses_left;
        s32 unknown_2;
        s32 unknown_3;
        s32 unknown_4;
        u8 unknown_5;
        u8 times_taken_on_adventure;
    }
};

// Currently worn equipment
Equipment head @ $;
Equipment face @ $;
Equipment neck @ $;
Equipment weapon @ $;
Equipment trinket @ $;

// Collar
String collar @ $;

// Level
s32 level @ $;

// Coefficient of inbreeding
// Identical to values in files/pedigree
double coi @ $;

// Day of birth
// -2 and -1 are valid numeric days
// e.g. starter cats were born on day -2
s64 birthday @ $;

// Day of death (house deaths only)
// -1 is an invalidity marker, not a numeric day
// Only logged when cats die in the house, and not the field
s64 deathday_house @ $;

// some byte array, possibly related to house boss kills
Vector<u64, u8> unknown_17 @ $;

enum Lifestage: u32 {
    // Kittens and younger adult cats
    Young,
    // Visually indistinguishable from young cats
    Midage,
    // Visibly old cats, next stage is death from old age
    Old
};
// Lifestage
// Cats perform a probability check each night to move through these stages.
Lifestage lifestage @ $;

bitfield ClearedCampaignZonesB0 {
    unknown_0 : 1;                // 0
    path : 1 ;                    // 1; the tutorial
    alley: 1;                     // 2
    sewers : 1;                   // 3
    junkyard : 1;                 // 4
    caves : 1;                    // 5
    boneyard: 1;                  // 6
    throbbing_domain: 1;          // 7
};
bitfield ClearedCampaignZonesB1 {
    desert : 1;                   // 8
    crater : 1 ;                  // 9
    bunker: 1;                    // 10
    moon : 1;                     // 11
    core : 1;                     // 12
    unknown_13 : 1;               // 13; probably Rift, though haven't visited yet
    lab: 1;                       // 14
    unknown_15: 1;                // 15; probably one of Ice Age/Future
};
bitfield ClearedCampaignZonesB2 {
    unknown_23_16 : 8;            // 23:16; probably rest of Act 3
};
bitfield ClearedCampaignZonesB3To7 {
    unknown_b3_0: 8;
    unknown_b4_0: 8;
    unknown_b5_0: 8;
    unknown_b6_0: 8;
    unknown_b7_0: 8;
};

// Boolean bitfield of cleared zones
ClearedCampaignZonesB0 cleared_zones0 @ $;
ClearedCampaignZonesB1 cleared_zones1 @ $;
ClearedCampaignZonesB2 cleared_zones2 @ $;
ClearedCampaignZonesB3To7 cleared_zones37 @ $;

u8 unknown_21 @ $;

// Number of visited zones in the campaign
u8 num_visited_zones @ $;

u8 unknown_23 @ $;

// Fixed-sized array with indices corresponding to entries in injuries.gon
struct Injury {
    s32 broken_paw; // str
    s32 torn_tendon; // dex
    s32 broken_rib; // con
    s32 concussion; // int
    s32 disfigured; // cha
    s32 broken_leg; // spd
    s32 jinxed; // lck
    s32 immolated; // cha lck
    s32 exsanguinated; // str dex
    s32 poisoned; // con int
    s32 cursed; // lck lck
    s32 radiated; // con
    s32 unused[4];
};

Injury injuries @ $;
