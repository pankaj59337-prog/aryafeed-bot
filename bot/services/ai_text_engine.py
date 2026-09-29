"""AI Self-Thinking Text Generation Engine for Viral Reels."""

import logging
import random
from typing import List, Optional

logger = logging.getLogger(__name__)

# Exact viral reference scripts cataloged from C:\Users\PANKAJ\Downloads\scripts
REFERENCE_SEXY_SCRIPTS: List[str] = [
    "If u think u can flirt better than me, talk to me after 2 AM",
    "Maine flirt back kardiya na to ladle tu so nahi payega",
    "Don't trust mee... I have a beautiful Heart & innocent face with P*rnstar mindset!!",
    "Umar hi aisi hai Samjh nahi a raha Hormone sambhalu Yaaa career!!",
    "Not gonna lie but I can change your hahaha into ahahaha.",
    "Can we clap together Without using hands",
    "My mouth will always Be better than your hand",
    "Last time kab Kia tha aapne Vo sab",
    "if distance didn't exist we'd probably be f*king right now",
    "Wanna some darty chat ? 🌚✨ (rhendo cutiee haar jaogi...)",
    "Choose one?\n1. 10 minutes Rough\n2. 40 minutes Slowly",
    "One emoji for your current mood 🌚",
    "Don't act so innocent, I know what you do when no one's home",
    "Rooh se pyar Karne wala kaise jane ga jism ka mazaaa??",
    "What's your type? A dirty minded person with a good heart..!!",
    "I paused my p0rn to text you back, don't ever question my loyalty",
    "I LOVE MONEY But 'W' is Silent !!",
    "I'm so bored can we flirt tonight then act like nothing happened tomorrow.",
    "Anyone for late night chat ?? Dm me",
    "Masoom toh wo log hai Jo Neptune Kiss ka Matlab nahi jante",
    "I can't drive a car but I can drive u insane",
    "Suppose I'm your santa, so tell me Your 3 risky wishes?",
    "I'm bored, surprise me with some 1 view stuff.",
    "If you think u can flirt Better..... Talk to me after 11pm",
    "PeriOds khtam hote hi mn esa krta h ki bs koi meri udhed k rakhde",
    "Forgive me for my dirty talks, it was not me, it was my hormones.",
    "Dirty talks reduce stress just inform me, if you have any stress!!!",
    # Desi Romantic & Sultry Saree Moodboard References
    "Unhe laga saree me masoom lagungi, ab unhe kaun samjhaye ki aag pallu me hai 🌚💋",
    "Ek toh ye kali saree, upar se tumhari ye nigahein... aaj raat bachna mushkil hai 🌚💋",
    "Saree pehnu ya western, tera dhyan toh bas meri kamar pe hi rukna hai 🙈🔥",
    "Tumhe lagta hai main shant hoon? kabhi akele me milna, saare vaham nikal dungi 🌚✨",
    "Raat ke 2 baje tumhara khayal aur ye thandi hawa... mood kharab kar rahi hai 💋",
    "I'm not responsible agar meri saree ka pallu dekh kar tumhara control kho jaye 🌚✨",
    "Jitna tum innocent bante ho na, utne hi khatarnaak tumhare iraade hain 🙈🔥",
    "Bas ek baar pyaar se pakad lo, saari zidd ek second me pighal jayegi 💋",
    "Late night mirror selfie sirf isliye, taaki tumhari neend thodi aur udd sake 🌚💋",
    "Main toh chup-chap baithi thi, par meri saree ki dori ne saara kaam kharab kar diya 💋🙈",
    "Ghar wale kehte hain ladki sanskari hai... unhe kya pata 2 AM ke baad kiske khayalon me rehti hoon 🌚💋",
    "Zulfein bandh ke rakhu ya kholi chhod du? batao kis me hosh khone ka irada hai 💋✨",
    "Teri ek nazar kafi hai mere dil ka thermostat badhane ke liye 🔥🙈",
    "Don't look at my lips while I'm talking, warna baat adhoori reh jayegi 💋🌚",
    "Mera favourite outfit? Saree... aur tera favourite part? Uski dori 🙈🔥",
    "Raat ko itni der tak jaagte ho, kaho toh neend udane ka koi solid bahana ban jau? 🌚💋",
    "I’m not a bad girl, but with you I definitely have bad intentions 💋✨",
    "Seedha bolo na ki meri kamar ke til pe dil aa gaya hai, ye sharmaane ka natak kyu? 🌚🔥",
    "Pyaar ek taraf, par jo maza late night flirty fights me hai wo kahi nahi 🙈💋",
    "Tumhe lagta hai main ignore kar rahi hoon? Main toh bas dekh rahi hoon kab tak tadap sakte ho 🌚✨",
    "Bas itni si khwaish hai... thodi si chhed-chhad aur dher saara sukoon 💋🔥",
    "Itna sweet ban ke mat dekho, sugar nahi seedha addiction ho jayega 🌚💋",
    "One late night ride with you, and zero promises for what happens in the car 🙈🔥",
    "Saree ka pallu sambhalu ya tumhare irade? Dono hi haath se nikalte ja rahe hain 🌚💋",
    "You're cute, but I bet you'd look better under my bad influence 💋✨",
    "Thoda aur paas aao... kuch aisi baat kehni hai jo hawa bhi na sun sake 🌚🔥",
    "Meri aankhon me dekh kar baat karo, floor par dekhne se control nahi aayega 💋🙈",
    "Ek cup chai, thandi raat, aur tumhari shararati ungliyan meri kamar par... bas itna hi chahiye 🌚💋",
    "Aankhein band karo aur socho: main, tum aur ek band kamra... ab bolo neend aayegi? 🙈🔥",
    "flirt back karne ki galti mat karna, aadat lag gayi toh chhutti nahi milegi 🌚💋",
    "Kaash tum yaha hote, meri nightdress ka ribbon tumse hi bandhwati 💋✨",
    "They told me to dress my age, so I wore saree and brought down their blood pressure 🌚🔥",
    "Aadha pagal toh tumhari muskuraahat ne kar diya, baaki ka kaam ye late night texts kar rahe hain 💋🙈",
]

