"""Buddy definitions — ASCII art companions for the cteam dashboard."""

BUDDIES = {
    "cat": {
        "name": "Neko",
        "idle": [
            r"  /\_/\  ",
            r" ( o.o ) ",
            r"  > ^ <  ",
        ],
        "happy": [
            r"  /\_/\  ",
            r" ( ^.^ ) ",
            r"  > ~ <  ",
        ],
        "sleep": [
            r"  /\_/\  ",
            r" ( -.- ) ",
            r"  > _ <  ",
            r"    z z  ",
        ],
        "alert": [
            r"  /\_/\  ",
            r" ( O.O ) ",
            r"  > ! <  ",
        ],
        "think": [
            r"  /\_/\  ",
            r" ( ?.? ) ",
            r"  > ~ <  ",
            r"    ...  ",
        ],
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
            r" /^ ^\  ",
            r"/ 0  0 \ ",
            r"V\ == /V ",
            r"  \__/   ",
        ],
        "happy": [
            r" /^ ^\  ",
            r"/ ^  ^ \ ",
            r"V\ == /V ",
            r"  \__/ ~ ",
        ],
        "sleep": [
            r" /v v\  ",
            r"/ -  - \ ",
            r"V\ -- /V ",
            r"  \__/   ",
        ],
        "alert": [
            r" /! !\  ",
            r"/ O  O \ ",
            r"V\ == /V ",
            r"  \__/ ! ",
        ],
        "think": [
            r" /^ ^\  ",
            r"/ o  o \ ",
            r"V\ .. /V ",
            r"  \__/   ",
        ],
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
            r" {o,o} ",
            r" |)__) ",
            r' -"-"- ',
        ],
        "happy": [
            r" {^,^} ",
            r" |)__) ",
            r' -"-"- ',
        ],
        "sleep": [
            r" {-,-} ",
            r" |)__) ",
            r' -"-"- ',
        ],
        "alert": [
            r" {O,O} ",
            r" |)__) ",
            r' -"-"- ',
        ],
        "think": [
            r" {o,o}?",
            r" |)__) ",
            r' -"-"- ',
        ],
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
            r"   ___  ",
            r"  / o \ ",
            r" | . . |",
            r"  \___/ ",
            r"   ~~~  ",
        ],
        "happy": [
            r"   ___  ",
            r"  / ^ \ ",
            r" | ^.^ |",
            r"  \___/ ",
            r"   ~~~  ",
        ],
        "sleep": [
            r"   ___  ",
            r"  / _ \ ",
            r" | -.- |",
            r"  \___/ ",
            r"   ~~~  ",
        ],
        "alert": [
            r"   ___  ",
            r"  / ! \ ",
            r" | O O |",
            r"  \___/ ",
            r"   ~~~  ",
        ],
        "think": [
            r"   ___  ",
            r"  / ? \ ",
            r" | o.o |",
            r"  \___/ ",
            r"   ~~.  ",
        ],
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
            r" [._.]  ",
            r" /|__|\ ",
            r"  d  b  ",
        ],
        "happy": [
            r" [^.^]  ",
            r" /|__|\ ",
            r"  d  b  ",
        ],
        "sleep": [
            r" [-.-]  ",
            r" /|__|\ ",
            r"  d  b  ",
        ],
        "alert": [
            r" [!.!]  ",
            r" /|__|\ ",
            r"  d  b  ",
        ],
        "think": [
            r" [o.o]? ",
            r" /|__|\ ",
            r"  d  b  ",
        ],
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

BUDDY_LIST = list(BUDDIES.keys())
