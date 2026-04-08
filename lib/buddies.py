"""Buddy definitions — Animated ASCII art companions for the cteam dashboard.

Each mood has a list of frames that cycle for idle animation.
Reaction moods have multi-frame sequences that play once then return to idle.
"""

BUDDIES = {
    "cat": {
        "name": "Neko",
        # --- Looping animations (cycle continuously) ---
        "idle": [
            [  # frame 0: neutral
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ^ <  ",
            ],
            [  # frame 1: blink
                r"  /\_/\  ",
                r" ( -.- ) ",
                r"  > ^ <  ",
            ],
            [  # frame 2: tail right
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ^ < ~",
            ],
            [  # frame 3: neutral
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ^ <  ",
            ],
            [  # frame 4: tail left
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"~ > ^ <  ",
            ],
        ],
        "happy": [
            [
                r"  /\_/\  ",
                r" ( ^.^ ) ",
                r"  > ~ <  ",
            ],
            [
                r"  /\_/\  ",
                r" ( ^.^ ) ",
                r" ~> ~ <  ",
            ],
            [
                r"  /\_/\  ",
                r" ( ^.^ ) ",
                r"  > ~ <~ ",
            ],
        ],
        "sleep": [
            [
                r"  /\_/\  ",
                r" ( -.- ) ",
                r"  > _ <  ",
                r"         ",
            ],
            [
                r"  /\_/\  ",
                r" ( -.- ) ",
                r"  > _ <  ",
                r"      z  ",
            ],
            [
                r"  /\_/\  ",
                r" ( -.- ) ",
                r"  > _ <  ",
                r"     z z ",
            ],
            [
                r"  /\_/\  ",
                r" ( -.- ) ",
                r"  > _ <  ",
                r"    z z z",
            ],
        ],
        "think": [
            [
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ~ <  ",
                r"   .     ",
            ],
            [
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ~ <  ",
                r"   . .   ",
            ],
            [
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ~ <  ",
                r"   . . . ",
            ],
        ],
        # --- One-shot animations (play once, return to idle) ---
        "alert": [
            [  # ears up, eyes wide
                r"  /!_!\  ",
                r" ( O.O ) ",
                r"  > ! <  ",
            ],
            [
                r"  /\_/\  ",
                r" ( O.O ) ",
                r"  > ! <  ",
            ],
            [  # settles
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ^ <  ",
            ],
        ],
        "pounce": [
            [  # crouch
                r"  /\_/\  ",
                r" ( O.O ) ",
                r"  >___<  ",
            ],
            [  # leap
                r"    /\_/\ ",
                r"   ( >.< )",
                r"  ~/ ^ \~",
            ],
            [  # land
                r"      /\_/\ ",
                r"     ( ^.^ )",
                r"      >w<   ",
            ],
            [  # return
                r"  /\_/\  ",
                r" ( ^.^ ) ",
                r"  > ^ <  ",
            ],
        ],
        "startle": [
            [
                r"  /!\!\  ",
                r" (O . O) ",
                r"  >   <  ",
            ],
            [
                r"  /\_/\  ",
                r" ( O.O ) ",
                r"  > ! <  ",
            ],
            [
                r"  /\_/\  ",
                r" ( o.o ) ",
                r"  > ^ <  ",
            ],
        ],
        # --- Mood → animation type mapping ---
        "oneshot_moods": ["alert", "pounce", "startle"],
        "messages": {
            "idle": [
                "purrrr...",
                "*stretches*",
                "*stares at cursor*",
                "meow?",
                "*kneads keyboard*",
                "*tail swish*",
                "...",
                "*blinks slowly*",
            ],
            "sprint_start": [
                "ooh, a sprint! *ears perk up*",
                "*watches agents intently*",
                "go go go!",
            ],
            "sprint_done": [
                "*purrs loudly*",
                "nice work, human",
                "*headbutt*",
            ],
            "sprint_fail": [
                "*hisses at the error*",
                "that agent needs a nap",
                "*knocks error off table*",
            ],
            "build": [
                "*watches code scroll by*",
                "*paw on screen*",
                "is that... a bug? *pounce*",
            ],
            "long_idle": [
                "*curls into ball*",
                "zzz...",
                "*dream twitches*",
                "*snore*",
            ],
        },
    },
    "dog": {
        "name": "Byte",
        "idle": [
            [
                r" /^ ^\  ",
                r"/ 0  0 \ ",
                r"V\ == /V ",
                r"  \__/   ",
            ],
            [  # blink
                r" /^ ^\  ",
                r"/ -  - \ ",
                r"V\ == /V ",
                r"  \__/   ",
            ],
            [  # pant
                r" /^ ^\  ",
                r"/ 0  0 \ ",
                r"V\ == /V ",
                r"  \__/ P ",
            ],
            [
                r" /^ ^\  ",
                r"/ 0  0 \ ",
                r"V\ == /V ",
                r"  \__/   ",
            ],
        ],
        "happy": [
            [
                r" /^ ^\  ",
                r"/ ^  ^ \ ",
                r"V\ == /V ",
                r"  \__/ ~ ",
            ],
            [  # tail other side
                r" /^ ^\  ",
                r"/ ^  ^ \ ",
                r"V\ == /V ",
                r"~ \__/   ",
            ],
            [  # wiggle
                r"  /^ ^\ ",
                r" / ^  ^ \ ",
                r" V\ == /V",
                r"   \__/ ~",
            ],
        ],
        "sleep": [
            [
                r" /v v\  ",
                r"/ -  - \ ",
                r"V\ -- /V ",
                r"  \__/   ",
            ],
            [
                r" /v v\  ",
                r"/ -  - \ ",
                r"V\ -- /V ",
                r"  \__/ z ",
            ],
            [
                r" /v v\  ",
                r"/ -  - \ ",
                r"V\ -- /V ",
                r"  \__/z z",
            ],
        ],
        "alert": [
            [
                r" /! !\  ",
                r"/ O  O \ ",
                r"V\ == /V ",
                r"  \__/ ! ",
            ],
            [
                r" /^ ^\  ",
                r"/ O  O \ ",
                r"V\ == /V ",
                r"  \__/   ",
            ],
            [
                r" /^ ^\  ",
                r"/ 0  0 \ ",
                r"V\ == /V ",
                r"  \__/   ",
            ],
        ],
        "think": [
            [
                r" /^ ^\  ",
                r"/ o  o \ ",
                r"V\ .. /V ",
                r"  \__/   ",
            ],
            [
                r" /^ ^\  ",
                r"/ o  o \ ",
                r"V\ .. /V ",
                r"  \__/ ? ",
            ],
        ],
        "zoomies": [
            [
                r"     /^ ^\  ",
                r"    / ^  ^ \ ",
                r"   V\ == /V ",
                r" ~~  \__/   ",
            ],
            [
                r"         /^ ^\ ",
                r"        / ^  ^ \ ",
                r"       V\ == /V ",
                r"   ~~   \__/   ",
            ],
            [
                r"  /^ ^\       ",
                r" / ^  ^ \     ",
                r" V\ == /V     ",
                r"   \__/   ~~  ",
            ],
            [
                r" /^ ^\  ",
                r"/ ^  ^ \ ",
                r"V\ == /V ",
                r"  \__/ ~ ",
            ],
        ],
        "oneshot_moods": ["alert", "zoomies"],
        "messages": {
            "idle": [
                "*wag wag*",
                "*pant*",
                "woof!",
                "*tilts head*",
                "*brings you a stick*",
                "*tail helicopter*",
            ],
            "sprint_start": [
                "*BARK BARK*",
                "*zooomies*",
                "LET'S GOOO!",
            ],
            "sprint_done": [
                "*happy dance*",
                "*licks your face*",
                "GOOD BOY? AM I GOOD BOY?",
            ],
            "sprint_fail": [
                "*whimper*",
                "*sad eyes*",
                "*brings you the error gently*",
            ],
            "build": [
                "*watches intently*",
                "*sniffs the code*",
                "i don't understand but i support you",
            ],
            "long_idle": [
                "*flop*",
                "*snore... snore...*",
                "*leg twitch*",
                "*dream bark*",
            ],
        },
    },
    "owl": {
        "name": "Sage",
        "idle": [
            [
                r" {o,o} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [  # blink
                r" {-,-} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [
                r" {o,o} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [  # head tilt
                r"  {o,o}",
                r"  |)__)",
                r'  -"-"-',
            ],
        ],
        "happy": [
            [
                r" {^,^} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [  # ruffle
                r" {^,^} ",
                r" |)~~) ",
                r' -"-"- ',
            ],
        ],
        "sleep": [
            [
                r" {-,-} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [
                r" {-,-} ",
                r" |)__) ",
                r' -"-"-z',
            ],
        ],
        "alert": [
            [
                r" {O,O} ",
                r" |)__) ",
                r' -"-"- ',
            ],
            [  # head spin
                r" {O,O} ",
                r" (__(| ",
                r' -"-"- ',
            ],
            [
                r" {o,o} ",
                r" |)__) ",
                r' -"-"- ',
            ],
        ],
        "think": [
            [
                r" {o,o}?",
                r" |)__) ",
                r' -"-"- ',
            ],
            [
                r" {o,o} ",
                r" |)__)?",
                r' -"-"- ',
            ],
        ],
        "oneshot_moods": ["alert"],
        "messages": {
            "idle": [
                "hoo...",
                "*ruffles feathers*",
                "*rotates head 180°*",
                "*blinks wisely*",
                "*silent judgement*",
            ],
            "sprint_start": [
                "a wise approach",
                "*keen observation mode*",
                "I shall watch carefully",
            ],
            "sprint_done": [
                "as I predicted",
                "*satisfied hoot*",
                "well executed",
            ],
            "sprint_fail": [
                "hmm, I foresaw this",
                "*disappointed hoot*",
                "perhaps reconsider...",
            ],
            "build": [
                "*analyzes silently*",
                "interesting pattern...",
                "*takes notes mentally*",
            ],
            "long_idle": [
                "*perches motionless*",
                "...",
                "*one eye open*",
            ],
        },
    },
    "ghost": {
        "name": "Cinder",
        "idle": [
            [
                r"   ___  ",
                r"  / o \ ",
                r" | . . |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [  # flicker
                r"   ___  ",
                r"  /   \ ",
                r" | o.o |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [  # drift right
                r"    ___ ",
                r"   / o \ ",
                r"  | . . |",
                r"   \___/",
                r"    ~~~ ",
            ],
            [  # back
                r"   ___  ",
                r"  / o \ ",
                r" | . . |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [  # drift left
                r"  ___   ",
                r" / o \  ",
                r"| . . | ",
                r" \___/  ",
                r"  ~~~   ",
            ],
        ],
        "happy": [
            [
                r"   ___  ",
                r"  / ^ \ ",
                r" | ^.^ |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [  # float up
                r"   ___  ",
                r"  / ^ \ ",
                r" | ^.^ |",
                r"  \___/ ",
                r"        ",
                r"   ~~~  ",
            ],
            [  # float down
                r"        ",
                r"   ___  ",
                r"  / ^ \ ",
                r" | ^.^ |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
        ],
        "sleep": [
            [
                r"   ___  ",
                r"  / _ \ ",
                r" | -.- |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [  # fade
                r"   ___  ",
                r"  /   \ ",
                r" | -.- |",
                r"  \___/ ",
                r"   ...  ",
            ],
        ],
        "alert": [
            [  # bright flash
                r"  *___* ",
                r" */ ! \*",
                r"*| O O |*",
                r" *\___/*",
                r"   ~~~  ",
            ],
            [
                r"   ___  ",
                r"  / ! \ ",
                r" | O O |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [
                r"   ___  ",
                r"  / o \ ",
                r" | . . |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
        ],
        "think": [
            [
                r"   ___  ",
                r"  / ? \ ",
                r" | o.o |",
                r"  \___/ ",
                r"   ~~.  ",
            ],
            [
                r"   ___  ",
                r"  / ? \ ",
                r" | o.o |",
                r"  \___/ ",
                r"   ~..  ",
            ],
        ],
        "phase": [
            [  # going transparent
                r"   ___  ",
                r"  / o \ ",
                r" | . . |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
            [
                r"   . .  ",
                r"  .   . ",
                r" .  .  .",
                r"  . . . ",
                r"   . .  ",
            ],
            [  # gone
                r"        ",
                r"        ",
                r"    .   ",
                r"        ",
                r"        ",
            ],
            [  # reappear
                r"   . .  ",
                r"  .   . ",
                r" .  .  .",
                r"  . . . ",
                r"   . .  ",
            ],
            [
                r"   ___  ",
                r"  / o \ ",
                r" | . . |",
                r"  \___/ ",
                r"   ~~~  ",
            ],
        ],
        "oneshot_moods": ["alert", "phase"],
        "messages": {
            "idle": [
                "*floats quietly*",
                "boo~",
                "*phases through wall*",
                "*flickers*",
                "...*whisper*...",
            ],
            "sprint_start": [
                "*excited flickering*",
                "ooh spooky agents",
                "*haunts the sprint dir*",
            ],
            "sprint_done": [
                "*happy glow*",
                "*celebratory float*",
                "the spirits are pleased",
            ],
            "sprint_fail": [
                "*ominous flickering*",
                "cursed...",
                "*rattles chains at the bug*",
            ],
            "build": [
                "*peers through screen*",
                "*possesses the linter*",
                "i see dead code...",
            ],
            "long_idle": [
                "*becomes nearly invisible*",
                "*faint glow*",
                "still here...",
            ],
        },
    },
    "robot": {
        "name": "Chip",
        "idle": [
            [
                r" [._.]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [  # antenna blink
                r" [._.]° ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [
                r" [._.]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [  # shift weight
                r" [._.]  ",
                r" /|__|\ ",
                r"  d   b ",
            ],
        ],
        "happy": [
            [
                r" [^.^]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [  # arms up
                r" [^.^]  ",
                r"\|__|/  ",
                r"  d  b  ",
            ],
            [
                r" [^.^]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
        ],
        "sleep": [
            [
                r" [-.-]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [
                r" [-.-]  ",
                r" /|__|\ ",
                r"  d  b z",
            ],
        ],
        "alert": [
            [  # alarm
                r"![!.!]! ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [
                r" [!.!]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [
                r" [._.]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
        ],
        "think": [
            [
                r" [o.o]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
            [  # processing
                r" [o.o]  ",
                r" /|##|\ ",
                r"  d  b  ",
            ],
            [
                r" [o.o]? ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
        ],
        "dance": [
            [
                r" [^.^]  ",
                r"\|__|/  ",
                r" d    b ",
            ],
            [
                r"  [^.^] ",
                r" /|__|\  ",
                r"  d  b  ",
            ],
            [
                r" [^.^]  ",
                r"\|__|/  ",
                r"  b    d",
            ],
            [
                r" [^.^]  ",
                r" /|__|\ ",
                r"  d  b  ",
            ],
        ],
        "oneshot_moods": ["alert", "dance"],
        "messages": {
            "idle": [
                "beep boop",
                "*processing...*",
                "01101000 01101001",
                "*fan whirrs*",
                "*LED blink*",
            ],
            "sprint_start": [
                "INITIATING SPRINT PROTOCOL",
                "*overclocking*",
                "ALL SYSTEMS GO",
            ],
            "sprint_done": [
                "TASK COMPLETE. EFFICIENCY: 97.3%",
                "*victory beep*",
                "READY FOR NEXT DIRECTIVE",
            ],
            "sprint_fail": [
                "ERROR DETECTED. RECALCULATING.",
                "*sad beep*",
                "SUGGEST: retry with --force",
            ],
            "build": [
                "*compiling emotions*",
                "*analyzing syntax tree*",
                "PATTERN RECOGNIZED",
            ],
            "long_idle": [
                "*enters sleep mode*",
                "*low power...*",
                "STANDBY",
            ],
        },
    },
}

# State → mood + animation type mapping
STATE_MOOD_MAP = {
    "idle":         ("idle", "loop"),
    "sprint_start": ("alert", "oneshot"),
    "sprint_done":  ("happy", "loop"),
    "sprint_fail":  ("alert", "oneshot"),
    "build":        ("think", "loop"),
    "long_idle":    ("sleep", "loop"),
}

# Special reaction animations per buddy (triggered on state change)
STATE_REACTION_MAP = {
    "cat":   {"sprint_start": "pounce",   "sprint_fail": "startle"},
    "dog":   {"sprint_start": "zoomies",  "sprint_done": "zoomies"},
    "ghost": {"sprint_fail":  "phase",    "long_idle": "phase"},
    "robot": {"sprint_done":  "dance",    "sprint_start": "dance"},
    "owl":   {},
}

BUDDY_LIST = list(BUDDIES.keys())