# Generative formula components for synthesized hooks
SEXY_OPENERS = [
    "Ek sachi baat batau,",
    "If you think you're toxic,",
    "Late night thoughts:",
    "Don't fall in love with me,",
    "Someone told me flirting burns calories,",
    "Just a friendly reminder:",
    "My innocent smile is just a cover,",
    "Can we just skip the small talk and",
    "Agar maine sach bol diya na,",
    "2 AM rules are simple:",
    "Mummy ko lagta hai so rahi hoon, par",
    "Suno na,",
    "Sach batao,",
    "Agar main thodi ziddi ban jau toh,",
]

SEXY_BODIES = [
    "I'm 99% sweet and 1% what you dream about at night.",
    "You look like my next favourite mistake.",
    "flirt karoge ya seedha Dil churaane ka plan hai? 🌚",
    "I can be your peace by day and your obsession by night.",
    "apne iraade pehle bata do, baad me sambhalna mushkil hoga.",
    "one look from you and my self-control just logs out.",
    "main seedha bolti nahi, seedha karke dikhati hoon.",
    "talk to me when everyone else is asleep.",
    "you're dangerously close to ruining my good girl reputation.",
    "you couldn't handle me even if I came with an instruction manual.",
    "aaj raat tumhari neend churaane ka full plan hai 🌚💋",
    "kabhi fursat me aana, dikhaungi sharafat ke piche kya hai 🙈🔥",
    "meri aankhon me itna mat dekho, nasha ho jayega 💋✨",
    "tumhare bina ye thandi raat thodi zyada lamba lag rahi hai 🌚",
]

CINEMATIC_HOOKS = [
    "In a city of eight million people, all I looked for was your silhouette.",
    "We were a poem written in smoke, beautiful until we vanished.",
    "Some people walk into your life just to show you what silence feels like.",
    "The moon never apologizes for being alone among billions of stars.",
    "We loved each other in the spaces between what was said and what was felt.",
    "Not every story needs a happy ending to be a masterpiece.",
    "Memories don't die, they just learn how to live in the dark.",
]

MEME_HOOKS = [
    "Me: I'm gonna sleep early tonight.\nMy brain at 3 AM: Let's re-examine that awkward interaction from 2017.",
    "My toxic trait is thinking I can learn an entire semester's syllabus in 4 hours.",
    "Diet starts tomorrow... which is great because tomorrow never comes.",
    "I need a 6-month vacation, twice a year.",
    "Adulting is literally saying 'it is what it is' until you pass out.",
    "My patience level right now is at 2% with battery saver off.",
    "When someone asks 'what do you do for fun?' and you just lay in bed on your phone.",
]

ROMANTIC_HOOKS = [
    "I fell in love with the way you touch my soul without even touching my hands.",
    "In every lifetime and every universe, my heart would still find yours.",
    "You don't feel like an accident. You feel like destiny.",
    "Home isn't four walls anymore. It's the sound of your voice.",
    "I never believed in magic until you looked at me and the whole world stopped.",
    "With you, even silence feels like the deepest conversation.",
]

QUOTE_HOOKS = [
    "Work in silence. Let your success make the deafening noise.",
    "You didn't come this far to only come this far.",
    "Discipline is choosing between what you want now and what you want most.",
    "The person who moves a mountain begins by carrying away small stones.",
    "Never let your fear of striking out keep you from playing the game.",
    "Your future is created by what you do today, not tomorrow.",
]

MINIMAL_HOOKS = [
    "Stay wild.",
    "Less noise. More life.",
    "Golden hour state of mind.",
    "Unbothered.",
    "Quiet confidence.",
    "Chasing sunsets, not people.",
    "Silence is an answer too.",
]


def generate_viral_text(style: str = "sexy", custom_topic: Optional[str] = None) -> str:
    """Generate a high-converting, viral reel text caption based on category."""
    style_key = style.lower().strip()

    if style_key == "sexy":
        # 50% chance pick a verified viral reference hook, 50% chance generate a fresh combination
        if random.random() < 0.45:
            return random.choice(REFERENCE_SEXY_SCRIPTS)
        else:
            opener = random.choice(SEXY_OPENERS)
            body = random.choice(SEXY_BODIES)
            return f"{opener}\n{body}"

    elif style_key == "cinematic":
        return random.choice(CINEMATIC_HOOKS)

    elif style_key == "meme":
        return random.choice(MEME_HOOKS)

    elif style_key == "romantic":
        return random.choice(ROMANTIC_HOOKS)

    elif style_key == "quote":
        return random.choice(QUOTE_HOOKS)

    elif style_key == "minimal":
        return random.choice(MINIMAL_HOOKS)

    else:
        # Fallback to sexy / flirty
        return random.choice(REFERENCE_SEXY_SCRIPTS)
